"""
心犀AI - LangGraph 工作流编排
===============================
用 LangGraph 的 StateGraph 将所有 Agent 节点串联成完整的工作流。

学习要点：
---------
LangGraph 是 LangChain 团队出品的"状态图"引擎，用于编排复杂的 Agent 工作流。
核心概念只有四个：

  1. State（状态）: 在各节点之间共享的数据容器 → 定义在 state.py
  2. Node（节点）: 一个处理函数，读取 State、写回 State → 定义在 nodes.py
  3. Edge（边）: 节点之间的连接关系（A 执行完后去 B）
  4. Conditional Edge（条件边）: 根据 State 中的值决定下一步走向

工作流拓扑：
  parse_intent → hybrid_search → post_analysis → [条件判断]
                                                      │
                    ┌─── 满足阈值 ──→ generate_match → END
                    │
                    └─── 不满足 ──→ reflection → [检查循环次数]
                                                        │
                                      ┌── 未超限 ──→ hybrid_search（重试）
                                      └── 已超限 ──→ generate_match → END
"""

from functools import partial
from langgraph.graph import StateGraph, START, END

from config.settings import match_config
from src.agent.state import AgentState
from src.agent.nodes import (
    parse_intent,
    hybrid_search,
    post_analysis,
    reflection,
    generate_match,
)
from src.retrieval.hybrid_retriever import HybridRetriever


def build_matching_graph(retriever: HybridRetriever):
    """
    构建并编译婚恋匹配的 LangGraph 工作流。

    参数:
        retriever: 混合检索器实例（需要注入数据库依赖）

    返回:
        编译好的 LangGraph 应用，可以直接 .invoke(state) 调用
    """

    # ========================================
    # 1. 创建 StateGraph
    # ========================================
    # StateGraph 需要知道 State 的类型定义
    graph = StateGraph(AgentState)

    # ========================================
    # 2. 添加节点
    # ========================================
    # 每个节点就是一个函数：接收 state dict，返回更新的 dict
    graph.add_node("parse_intent", parse_intent)

    # hybrid_search 需要 retriever 参数，用 functools.partial 绑定
    # partial 会"预填充"retriever 参数，生成一个只接受 state 的新函数
    search_node = partial(hybrid_search, retriever=retriever)
    graph.add_node("hybrid_search", search_node)

    graph.add_node("post_analysis", post_analysis)
    graph.add_node("reflection", reflection)
    graph.add_node("generate_match", generate_match)

    # ========================================
    # 3. 连接边（定义节点间的流转关系）
    # ========================================

    # 入口 → 意图解析
    graph.add_edge(START, "parse_intent")

    # 意图解析 → 混合检索
    graph.add_edge("parse_intent", "hybrid_search")

    # 混合检索 → 后分析
    graph.add_edge("hybrid_search", "post_analysis")

    # 后分析 → 条件判断（这是最关键的条件分支！）
    graph.add_conditional_edges(
        "post_analysis",
        _should_continue,          # 路由函数：返回下一个节点的名称
        {
            "generate_match": "generate_match",   # 满足条件 → 生成推荐信
            "reflection": "reflection",            # 不满足 → 反思
        },
    )

    # 反思 → 条件判断（检查是否超过最大循环次数）
    graph.add_conditional_edges(
        "reflection",
        _should_retry,
        {
            "hybrid_search": "hybrid_search",     # 未超限 → 重新检索
            "generate_match": "generate_match",   # 已超限 → 直接用当前结果生成推荐
        },
    )

    # 生成推荐信 → 结束
    graph.add_edge("generate_match", END)

    # ========================================
    # 4. 编译图
    # ========================================
    # compile() 会检查图的完整性（是否有孤立节点、是否所有路径都能到达 END）
    app = graph.compile()

    return app


# ============================================================
# 路由函数：条件边的"大脑"
# ============================================================

def _should_continue(state: AgentState) -> str:
    """
    后分析节点执行完毕后，判断是否继续。

    逻辑：
    - 如果最高契合分 >= 阈值 → 满意，去生成推荐信
    - 如果最高契合分 < 阈值 → 不满意，去反思
    """
    best_score = state.get("best_score", 0)
    # 将 0~100 的分数和 0~1 的阈值统一比较
    threshold = match_config.match_threshold * 100  # 转为百分制

    if best_score >= threshold:
        return "generate_match"
    else:
        return "reflection"


def _should_retry(state: AgentState) -> str:
    """
    反思节点执行完毕后，判断是否重试。

    逻辑：
    - 如果循环次数 < 最大次数 → 重试检索
    - 如果已达最大次数 → 放弃优化，直接用当前结果
    """
    loop_count = state.get("loop_count", 0)  # reflection 节点已递增过
    max_loops = match_config.max_agent_loops

    if loop_count < max_loops:
        return "hybrid_search"
    else:
        return "generate_match"
