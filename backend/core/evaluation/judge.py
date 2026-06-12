"""
心犀AI - LLM-as-Judge 匹配质量评估（Phase 7）
================================================
使用一个独立的 LLM（Judge）来评估匹配推荐的质量。

学习要点：
---------
LLM-as-Judge 是一种越来越流行的评估方法：
  - 用一个 LLM 来"打分"另一个 LLM 的输出
  - 类似于人类评审，但自动化、可规模化
  - 特别适合评估"开放式"输出（如推荐信、匹配理由）的质量

评估维度：
  1. 相关性 (Relevance): 候选人是否真的符合用户的择偶要求
  2. 多样性 (Diversity): 推荐结果是否有合理的差异性
  3. 解释力 (Explanation): 匹配理由是否有说服力、是否具体
  4. 一致性 (Consistency): 评分和理由是否自洽
  5. 温度感 (Warmth): 推荐信是否有温度、是否打动人心

注意事项：
  - Judge 模型和匹配模型最好不同（避免"自己给自己打分"的偏差）
  - 本学习项目使用同一个 DeepSeek 模型（简化处理）
  - 生产环境建议用不同模型做 Judge
"""

import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config.settings import llm_config
from core.models.llm_outputs import MatchEvaluation


# ============================================================
# Judge 模型（可以配置不同的 LLM，这里复用同一个 DeepSeek）
# ============================================================

def _create_judge_llm(temperature: float = 0.2) -> ChatOpenAI:
    """
    创建 Judge LLM 实例。
    使用较低温度（0.2）确保评估的稳定性和一致性。
    """
    return ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=temperature,
    )


def _parse_json_response(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    text = text.strip()
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        return json.loads(code_block.group(1).strip())

    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        return json.loads(text[first_brace:last_brace + 1])

    raise ValueError(f"无法从 LLM 回复中提取 JSON:\n{text[:500]}")


# ============================================================
# 评估 Prompt
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

请严格按照 JSON 格式输出评估结果。
"""),
    ("human", """## 用户资料
- 昵称: {user_nickname}，{user_gender}，{user_age}岁，{user_city}
- 关于我: {user_about_me}
- 理想的Ta: {user_ideal_partner}
- 兴趣爱好: {user_hobbies}
- 择偶要求: {target_gender}，{target_age_min}-{target_age_max}岁，城市: {target_city}

## 匹配结果
{match_results_text}

## 推荐信
{match_letters_text}

请输出 JSON 格式的评估结果：
```json
{{
  "overall_score": 1到10的整体评分,
  "dimensions": [
    {{"dimension": "relevance", "score": 分数, "comment": "评价"}},
    {{"dimension": "compatibility", "score": 分数, "comment": "评价"}},
    {{"dimension": "explanation", "score": 分数, "comment": "评价"}},
    {{"dimension": "consistency", "score": 分数, "comment": "评价"}},
    {{"dimension": "warmth", "score": 分数, "comment": "评价"}}
  ],
  "strengths": "主要优点",
  "weaknesses": "主要不足",
  "suggestion": "改进建议"
}}
```
"""),
])


def evaluate_match(
    user_profile,
    match_results: list[dict],
    match_letters: list[str],
) -> MatchEvaluation:
    """
    使用 LLM-as-Judge 评估匹配结果的质量。

    参数:
        user_profile: 用户的 UserProfile
        match_results: 匹配结果列表（来自 analysis_results 或 top_matches）
        match_letters: 推荐信列表

    返回:
        MatchEvaluation 评估结果
    """
    llm = _create_judge_llm()

    # 格式化匹配结果
    results_parts = []
    for i, m in enumerate(match_results, 1):
        results_parts.append(
            f"候选人{i}: {m.get('nickname', '?')}，{m.get('score', 0)}分\n"
            f"  理由: {m.get('reason', '无')}"
        )
    match_results_text = "\n\n".join(results_parts) if results_parts else "无匹配结果"

    # 格式化推荐信
    letters_parts = []
    for i, letter in enumerate(match_letters, 1):
        letters_parts.append(f"推荐信{i}:\n{letter}")
    match_letters_text = "\n\n".join(letters_parts) if letters_parts else "无推荐信"

    prompt_messages = _judge_prompt.invoke({
        "user_nickname": user_profile.nickname,
        "user_gender": user_profile.gender,
        "user_age": user_profile.age,
        "user_city": user_profile.city,
        "user_about_me": user_profile.about_me,
        "user_ideal_partner": user_profile.ideal_partner,
        "user_hobbies": user_profile.hobbies,
        "target_gender": user_profile.target_gender,
        "target_age_min": user_profile.target_age_min,
        "target_age_max": user_profile.target_age_max,
        "target_city": user_profile.target_city,
        "match_results_text": match_results_text,
        "match_letters_text": match_letters_text,
    })

    response = llm.invoke(prompt_messages)
    data = _parse_json_response(response.content)
    return MatchEvaluation.model_validate(data)
