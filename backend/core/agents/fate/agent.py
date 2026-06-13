"""
FateAnalysisAgent - 缘分分析 Agent。

架构说明（LangGraph 学习要点）：
=================================
本 Agent 使用 LangGraph 实现两层分析流程：

第一层（group_overview）：
  START → compute_compatibility → generate_overview → END

第二层（deep/comm/comparison）：
  START → compute_compatibility → [路由] →
  generate_deep_compatibility / generate_comm_advice / generate_comparison → END

核心技术：
- StateGraph：定义 Agent 的状态机，每个节点是一个处理函数
- TypedDict State：强类型状态定义，每个节点读取并返回状态
- Tool Calling（直接调用）：compute_compatibility 节点直接调用工具
- LLM 生成叙事报告：LLM 接收结构化兼容性数据，输出 JSON 报告
- 条件边（Conditional Edge）：根据 analysis_type 路由到不同节点
- 异步执行：所有 LLM 调用均为 async，支持并发请求

Agent 状态设计：
- FateAnalysisState：TypedDict，贯穿整个图的执行过程
- 每个节点返回 {**state, 更新的字段}（不可变更新模式）
"""
from __future__ import annotations

import json
import logging
from typing import TypedDict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from core.agents.fate.tools import (
    calc_zodiac_compatibility,
    calc_chinese_zodiac_compatibility,
    calc_mbti_compatibility,
    get_tarot_for_fate,
)
from core.utils.llm_factory import create_ll

logger = logging.getLogger(__name__)


# ── Agent 状态定义 ────────────────────────────────────────────

class FateAnalysisState(TypedDict):
    """
    Agent 执行过程中的完整状态。

    LangGraph 学习要点：
    - TypedDict 保证每个字段的类型安全
    - 图中的每个节点都接收完整状态，返回部分更新
    - 使用 {**state, "new_field": value} 实现不可变更新
    """
    analysis_id: str
    analysis_type: str      # group_overview / deep_compatibility / comm_advice / comparison
    initiator: dict         # 发起者用户数据（to_dict() 输出）
    candidates: list        # 候选者用户数据列表
    match_params: dict      # 偏好参数（可空）

    compat_results: list    # 每位候选者的兼容性计算结果

    overview_result: Optional[dict]   # 第一层：全量洞察
    final_report: Optional[dict]      # 最终输出（各节点写入）
    error: Optional[str]


# ── 工具节点：计算兼容性数据 ─────────────────────────────────

def compute_compatibility(state: FateAnalysisState) -> dict:
    """
    节点1：为每位候选者调用工具计算星座/属相/MBTI 兼容性。

    学习要点：
    - 这里直接调用 LangChain Tools（非通过 LLM 请求），效率更高
    - .invoke({...}) 是同步调用工具的标准方式
    - LLM 在后续节点中将这些结构化数据转化为自然语言报告
    - 部分评分计算在此处完成，为 LLM 提供客观依据
    """
    initiator = state["initiator"]
    results = []

    for candidate in state["candidates"]:
        compat: dict = {
            "candidate_id": candidate.get("user_id", ""),
            "candidate_name": candidate.get("nickname", ""),
        }

        # 西方星座兼容性
        if initiator.get("zodiac_sign") and candidate.get("zodiac_sign"):
            try:
                z_result = calc_zodiac_compatibility.invoke({
                    "zodiac_a": initiator["zodiac_sign"],
                    "zodiac_b": candidate["zodiac_sign"],
                })
                compat["zodiac"] = z_result
            except Exception as e:
                logger.warning(f"zodiac calc error: {e}")

        # 属相兼容性
        if initiator.get("chinese_zodiac") and candidate.get("chinese_zodiac"):
            try:
                cz_result = calc_chinese_zodiac_compatibility.invoke({
                    "zodiac_a": initiator["chinese_zodiac"],
                    "zodiac_b": candidate["chinese_zodiac"],
                })
                compat["chinese_zodiac"] = cz_result
            except Exception as e:
                logger.warning(f"chinese zodiac calc error: {e}")

        # MBTI 兼容性
        if initiator.get("mbti") and candidate.get("mbti") and initiator["mbti"] != "未知" and candidate["mbti"] != "未知":
            try:
                m_result = calc_mbti_compatibility.invoke({
                    "mbti_a": initiator["mbti"],
                    "mbti_b": candidate["mbti"],
                })
                compat["mbti"] = m_result
            except Exception as e:
                logger.warning(f"mbti calc error: {e}")

        # 塔罗牌（group_overview 和 deep_compatibility 时生成）
        if state["analysis_type"] in ("group_overview", "deep_compatibility"):
            if initiator.get("zodiac_sign") and candidate.get("zodiac_sign"):
                try:
                    tarot = get_tarot_for_fate.invoke({
                        "initiator_zodiac": initiator["zodiac_sign"],
                        "candidate_zodiac": candidate["zodiac_sign"],
                    })
                    compat["tarot"] = tarot
                except Exception as e:
                    logger.warning(f"tarot calc error: {e}")

        # 综合初步评分（加权，LLM 后续会给出完整分）
        scores = []
        weights = []
        if "zodiac" in compat:
            scores.append(compat["zodiac"].get("score", 70) * 0.20)
            weights.append(0.20)
        if "chinese_zodiac" in compat:
            scores.append(compat["chinese_zodiac"].get("score", 70) * 0.20)
            weights.append(0.20)
        if "mbti" in compat:
            scores.append(compat["mbti"].get("score", 70) * 0.30)
            weights.append(0.30)

        # 基础条件分（年龄/城市）
        basic_score = _calc_basic_score(initiator, candidate)
        scores.append(basic_score * 0.30)
        weights.append(0.30)

        total_weight = sum(weights)
        compat["partial_score"] = round(sum(scores) / total_weight) if total_weight > 0 else 70
        results.append(compat)

    # 按 partial_score 降序排列
    results.sort(key=lambda x: x.get("partial_score", 0), reverse=True)
    return {**state, "compat_results": results}


def _calc_basic_score(initiator: dict, candidate: dict) -> int:
    """基础条件匹配评分（年龄/城市/身高）。"""
    score = 70
    age = candidate.get("age", 0)
    if age and initiator.get("target_age_min") and initiator.get("target_age_max"):
        if initiator["target_age_min"] <= age <= initiator["target_age_max"]:
            score += 15
        else:
            score -= 15
    if initiator.get("target_city") and initiator["target_city"] != "不限":
        if candidate.get("city") == initiator["target_city"]:
            score += 10
    return min(100, max(0, score))


def _safe_parse_json(content: str) -> dict:
    """安全解析 LLM 输出的 JSON，处理 markdown 代码块等情况。"""
    # 去除 markdown 代码块标记
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 提取第一个完整 JSON 对象
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
    return {"raw": content, "parse_error": True}


# ── 节点：生成群体洞察报告 ────────────────────────────────────

async def generate_overview(state: FateAnalysisState) -> dict:
    """
    节点2（group_overview）：LLM 生成全量洞察报告。

    学习要点：
    - SystemMessage 设定 AI 角色和输出格式约束
    - HumanMessage 传入结构化兼容性数据（tools 计算的结果）
    - LLM 将数字评分转化为有温度的文字洞察
    - temperature=0.8：适度创造性，让每次报告略有差异
    """
    llm = get_llm(temperature=0.8, streaming=False)

    initiator = state["initiator"]
    compat_data = state["compat_results"]

    system_prompt = """你是「心犀」AI 红娘，专业分析两人的缘分契合度。
分析风格：温暖有趣，融合现代玄学感（星座、属相、MBTI），给出真诚而有洞见的建议。
输出要求：返回纯 JSON（不要 markdown 代码块），结构如下：
{
  "initiator_insight": "对用户本人择偶偏好的洞察（80字内）",
  "candidates": [
    {
      "candidate_id": "user_id",
      "candidate_name": "昵称",
      "overall_score": 85,
      "headline": "一句话概括缘分（15字内，有趣有温度）",
      "zodiac_note": "星座分析（30字内）",
      "chinese_zodiac_note": "属相分析（30字内）",
      "mbti_note": "MBTI分析（30字内）",
      "energy_color": "#667eea",
      "tarot_card": "恋人",
      "tarot_emoji": "💑",
      "tarot_reading": "塔罗解读（25字内）",
      "pros": ["优势1", "优势2", "优势3"],
      "summary": "综合缘分小结（60字内）"
    }
  ],
  "top_recommendation": "最推荐的候选者user_id",
  "recommendation_reason": "推荐理由（40字内）"
}"""

    user_data = json.dumps({
        "initiator": {
            "nickname": initiator.get("nickname"),
            "age": initiator.get("age"),
            "zodiac_sign": initiator.get("zodiac_sign"),
            "chinese_zodiac": initiator.get("chinese_zodiac"),
            "mbti": initiator.get("mbti"),
            "about_me": (initiator.get("about_me") or "")[:200],
            "ideal_partner": (initiator.get("ideal_partner") or "")[:200],
        },
        "compatibility_data": compat_data,
    }, ensure_ascii=False)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请分析以下缘分数据：\n{user_data}"),
        ])
        report = _safe_parse_json(response.content)
    except Exception as e:
        logger.error(f"generate_overview LLM error: {e}")
        report = {
            "error": str(e),
            "candidates": [
                {
                    "candidate_id": r.get("candidate_id"),
                    "candidate_name": r.get("candidate_name"),
                    "overall_score": r.get("partial_score", 70),
                    "headline": "缘分待续探索",
                    "pros": ["正在计算中"],
                    "summary": "AI 分析暂时不可用，请稍后重试",
                }
                for r in compat_data
            ],
        }

    return {**state, "overview_result": report, "final_report": report}


# ── 节点：深度相性分析 ────────────────────────────────────────

async def generate_deep_compatibility(state: FateAnalysisState) -> dict:
    """节点：深度相性分析（爱情语言/价值观/潜在摩擦点）。"""
    llm = get_llm(temperature=0.8, streaming=False)

    initiator = state["initiator"]
    candidates = state["candidates"]
    compat_data = state["compat_results"]

    system_prompt = """你是专业的爱情分析师，深度分析两人的相性。
输出纯 JSON：
{
  "analyses": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "love_language": {
        "initiator_likely": "肯定言辞",
        "candidate_likely": "精心时刻"
      },
      "compatibility_matrix": {
        "personality": {"score": 85, "note": "简洁说明"},
        "values": {"score": 80, "note": "简洁说明"},
        "lifestyle": {"score": 75, "note": "简洁说明"},
        "communication": {"score": 82, "note": "简洁说明"}
      },
      "friction_points": ["潜在摩擦点1", "潜在摩擦点2"],
      "growth_potential": "这段关系能带给彼此的成长（40字）",
      "final_verdict": "深度总结（80字，真诚不浮夸）"
    }
  ]
}"""

    user_data = json.dumps({
        "initiator": {k: initiator.get(k) for k in ["nickname", "age", "zodiac_sign", "chinese_zodiac", "mbti", "about_me", "ideal_partner", "hobbies"]},
        "candidates": [
            {k: c.get(k) for k in ["user_id", "nickname", "age", "zodiac_sign", "chinese_zodiac", "mbti", "about_me", "hobbies"]}
            for c in candidates
        ],
        "compat_data": compat_data,
    }, ensure_ascii=False, default=str)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请进行深度相性分析：\n{user_data}"),
        ])
        report = _safe_parse_json(response.content)
    except Exception as e:
        logger.error(f"generate_deep_compatibility error: {e}")
        report = {"error": str(e), "analyses": []}

    return {**state, "final_report": report}


# ── 节点：沟通建议 ────────────────────────────────────────────

async def generate_comm_advice(state: FateAnalysisState) -> dict:
    """节点：生成具体的破冰句和约会建议。"""
    llm = get_llm(temperature=0.9, streaming=False)

    initiator = state["initiator"]
    candidates = state["candidates"]

    system_prompt = """你是机智幽默的约会顾问，给出实用又有趣的破冰建议。
输出纯 JSON：
{
  "advices": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "opening_lines": ["破冰第一句1（结合对方兴趣）", "破冰第一句2", "破冰第一句3"],
      "date_ideas": ["约会场景1", "约会场景2"],
      "topics_to_avoid": ["避免的话题"],
      "topics_to_explore": ["推荐深聊的话题"],
      "timing_tip": "最佳联系时机（20字）"
    }
  ]
}"""

    user_data = json.dumps({
        "initiator": {k: initiator.get(k) for k in ["nickname", "mbti", "hobbies", "about_me"]},
        "candidates": [
            {k: c.get(k) for k in ["user_id", "nickname", "mbti", "hobbies", "about_me"]}
            for c in candidates
        ],
    }, ensure_ascii=False)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请给出沟通建议：\n{user_data}"),
        ])
        report = _safe_parse_json(response.content)
    except Exception as e:
        logger.error(f"generate_comm_advice error: {e}")
        report = {"error": str(e), "advices": []}

    return {**state, "final_report": report}


# ── 节点：横向对比 ────────────────────────────────────────────

async def generate_comparison(state: FateAnalysisState) -> dict:
    """节点：生成多候选者横向对比报告。"""
    llm = get_llm(temperature=0.7, streaming=False)

    initiator = state["initiator"]
    candidates = state["candidates"]
    compat_data = state["compat_results"]

    system_prompt = """你是数据分析师，用对比表格形式呈现候选者综合分析。
输出纯 JSON：
{
  "dimensions": ["性格匹配", "兴趣共鸣", "价值观", "星座相性", "MBTI相性", "地理距离", "发展潜力"],
  "candidates": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "scores": {
        "性格匹配": {"score": 85, "note": "简洁"},
        "兴趣共鸣": {"score": 80, "note": "简洁"},
        "价值观": {"score": 82, "note": "简洁"},
        "星座相性": {"score": 75, "note": "简洁"},
        "MBTI相性": {"score": 90, "note": "简洁"},
        "地理距离": {"score": 95, "note": "简洁"},
        "发展潜力": {"score": 88, "note": "简洁"}
      },
      "total_score": 85,
      "unique_advantage": "这个人最突出的优势（20字）"
    }
  ],
  "winner": "综合最佳候选者user_id",
  "winner_reason": "推荐理由（30字）"
}"""

    user_data = json.dumps({
        "initiator": {k: initiator.get(k) for k in ["nickname", "mbti", "zodiac_sign", "city"]},
        "candidates": [
            {k: c.get(k) for k in ["user_id", "nickname", "mbti", "zodiac_sign", "city", "hobbies"]}
            for c in candidates
        ],
        "compat_data": compat_data,
    }, ensure_ascii=False, default=str)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请生成对比分析：\n{user_data}"),
        ])
        report = _safe_parse_json(response.content)
    except Exception as e:
        logger.error(f"generate_comparison error: {e}")
        report = {"error": str(e), "candidates": []}

    return {**state, "final_report": report}


# ── 路由函数 ──────────────────────────────────────────────────

def route_analysis_type(state: FateAnalysisState) -> str:
    """
    条件边路由函数：根据 analysis_type 决定下一个节点。

    LangGraph 学习要点：
    - add_conditional_edges 的第二个参数是"路由函数"
    - 路由函数接收当前状态，返回下一个节点名称（字符串）
    - 第三个参数是路由映射表（可能的返回值 → 节点名）
    """
    routing = {
        "group_overview": "generate_overview",
        "deep_compatibility": "generate_deep_compatibility",
        "comm_advice": "generate_comm_advice",
        "comparison": "generate_comparison",
    }
    return routing.get(state["analysis_type"], "generate_overview")


# ── 构建并编译 LangGraph ──────────────────────────────────────

def build_fate_graph():
    """
    构建缘分分析状态机。

    LangGraph 学习要点：
    - StateGraph(FateAnalysisState)：创建以 FateAnalysisState 为状态的图
    - add_node(name, func)：添加节点，func 接收 state 返回更新
    - add_conditional_edges：根据函数返回值决定下一个节点
    - set_entry_point：设置入口节点
    - add_edge(a, b)：添加有向边（a → b）
    - compile()：编译为可执行 Runnable，支持 invoke/ainvoke/stream
    """
    graph = StateGraph(FateAnalysisState)

    # 注册节点
    graph.add_node("compute_compatibility", compute_compatibility)
    graph.add_node("generate_overview", generate_overview)
    graph.add_node("generate_deep_compatibility", generate_deep_compatibility)
    graph.add_node("generate_comm_advice", generate_comm_advice)
    graph.add_node("generate_comparison", generate_comparison)

    # 入口：compute_compatibility
    graph.set_entry_point("compute_compatibility")

    # 条件边：兼容性计算完成后，按 analysis_type 路由
    graph.add_conditional_edges(
        "compute_compatibility",
        route_analysis_type,
        {
            "generate_overview": "generate_overview",
            "generate_deep_compatibility": "generate_deep_compatibility",
            "generate_comm_advice": "generate_comm_advice",
            "generate_comparison": "generate_comparison",
        },
    )

    # 所有分析节点 → END
    for node_name in [
        "generate_overview",
        "generate_deep_compatibility",
        "generate_comm_advice",
        "generate_comparison",
    ]:
        graph.add_edge(node_name, END)

    return graph.compile()


# 全局图实例（单例，避免重复编译带来的开销）
fate_graph = build_fate_graph()


# ── 对外接口 ──────────────────────────────────────────────────

async def run_fate_analysis(
    analysis_id: str,
    analysis_type: str,
    initiator: dict,
    candidates: list,
    match_params: dict | None = None,
) -> dict:
    """
    运行缘分分析，返回完整报告。

    Args:
        analysis_id: 分析记录 ID（用于追踪）
        analysis_type: 分析类型（group_overview/deep_compatibility/comm_advice/comparison）
        initiator: 发起者用户数据（User.to_dict() 输出）
        candidates: 候选者用户数据列表
        match_params: 临时覆盖的偏好参数（可空）

    Returns:
        final_report: dict（缘分分析报告，结构因 analysis_type 不同而异）
    """
    initial_state: FateAnalysisState = {
        "analysis_id": analysis_id,
        "analysis_type": analysis_type,
        "initiator": initiator,
        "candidates": candidates,
        "match_params": match_params or {},
        "compat_results": [],
        "overview_result": None,
        "final_report": None,
        "error": None,
    }

    try:
        final_state = await fate_graph.ainvoke(initial_state)
        return final_state.get("final_report") or {}
    except Exception as e:
        logger.error(f"FateAnalysisAgent error: {e}", exc_info=True)
        return {"error": str(e), "analysis_id": analysis_id}
