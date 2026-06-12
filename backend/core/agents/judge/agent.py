"""
心犀AI - 质量评估 Agent（Judge）
====================================
使用 LLM-as-Judge 评估匹配推荐的质量。

学习要点：
---------
LLM-as-Judge 是一种越来越流行的评估方法：
  - 用一个 LLM 来"打分"另一个 LLM 的输出
  - 类似于人类评审，但自动化、可规模化
  - 特别适合评估"开放式"输出（如推荐信、匹配理由）的质量

评估维度：
  1. 相关性 (relevance): 候选人是否真的符合用户的择偶要求
  2. 契合度 (compatibility): 候选人与用户在性格、兴趣、价值观方面的匹配程度
  3. 解释力 (explanation): 匹配理由是否具体、有说服力、不空泛
  4. 一致性 (consistency): 评分和理由是否自洽
  5. 温度感 (warmth): 推荐信是否有温度、是否打动人心

在原版中，Judge 是一个独立的 REST 端点（POST /api/match/evaluate/{match_id}）。
现在集成到 Supervisor 图中，作为流程的最后一步自动执行。

本 Agent 基于 evaluation/judge.py 的逻辑改造。
"""

import json
import re
from langchain_core.prompts import ChatPromptTemplate

from core.agents.supervisor.state import SupervisorState
from core.utils.llm_factory import create_ll
from core.utils.json_parser import parse_json_response
from core.models.llm_outputs import MatchEvaluation


# ============================================================
# Prompt 模板
# ============================================================

_judge_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一位资深的婚恋顾问评审专家。
你的任务是评估一份 AI 婚恋匹配结果的质量。

评估维度（每个维度 1-10 分）：
1. 相关性 (relevance): 候选人是否真的符合用户明确提出的择偶要求（年龄、城市、性别等硬性条件）
2. 契合度 (compatibility): 候选人与用户在性格、兴趣、价值观方面的匹配程度
3. 解释力 (explanation): 匹配理由是否具体、有说服力、不空泛
4. 一致性 (consistency): 评分和理由是否自洽，高分是否有充分理由支撑
5. 温度感 (warmth): 推荐信是否真诚温暖、是否能让用户心动

{json_instruction}"""),
    ("human", """请评估以下 AI 婚恋匹配结果。

## 用户资料
- 昵称: {nickname}，{gender}，{age}岁，{city}
- 择偶要求: {target_gender}，{target_age_min}~{target_age_max}岁，城市: {target_city}
- 关于我: {about_me}
- 兴趣爱好: {hobbies}

## 匹配结果
{results_text}

## 推荐信
{letters_text}
"""),
])

_JUDGE_JSON_SCHEMA = """```json
{
  "overall_score": 整体评分(1-10),
  "relevance": 相关性评分(1-10),
  "compatibility": 契合度评分(1-10),
  "explanation": 解释力评分(1-10),
  "consistency": 一致性评分(1-10),
  "warmth": 温度感评分(1-10),
  "strengths": "匹配结果的优点（1-2句话）",
  "weaknesses": "匹配结果的不足（1-2句话）",
  "suggestions": "改进建议（1-2句话）"
}
```"""


# ============================================================
# Agent 入口函数
# ============================================================

def judge_agent(state: SupervisorState) -> dict:
    """
    质量评估 Agent：用 LLM-as-Judge 评估匹配质量。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - top_matches: 最终推荐的候选人
        - match_letters: 推荐信

    输出（写回 State）：
        - evaluation: 评估结果字典
        - next_agent: "FINISH"（评估完成，流程结束）
    """
    user = state["user_profile"]
    top_matches = state.get("top_matches", [])
    match_letters = state.get("match_letters", [])
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append("⚖️ [Judge Agent] 评估匹配质量...")

    if not top_matches:
        messages.append("   ⚠️ 无匹配结果，跳过评估")
        return {
            "evaluation": {"overall_score": 0, "note": "无匹配结果"},
            "messages": messages,
            "next_agent": "FINISH",
            "agent_history": history + ["judge"],
            "current_agent": "judge",
        }

    # 格式化匹配结果
    results_parts = []
    for i, m in enumerate(top_matches, 1):
        results_parts.append(
            f"候选人{i}: {m.get('nickname', '?')}，"
            f"契合度 {m.get('score', 0)} 分，"
            f"理由: {m.get('reason', '无')}"
        )
    results_text = "\n".join(results_parts)

    # 格式化推荐信
    letters_text = "\n---\n".join(match_letters) if match_letters else "（无推荐信）"

    llm = create_ll(temperature=0.2)  # Judge 用低温度，确保评估稳定

    prompt_messages = _judge_prompt.invoke({
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "target_gender": user.target_gender,
        "target_age_min": user.target_age_min,
        "target_age_max": user.target_age_max,
        "target_city": user.target_city,
        "about_me": user.about_me,
        "hobbies": user.hobbies,
        "results_text": results_text,
        "letters_text": letters_text,
        "json_instruction": f"请严格按照以下 JSON 格式输出，不要添加任何额外文本或解释：\n{_JUDGE_JSON_SCHEMA}",
    })

    response = llm.invoke(prompt_messages)
    raw_text = response.content
    data = parse_json_response(raw_text)
    evaluation = MatchEvaluation.model_validate(data)

    messages.append(f"   评估完成：整体评分 {evaluation.overall_score}/10")
    messages.append(f"   优点: {evaluation.strengths}")

    return {
        "evaluation": evaluation.model_dump(),
        "messages": messages,
        # 评估完成，流程结束
        "next_agent": "FINISH",
        "agent_history": history + ["judge"],
        "current_agent": "judge",
    }
