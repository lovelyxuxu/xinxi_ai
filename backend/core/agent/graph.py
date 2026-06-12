"""
心犀AI - LangGraph 工作流编排（v2: 含 Human-in-the-loop）
=========================================================
用 LangGraph 的 StateGraph 将所有 Agent 节点串联成完整的工作流。

学习要点：
---------
LangGraph 是 LangChain 团队出品的"状态图"引擎，用于编排复杂的 Agent 工作流。
核心概念只有四个：

  1. State（状态）: 在各节点之间共享的数据容器 → 定义在 state.py
  2. Node（节点）: 一个处理函数，读取 State、写回 State → 定义在 nodes.py
  3. Edge（边）: 节点之间的连接关系（A 执行完后去 B）
  4. Conditional Edge（条件边）: 根据 State 中的值决定下一步走向

工作流拓扑（HITL_ENABLED=True 时）：
  parse_intent → hybrid_search → post_analysis → human_feedback → [条件判断]
                                                                        │
                    ┌─── approve ──────────→ generate_match → END
                    │
                    └─── reject/adjust ──→ reflection → [检查循环次数]
                                                            │
                                      ┌── 未超限 ──→ hybrid_search（重试）
                                      └── 已超限 ──→ generate_match → END

工作流拓扑（HITL_ENABLED=False 时，保持原流程）：
  parse_intent → hybrid_search → post_analysis → [条件判断]
                                                      │
                    ┌─── 满足阈值 ──→ generate_match → END
                    │
                    └─── 不满足 ──→ reflection → [检查循环次数]
                                                        │
                                      ┌── 未超限 ──→ hybrid_search（重试）
                                      └── 已超限 ──→ generate_match → END

Phase 6 新增 Human-in-the-loop：
  - human_feedback 节点使用 LangGraph 的 interrupt() 暂停执行
  - 用户可以审核候选人并提供反馈（approve/reject/adjust）
  - 通过 Command(resume=feedback) 恢复执行
  - 需要 checkpointer 才能使用 interrupt
"""

import os
from functools import partial
from langgraph.graph import StateGraph, START, END

from config.settings import match_config
from core.agent.state import AgentState
from core.agent.nodes import (
    parse_intent,
    hybrid_search,
    post_analysis,
    reflection,
    generate_match,
    human_feedback,
)
from core.retrieval.hybrid_retriever import HybridRetriever

# Phase 6: Human-in-the-loop 开关
# 设为 True 时，匹配流程会在分析后暂停，等待用户反馈
HITL_ENABLED = os.environ.get("HITL_ENABLED", "false").lower() == "true"


def build_matching_graph(retriever: HybridRetriever, checkpointer=None, hitl=None):
    """
    构建并编译婚恋匹配的 LangGraph 工作流。

    参数:
        retriever: 混合检索器实例（需要注入数据库依赖）
        checkpointer: 检查点持久化器（HITL 模式必须提供）
        hitl: 是否启用 Human-in-the-loop（默认读环境变量 HITL_ENABLED）

    返回:
        编译好的 LangGraph 应用，可以直接 .invoke(state) 调用
    """

    use_hitl = hitl if hitl is not None else HITL_ENABLED

    # ========================================
    # 1. 创建 StateGraph
    # ========================================
    graph = StateGraph(AgentState)

    # ========================================
    # 2. 添加节点
    # ========================================
    graph.add_node("parse_intent", parse_intent)

    search_node = partial(hybrid_search, retriever=retriever)
    graph.add_node("hybrid_search", search_node)

    graph.add_node("post_analysis", post_analysis)
    graph.add_node("reflection", reflection)
    graph.add_node("generate_match", generate_match)

    if use_hitl:
        # Phase 6: 添加人工反馈节点
        graph.add_node("human_feedback", human_feedback)

    # ========================================
    # 3. 连接边
    # ========================================

    # 入口 → 意图解析
    graph.add_edge(START, "parse_intent")

    # 意图解析 → 混合检索
    graph.add_edge("parse_intent", "hybrid_search")

    # 混合检索 → 后分析
    graph.add_edge("hybrid_search", "post_analysis")

    if use_hitl:
        # ========== HITL 模式 ==========
        # 后分析 → 人工反馈
        graph.add_edge("post_analysis", "human_feedback")

        # 人工反馈 → 条件判断（根据用户反馈类型路由）
        graph.add_conditional_edges(
            "human_feedback",
            _should_continue_after_feedback,
            {
                "generate_match": "generate_match",   # approve → 生成推荐信
                "reflection": "reflection",            # reject/adjust → 反思
            },
        )
    else:
        # ========== 原始模式（无 HITL）==========
        graph.add_conditional_edges(
            "post_analysis",
            _should_continue,
            {
                "generate_match": "generate_match",
                "reflection": "reflection",
            },
        )

    # 反思 → 条件判断
    graph.add_conditional_edges(
        "reflection",
        _should_retry,
        {
            "hybrid_search": "hybrid_search",
            "generate_match": "generate_match",
        },
    )

    # 生成推荐信 → 结束
    graph.add_edge("generate_match", END)

    # ========================================
    # 4. 编译图
    # ========================================
    # HITL 模式下 checkpointer 是必须的（interrupt 需要它来保存/恢复状态）
    if use_hitl and checkpointer is None:
        print("  [Phase 6] WARNING: HITL enabled without checkpointer! interrupt() won't work.")

    app = graph.compile(checkpointer=checkpointer)

    mode = "HITL (Human-in-the-loop)" if use_hitl else "Auto (无干预)"
    print(f"  [Graph] Matching graph compiled in {mode} mode")

    return app


# ============================================================
# 路由函数：条件边的"大脑"
# ============================================================

def _should_continue(state: AgentState) -> str:
    """
    后分析节点执行完毕后，判断是否继续（原始模式，无 HITL）。

    逻辑：
    - 如果最高契合分 >= 阈值 → 满意，去生成推荐信
    - 如果最高契合分 < 阈值 → 不满意，去反思
    """
    best_score = state.get("best_score", 0)
    threshold = match_config.match_threshold * 100

    if best_score >= threshold:
        return "generate_match"
    else:
        return "reflection"


def _should_continue_after_feedback(state: AgentState) -> str:
    """
    Phase 6: 人工反馈节点执行完毕后，根据用户反馈路由。

    逻辑：
    - should_retry == False → 用户满意（approve），去生成推荐信
    - should_retry == True  → 用户不满意（reject/adjust），去反思
    """
    if state.get("should_retry"):
        return "reflection"
    else:
        return "generate_match"


def _should_retry(state: AgentState) -> str:
    """
    反思节点执行完毕后，判断是否重试。

    逻辑：
    - 如果循环次数 < 最大次数 → 重试检索
    - 如果已达最大次数 → 放弃优化，直接用当前结果
    """
    loop_count = state.get("loop_count", 0)
    max_loops = match_config.max_agent_loops

    if loop_count < max_loops:
        return "hybrid_search"
    else:
        return "generate_match"
