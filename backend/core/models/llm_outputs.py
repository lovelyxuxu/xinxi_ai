"""
心犀AI - LLM 结构化输出模型
================================
用 Pydantic 定义 LLM 返回的数据结构，配合 LangChain 的 with_structured_output() 使用。

学习要点：
---------
传统做法：
  1. 让 LLM 返回 JSON 字符串
  2. 手动 json.loads() 解析
  3. LLM 有时会返回非法 JSON，需要各种兜底处理

现代做法（本文件展示的）：
  1. 用 Pydantic 定义好输出结构
  2. 用 llm.with_structured_output(Model) 让 LangChain 自动处理
  3. LLM 直接返回 Pydantic 对象，类型安全，不需要手动解析

这是 LangChain 的 Structured Output 特性，底层会利用模型的 function calling 能力
来保证输出格式的一致性。
"""

from pydantic import BaseModel, Field
from typing import Optional


# ============================================================
# 意图解析节点的输出（parse_intent）
# ============================================================
class HardFilters(BaseModel):
    """硬性过滤条件：可以用结构化字段精确筛选的择偶要求"""
    target_gender: str = Field(description="期望对方性别：male 或 female")
    age_min: int = Field(description="期望对方最小年龄")
    age_max: int = Field(description="期望对方最大年龄")
    city: str = Field(description="期望对方城市，'不限'表示无限制")
    exclude_ids: list[str] = Field(
        default_factory=list,
        description="需要排除的用户ID列表（来自黑名单和历史推荐，可为空列表）",
    )


class IntentParseResult(BaseModel):
    """
    意图解析的完整输出。
    将用户感性的"我想找一个..."拆解为机器可理解的过滤条件 + 搜索文本。
    """
    hard_filters: HardFilters = Field(description="硬性过滤条件")
    rewritten_query: str = Field(
        description="重写后的语义搜索文本，用于向量检索，应涵盖性格、兴趣、生活方式等维度"
    )


# ============================================================
# 后分析节点的输出（post_analysis）
# ============================================================
class CandidateAnalysis(BaseModel):
    """单个候选人的分析结果"""
    user_id: str = Field(description="候选人ID")
    nickname: str = Field(description="候选人昵称")
    score: int = Field(
        ge=0, le=100,
        description="契合指数（0-100），综合考量性格、兴趣、价值观等维度"
    )
    reason: str = Field(description="匹配理由（2-3句话，聚焦三观和兴趣的契合点）")


class AnalysisResultList(BaseModel):
    """所有候选人的分析结果列表"""
    candidates: list[CandidateAnalysis] = Field(
        description="每位候选人的分析结果，按契合度从高到低排列"
    )


# ============================================================
# 反思节点的输出（reflection）
# ============================================================
class ReflectionResult(BaseModel):
    """
    Agent 反思的结果。
    当匹配结果不理想时，分析原因并选择改进策略。
    """
    analysis: str = Field(description="简要分析当前匹配不佳的原因")
    strategy: str = Field(
        description="调整策略：relax_age（放宽年龄）/ relax_city（放宽地域）/ rewrite_query（重写搜索文本）"
    )
    new_query: Optional[str] = Field(
        default=None,
        description="如果 strategy 为 rewrite_query，提供新的搜索文本；否则为 null"
    )


# ============================================================
# 用户访谈节点的输出（interview Subgraph）
# ============================================================
class InterviewExtraction(BaseModel):
    """
    访谈内容提取结果。
    从用户的自然语言回复中提取画像字段，并判断访谈是否可以结束。
    """
    updated_fields: dict = Field(
        description="从回复中提取的字段及更新值（如 {'hobbies': '摄影, 旅行'}）"
    )
    is_complete: bool = Field(
        description="是否已收集足够信息完成访谈"
    )
    analysis: str = Field(
        description="对当前访谈进度的简要分析（还差什么，或者为什么可以结束了）"
    )


# ============================================================
# Phase 7: LLM-as-Judge 匹配质量评估
# ============================================================
class MatchDimensionScore(BaseModel):
    """单个评估维度的得分"""
    dimension: str = Field(description="评估维度名称")
    score: int = Field(ge=1, le=10, description="该维度得分（1-10）")
    comment: str = Field(description="对该维度的简要评价")


class MatchEvaluation(BaseModel):
    """
    LLM-as-Judge 匹配质量评估结果。

    学习要点：
    ---------
    LLM-as-Judge 是一种用 LLM 来评估另一个 LLM 输出质量的技术。
    在 RAG/Agent 系统中非常有用，可以自动化地评估：
    - 检索结果是否相关
    - 推荐是否合理
    - 解释是否有说服力
    """
    overall_score: int = Field(
        ge=1, le=10,
        description="整体匹配质量评分（1-10）"
    )
    dimensions: list[MatchDimensionScore] = Field(
        description="各维度的详细评分"
    )
    strengths: str = Field(description="本次匹配的主要优点")
    weaknesses: str = Field(description="本次匹配的主要不足")
    suggestion: str = Field(description="改进建议（如何优化匹配策略）")

