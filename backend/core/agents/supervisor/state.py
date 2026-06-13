"""
心犀AI - Supervisor 多 Agent 状态定义
========================================
在原始 AgentState 基础上，添加 Supervisor 模式所需的额外字段。

学习要点：
---------
Supervisor 模式的核心思想：
  - 一个"调度者"节点（Supervisor）负责决定下一步执行哪个 Agent
  - 各专业 Agent 只关心自己的输入输出，不关心调度逻辑
  - 状态（State）是所有 Agent 共享的"黑板"（Blackboard）

为什么需要额外字段？
  - next_agent: Supervisor 用它告诉 LangGraph "下一个该谁上场"
  - agent_history: 记录哪些 Agent 已经执行过，便于分析和调试
  - current_agent: 当前正在执行的 Agent 名称，便于日志追踪
"""

from typing import TypedDict, Optional, Literal

from core.models.user_profile import UserProfile


# ============================================================
# Agent 名称的合法值（用于类型检查和路由映射）
# ============================================================

# 学习要点：Literal 类型可以限制字符串的取值范围
# 类似于其他语言的 enum，但更轻量，适合"有限选项"的场景
AgentName = Literal[
    "intent",       # 意图解析 Agent
    "retrieval",    # 混合检索 Agent
    "hitl",         # HITL 中断节点（Phase 3c 新增）
    "analysis",     # 深度分析 Agent
    "reflection",   # 策略反思 Agent
    "letter",       # 推荐信生成 Agent
    "judge",        # 质量评估 Agent
    "FINISH",       # 特殊值：流程结束
]


class SupervisorState(TypedDict, total=False):
    """
    Supervisor 多 Agent 工作流的共享状态。

    学习要点：
    ---------
    - TypedDict(total=False) 让所有字段都可选，每个 Agent 只需更新它关心的字段
    - 这个设计类似"黑板模式"（Blackboard Pattern）：
      所有 Agent 共享同一块"黑板"，各自读取和写入自己负责的部分
    - Supervisor 通过 next_agent 字段控制流程走向

    数据流概览：
      用户资料 → [intent] → hard_filters + rewritten_query
               → [retrieval] → candidates
               → [analysis] → analysis_results + best_score
               → [条件判断]
                  ├── 满意 → [letter] → top_matches + match_letters → [judge] → FINISH
                  └── 不满意 → [reflection] → retry_strategy → [retrieval]（重试）
    """

    # === 输入：用户画像（与原版相同）===
    user_profile: UserProfile

    # === Supervisor 调度字段（新增！）===
    next_agent: str
    """
    Supervisor 用这个字段告诉 LangGraph 下一个要执行的 Agent。
    例如 "retrieval" 表示下一个执行检索 Agent。
    值为 "FINISH" 时表示整个流程结束。
    """

    agent_history: list[str]
    """
    已执行的 Agent 列表，例如 ["intent", "retrieval", "analysis"]。
    用于调试、日志追踪，以及 Supervisor 的 LLM 路由决策。
    """

    current_agent: str
    """当前正在执行的 Agent 名称，便于在日志中标识来源。"""

    # === 意图解析输出（同原版）===
    hard_filters: dict
    rewritten_query: str

    # === 检索输出（同原版）===
    candidates: list[dict]

    # === 分析输出（同原版）===
    analysis_results: list[dict]
    best_score: float

    # === 循环控制（同原版）===
    loop_count: int
    should_retry: bool
    retry_strategy: str
    new_query: Optional[str]

    # === 最终输出（同原版）===
    top_matches: list[dict]
    match_letters: list[str]

    # === Human-in-the-loop 反馈 ===
    human_feedback_type: str
    """
    用户反馈类型：approve / reject / adjust
    在 HITL 模式下，Supervisor 根据此字段决定路由。
    """

    # === 评估输出（新增：Judge Agent 集成到图中）===
    evaluation: dict
    """
    Judge Agent 的评估结果，包含各维度分数和改进建议。
    原版是独立的 REST 端点，现在集成到图中自动执行。
    """

    # === 可观测性（Phase 3：LangFuse 追踪）===
    langfuse_trace_id: str
    """
    LangFuse 追踪 ID。
    在图执行开始前生成，存入 State，供 Judge Agent 上报评分时使用。
    格式：match_{user_id}_{timestamp}
    如果 LangFuse 未启用，此字段为空字符串。
    """

    # === Phase 3c：Agentic RAG 检索信息 ===
    retrieval_rounds: int
    """实际执行的检索轮次（1-3），用于展示给用户"""

    retrieval_note: str
    """检索条件说明（如"已放宽年龄范围"），在 HITL 预览时展示给用户"""

    # === Phase 3c：HITL（Human-in-the-Loop）===
    hitl_decision: dict
    """
    用户在 HITL 中断点的决策，由 interrupt() 返回值填充。
    格式：{"action": "proceed"}

    学习要点：
    - interrupt(payload) 的返回值来自外部的 Command(resume=value)
    - 这就是 LangGraph HITL 的信息传递机制：
      外部 → Command(resume=user_choice) → interrupt() 返回值 → state["hitl_decision"]
    """

    # === 调试信息 ===
    messages: list[str]
