"""
心犀AI - Supervisor 多 Agent 图构建器
=========================================
用 LangGraph 的 StateGraph 构建 Supervisor 模式的多 Agent 工作流。

学习要点：
---------
Supervisor 模式的图结构非常简单：
  - 所有 Agent 都是平行的节点
  - 每个 Agent 执行完毕后回到 Supervisor
  - Supervisor 通过条件边（Conditional Edge）决定下一个 Agent

  ┌──────────────────────────────────────┐
  │  START → Supervisor                  │
  │           ↗    ↘                     │
  │       Agent1   Agent2   Agent3 ...   │
  │           ↘    ↗                     │
  │          Supervisor → FINISH/Agent   │
  └──────────────────────────────────────┘

与原版图的区别：
  - 原版：parse_intent → hybrid_search → post_analysis → ...（链式）
  - 新版：所有节点都通过 Supervisor 中转（星型）

这种结构的优势：
  1. 增删 Agent 只需修改路由逻辑，不影响其他 Agent
  2. 每个 Agent 完全独立，可以单独测试
  3. 未来可以动态调整流程（如 LLM 决定跳过某个步骤）
"""

import os
from functools import partial
from langgraph.graph import StateGraph, START, END

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.agents.supervisor.router import rule_based_router, llm_based_router
from core.agents.intent.agent import intent_agent
from core.agents.retrieval.agent import retrieval_agent
from core.agents.analysis.agent import analysis_agent
from core.agents.reflection.agent import reflection_agent
from core.agents.letter.agent import letter_agent
from core.agents.judge.agent import judge_agent
from core.retrieval.hybrid_retriever import HybridRetriever


# 路由方式配置：rule（规则版）或 llm（LLM 版）
# 可以通过环境变量 SUPERVISOR_ROUTER 切换
ROUTER_MODE = os.environ.get("SUPERVISOR_ROUTER", "rule")


def _supervisor_node(state: SupervisorState) -> dict:
    """
    Supervisor 节点：调度中心。

    在 Supervisor 模式中，Supervisor 本身也是一个节点。
    它的职责很简单：查看当前状态，决定下一步执行哪个 Agent。

    学习要点：
    - Supervisor 节点不做任何"业务逻辑"——它只做"调度"
    - 路由决策的结果通过 state["next_agent"] 传递
    - LangGraph 的 conditional_edges 会读取这个值来决定走向
    """
    messages = state.get("messages", [])
    history = state.get("agent_history", [])

    # 根据配置选择路由方式
    if ROUTER_MODE == "llm":
        next_agent = llm_based_router(state)
    else:
        next_agent = rule_based_router(state)

    messages.append(f"🤖 [Supervisor] 调度决策 → {next_agent}")

    return {
        "next_agent": next_agent,
        "messages": messages,
    }


def _route_to_agent(state: SupervisorState) -> str:
    """
    Supervisor 节点的条件边函数。

    读取 state["next_agent"]，返回对应的节点名称。
    LangGraph 会用这个返回值来决定下一步执行哪个节点。

    学习要点：
    - 条件边（Conditional Edge）是 LangGraph 的核心路由机制
    - 函数返回的字符串必须和 add_conditional_edges 的映射表匹配
    - "FINISH" 映射到 END，让流程结束
    """
    return state.get("next_agent", "FINISH")


def build_supervisor_graph(retriever: HybridRetriever, checkpointer=None):
    """
    构建并编译 Supervisor 多 Agent 工作流。

    参数:
        retriever: 混合检索器实例（注入到 Retrieval Agent）
        checkpointer: 检查点持久化器（HITL 模式必须提供）

    返回:
        编译好的 LangGraph 应用
    """
    # ========================================
    # 1. 创建 StateGraph
    # ========================================
    graph = StateGraph(SupervisorState)

    # ========================================
    # 2. 添加节点
    # ========================================

    # Supervisor 节点（调度中心）
    graph.add_node("supervisor", _supervisor_node)

    # 各专业 Agent 节点
    graph.add_node("intent_agent", intent_agent)

    # Retrieval Agent 需要注入 retriever 实例（用 functools.partial 绑定参数）
    search_node = partial(retrieval_agent, retriever=retriever)
    graph.add_node("retrieval_agent", search_node)

    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("reflection_agent", reflection_agent)
    graph.add_node("letter_agent", letter_agent)
    graph.add_node("judge_agent", judge_agent)

    # ========================================
    # 3. 连接边
    # ========================================

    # 入口 → Supervisor（Supervisor 决定第一个 Agent）
    graph.add_edge(START, "supervisor")

    # Supervisor → 条件边（根据 next_agent 路由到对应 Agent）
    graph.add_conditional_edges(
        "supervisor",
        _route_to_agent,
        {
            "intent": "intent_agent",
            "retrieval": "retrieval_agent",
            "analysis": "analysis_agent",
            "reflection": "reflection_agent",
            "letter": "letter_agent",
            "judge": "judge_agent",
            "FINISH": END,
        },
    )

    # 每个 Agent 执行完毕后回到 Supervisor
    # 这是 Supervisor 模式的关键设计：所有路径都经过调度中心
    graph.add_edge("intent_agent", "supervisor")
    graph.add_edge("retrieval_agent", "supervisor")
    graph.add_edge("analysis_agent", "supervisor")
    graph.add_edge("reflection_agent", "supervisor")
    graph.add_edge("letter_agent", "supervisor")
    graph.add_edge("judge_agent", "supervisor")

    # ========================================
    # 4. 编译图
    # ========================================
    app = graph.compile(checkpointer=checkpointer)

    mode = "LLM" if ROUTER_MODE == "llm" else "Rule-based"
    print(f"  [Supervisor] Graph compiled with {mode} router")

    return app
