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
from langgraph.types import interrupt

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


def _hitl_node(state: SupervisorState) -> dict:
    """
    HITL（Human-in-the-Loop）中断节点。

    学习要点（重点！）：
    ---------
    1. interrupt(payload) 的工作原理：
       - 调用时，LangGraph 立即暂停图的执行
       - 当前完整的 State 被 Checkpointer 存储到 SQLite（thread_id 为 key）
       - payload 被包装为 Interrupt 对象，通过
         graph.get_state(config).tasks[0].interrupts 暴露给外部调用者
       - 图处于 "suspended" 状态，等待外部 resume

    2. Command(resume=value) 的工作原理：
       - 外部调用 graph.ainvoke(Command(resume=value), config=config)
       - LangGraph 从 Checkpointer 恢复 State
       - interrupt() 调用点返回 value（即 Command 中的 resume 值）
       - 图继续执行

    3. 为什么需要 Checkpointer？
       - 中断发生时，图需要知道从哪里恢复
       - Checkpointer 保存了"当前执行到哪个节点"的快照
       - 没有 Checkpointer 就无法实现 HITL（图不知道如何恢复）
       - 本项目使用 AsyncSqliteSaver（已在 deps.py 中初始化）

    数据流：
      retrieval_agent 完成
        → Supervisor 路由到 hitl_node
        → hitl_node 调用 interrupt(候选人预览数据)
        → 图暂停，外部可读取预览数据（通过 SSE 推送给前端）
        → 用户点击"开始深度分析"
        → 后端调用 Command(resume={"action": "proceed"})
        → interrupt() 返回 {"action": "proceed"}
        → hitl_node 完成，设置 next_agent="analysis"
        → Supervisor 路由到 analysis_agent
    """
    candidates = state.get("candidates", [])
    retrieval_note = state.get("retrieval_note", "")
    messages = state.get("messages", [])
    history = state.get("agent_history", [])

    # 构建候选人预览数据（精简版，只包含前端需要展示的字段）
    preview = []
    for c in candidates[:8]:  # 最多展示 8 个候选人
        preview.append({
            "user_id": c.get("user_id", ""),
            "nickname": c.get("nickname", ""),
            "age": c.get("age", 0),
            "city": c.get("city", ""),
            "avatar_url": c.get("avatar_url", None),
            "score": c.get("score", 0),
        })

    messages.append(
        f"⏸ [HITL] 等待用户确认 {len(preview)} 位候选人预览..."
    )

    # 中断！向外暴露候选人预览数据，等待用户操作
    # 学习要点：interrupt() 的参数会被序列化到 Checkpointer 中
    # 外部通过 graph.aget_state(config).tasks[0].interrupts[0].value 读取
    user_decision = interrupt({
        "type": "hitl_preview",
        "candidates": preview,
        "retrieval_note": retrieval_note,
        "candidate_count": len(candidates),
    })

    # 恢复执行（用户已点击"开始深度分析"）
    messages.append(
        f"▶ [HITL] 用户确认：{user_decision.get('action', 'proceed')}，开始深度分析"
    )

    return {
        "hitl_decision": user_decision,
        "messages": messages,
        "next_agent": "analysis",  # HITL 完成后交给深度分析
        "agent_history": history + ["hitl"],
        "current_agent": "hitl",
    }


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

    # Phase 3c: HITL 节点（在 retrieval 完成后等待用户确认）
    graph.add_node("hitl_node", _hitl_node)

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
            "hitl": "hitl_node",        # Phase 3c: HITL 节点
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
    graph.add_edge("hitl_node", "supervisor")   # Phase 3c: HITL 完成后回到 Supervisor
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
