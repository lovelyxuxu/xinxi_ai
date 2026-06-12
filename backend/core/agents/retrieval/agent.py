"""
心犀AI - 混合检索 Agent
=========================
执行硬性过滤 + 向量相似度搜索，从 Chroma 中检索候选人。

学习要点：
---------
本 Agent 是整个流程中唯一不涉及 LLM 调用的节点——它是纯粹的"数据操作"。
但它仍然是 Agent 架构中的独立模块，因为：
  1. 它有自己的输入输出契约（State schema）
  2. 它可以被 Supervisor 独立调度（包括重试时再次调度）
  3. 未来可能引入更智能的检索策略（如 LLM 辅助的查询扩展）

本 Agent 对应原版 nodes.py 中的 hybrid_search 节点。
"""

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.retrieval.hybrid_retriever import HybridRetriever


def retrieval_agent(state: SupervisorState, retriever: HybridRetriever) -> dict:
    """
    混合检索 Agent：硬性过滤 + 向量相似度搜索。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - rewritten_query: 语义搜索文本（来自 Intent Agent）
        - hard_filters: 硬性过滤条件（来自 Intent Agent）
        - loop_count: 当前循环次数（>0 时启用放宽模式）
        - retry_strategy: 重试策略（rewrite_query 时使用新查询）
        - new_query: 重写后的查询文本

    输出（写回 State）：
        - candidates: 候选人列表
        - next_agent: "analysis"（检索完后交给分析 Agent）

    注意：此函数需要外部注入 retriever 实例（通过 functools.partial 绑定）。
    """
    user = state["user_profile"]
    query_text = state["rewritten_query"]
    loop_count = state.get("loop_count", 0)
    retry_strategy = state.get("retry_strategy", "")
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append("📋 [Retrieval Agent] 执行混合检索...")

    # 从状态中获取 LLM 提取的硬性过滤条件
    hard_filters = state.get("hard_filters")
    if hard_filters:
        messages.append(f"   使用 LLM 提取的硬性条件: {hard_filters}")

    # 决定是否放宽条件（Agent 反思循环中使用）
    relaxed = loop_count > 0

    # 如果是重试且策略是 rewrite_query，使用新查询文本
    if retry_strategy == "rewrite_query" and state.get("new_query"):
        query_text = state["new_query"]
        messages.append("   使用重写后的搜索文本")

    # 执行检索（传入 hard_filters 让 LLM 的智能分析生效）
    candidates = retriever.retrieve(
        user=user,
        query_text=query_text,
        n_results=match_config.max_candidates,
        relaxed=relaxed,
        hard_filters=hard_filters,
    )

    messages.append(f"   检索到 {len(candidates)} 位候选人 (relaxed={relaxed})")

    return {
        "candidates": candidates,
        "messages": messages,
        # Supervisor 调度字段
        "next_agent": "analysis",    # 检索完成后，下一步是深度分析
        "agent_history": history + ["retrieval"],
        "current_agent": "retrieval",
    }
