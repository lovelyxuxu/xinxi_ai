"""
心犀AI - LangGraph Agent 状态定义
===================================
定义 Agent 在整个工作流中传递和更新的状态（State）。

学习要点：
---------
- LangGraph 的核心概念是 "State"（状态）——它是在各节点之间流动的数据容器
- 每个节点（Node）读取 State 中的信息，处理后再写回 State
- 使用 TypedDict 或 Pydantic 来定义 State 的结构
- 这种设计让你能清楚地看到每一步的输入输出，非常利于调试和学习

工作流程中的状态变化：
  用户资料 → [意图解析] → 硬性条件 + 搜索文本
           → [混合检索] → 候选人列表
           → [后分析]   → 评分排序
           → [条件判断] → 输出推荐信 / 返回重试
"""

from typing import TypedDict, Optional, Any
from src.models.user_profile import UserProfile


class AgentState(TypedDict, total=False):
    """
    Agent 工作流状态定义
    ---------------------
    使用 TypedDict 定义，total=False 表示所有字段都是可选的，
    这样每个节点只需要更新它关心的字段。
    """

    # === 输入：用户画像 ===
    user_profile: UserProfile       # 当前用户的完整画像

    # === 第一步：意图解析的输出 ===
    hard_filters: dict              # 提取的硬性过滤条件
    rewritten_query: str            # LLM 重写后的语义搜索文本

    # === 第二步：检索的输出 ===
    candidates: list[dict]          # 检索到的候选人列表

    # === 第三步：后分析的输出 ===
    analysis_results: list[dict]    # 每位候选人的评分和分析
    best_score: float               # 最高契合分数

    # === 第四步：循环控制 ===
    loop_count: int                 # 当前循环次数
    should_retry: bool              # 是否需要重试
    retry_strategy: str             # 重试策略: relax_age / relax_city / rewrite_query
    new_query: Optional[str]        # 重写后的新查询文本（如果是 rewrite_query 策略）

    # === 最终输出 ===
    top_matches: list[dict]         # 最终推荐的候选人（含评分和理由）
    match_letters: list[str]        # 生成的匹配推荐信

    # === 调试信息 ===
    messages: list[str]             # 每一步的日志消息，便于观察 Agent 的思考过程
