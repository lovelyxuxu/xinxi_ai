"""
心犀AI - 混合检索 Agent（Phase 3c 升级：Agentic RAG 3轮自适应循环）
====================================================================
执行硬性过滤 + 向量相似度搜索，从 Chroma 中检索候选人。

学习要点：
---------
Phase 3c 之前的版本：
  - retrieval_agent 只做一次检索
  - 如果结果不足，等 reflection_agent 触发重试（外部循环）
  - 问题：循环决策权在外部，retrieval_agent 没有自主判断能力

Phase 3c 改造（Agentic RAG）：
  - retrieval_agent 内置 3 轮循环，自主决定是否放宽条件
  - 这就是 "Agentic" 的含义：Agent 能感知环境（候选人不足），
    主动采取行动（放宽条件），不需要外部驱动

  Agentic RAG vs Naive RAG 对比：
  ┌─────────────────────────────────────────────────────────────┐
  │ Naive RAG：                                                  │
  │   查询 → 检索 → 返回结果（一次性，不管质量好不好）            │
  │                                                             │
  │ Agentic RAG：                                               │
  │   查询 → 检索 → 评估质量 → 不够好? → 调整策略 → 再检索       │
  │          ↑_______________________________|（最多 N 轮）      │
  └─────────────────────────────────────────────────────────────┘

3轮循环策略：
  ┌────────────────────────────────────────────────────────────┐
  │ 第1轮: 原始条件检索                                        │
  │   候选人 ≥ 3 → 返回（高质量结果）                          │
  │   候选人 < 3 → 触发第2轮                                   │
  ├────────────────────────────────────────────────────────────┤
  │ 第2轮: 年龄范围 ±5 岁（更宽容）                             │
  │   候选人 ≥ 3 → 返回，附 retrieval_note 说明                │
  │   候选人 < 3 → 触发第3轮                                   │
  ├────────────────────────────────────────────────────────────┤
  │ 第3轮: 忽略城市限制（全国范围）                              │
  │   直接返回，附 retrieval_note 说明                         │
  └────────────────────────────────────────────────────────────┘

与 reflection_agent 职责的变化：
  - Phase 3c 之前：reflection_agent 负责「是否重试」的决策
  - Phase 3c 之后：reflection_agent 专注于「结果质量最终评估」
    （是否达到推荐信生成的门槛）
"""

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.retrieval.hybrid_retriever import HybridRetriever

# 候选人数量的最低门槛（少于此值触发放宽条件）
_MIN_CANDIDATES = 3


def retrieval_agent(state: SupervisorState, retriever: HybridRetriever) -> dict:
    """
    混合检索 Agent（Agentic RAG 版）：自适应多轮检索。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - rewritten_query: 语义搜索文本（来自 Intent Agent）
        - hard_filters: 硬性过滤条件（来自 Intent Agent，可能含 exclude_ids）
        - loop_count: 外部反思循环次数（兼容 reflection_agent 的重试机制）

    输出（写回 State）：
        - candidates: 候选人列表
        - retrieval_rounds: 实际执行的轮次（1、2 或 3）
        - retrieval_note: 给用户看的条件说明（如"已放宽年龄范围"）
        - next_agent: "hitl"（Phase 3c 新增：先进 HITL 节点等待确认）

    注意：此函数仍然是同步的（sync），因为 HybridRetriever 是同步的。
    LangGraph 会自动在线程池中运行同步节点函数，不影响异步图的执行。
    """
    user = state["user_profile"]
    query_text = state["rewritten_query"]
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    hard_filters = state.get("hard_filters", {})

    messages.append("📋 [Retrieval Agent] 开始 Agentic RAG 检索...")

    # 从 Intent Agent 可能传来的 exclude_ids 中获取排除列表
    # 学习要点：工具调用的结果通过 hard_filters 间接传递
    # LLM 在 intent_agent 中调用工具后，会把 exclude_ids 填入 hard_filters
    exclude_ids: list[str] = hard_filters.get("exclude_ids", [])
    if exclude_ids:
        messages.append(f"   排除 {len(exclude_ids)} 个历史/黑名单用户")

    # 外部 reflection 循环触发时也使用 relaxed 模式（向后兼容原版逻辑）
    loop_count = state.get("loop_count", 0)

    retrieval_note = ""
    candidates: list[dict] = []
    actual_rounds = 0

    def _filter_excluded(cands: list[dict]) -> list[dict]:
        """过滤掉 exclude_ids 中的用户"""
        if not exclude_ids:
            return cands
        return [c for c in cands if c.get("user_id", "") not in exclude_ids]

    # ========================================
    # Agentic RAG 3轮循环
    # 学习要点：这个循环是"自主"的关键——
    # Agent 自己决定是否需要继续检索，而不是等外部告知
    # ========================================

    # 第1轮：原始条件检索
    actual_rounds = 1
    messages.append("   [第1轮] 使用原始条件检索...")
    candidates = retriever.retrieve(
        user=user,
        query_text=query_text,
        n_results=match_config.max_candidates,
        relaxed=(loop_count > 0),
        hard_filters=hard_filters,
    )
    candidates = _filter_excluded(candidates)
    messages.append(f"   [第1轮] 找到 {len(candidates)} 位候选人")

    if len(candidates) >= _MIN_CANDIDATES:
        messages.append("   ✓ 候选人充足，无需放宽条件")

    else:
        # 第2轮：放宽年龄范围 ±5 岁
        actual_rounds = 2
        messages.append(
            f"   候选人不足（< {_MIN_CANDIDATES}），触发第2轮：放宽年龄范围 ±5 岁"
        )

        relaxed_filters = dict(hard_filters)
        if "age_min" in relaxed_filters:
            relaxed_filters["age_min"] = max(18, relaxed_filters["age_min"] - 5)
        if "age_max" in relaxed_filters:
            relaxed_filters["age_max"] = min(60, relaxed_filters["age_max"] + 5)

        candidates = retriever.retrieve(
            user=user,
            query_text=query_text,
            n_results=match_config.max_candidates,
            relaxed=True,
            hard_filters=relaxed_filters,
        )
        candidates = _filter_excluded(candidates)
        messages.append(f"   [第2轮] 找到 {len(candidates)} 位候选人")

        if len(candidates) >= _MIN_CANDIDATES:
            retrieval_note = "已自动放宽年龄范围 ±5 岁，为你找到更多缘分候选人"
            messages.append("   ✓ 放宽年龄后候选人充足")

        else:
            # 第3轮：忽略城市限制，全国范围检索
            actual_rounds = 3
            messages.append("   候选人仍不足，触发第3轮：忽略城市限制（全国范围）")

            widest_filters = dict(hard_filters)
            widest_filters.pop("city", None)   # 移除城市限制
            widest_filters["age_min"] = max(18, widest_filters.get("age_min", 18) - 5)
            widest_filters["age_max"] = min(60, widest_filters.get("age_max", 45) + 5)

            candidates = retriever.retrieve(
                user=user,
                query_text=query_text,
                n_results=match_config.max_candidates,
                relaxed=True,
                hard_filters=widest_filters,
            )
            candidates = _filter_excluded(candidates)
            messages.append(f"   [第3轮] 找到 {len(candidates)} 位候选人")
            retrieval_note = "已大范围放宽搜索条件（年龄 ±5 岁 + 全国范围），为你找到更多缘分候选人"

    messages.append(
        f"   ✓ 检索完成：{len(candidates)} 位候选人（{actual_rounds} 轮"
        + (f"，{retrieval_note}" if retrieval_note else "，条件未放宽")
        + "）"
    )

    return {
        "candidates": candidates,
        "retrieval_rounds": actual_rounds,
        "retrieval_note": retrieval_note,
        "messages": messages,
        # Phase 3c: 检索完成后先进 HITL 节点等待用户确认
        # 学习要点：retrieval_agent 声明"下一步去 hitl"，
        # 但最终路由决策由 supervisor/router.py 的 rule_based_router 执行
        "next_agent": "hitl",
        "agent_history": history + ["retrieval"],
        "current_agent": "retrieval",
    }
