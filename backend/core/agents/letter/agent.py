"""
心犀AI - 推荐信生成 Agent
============================
为高分候选人撰写温暖、真诚的「缘分推荐信」。

学习要点：
---------
推荐信生成是整个流程的"最后一公里"——把冷冰冰的分数转化为打动人心的文字。
这个 Agent 使用高温度（0.8）来让 LLM 输出更有创意和温度的文字。

注意：推荐信是自由文本输出，不需要 JSON 结构化解析。
这里用 ChatPromptTemplate 管理 Prompt 即可，不需要 invoke_structured()。

本 Agent 对应原版 nodes.py 中的 generate_match 节点。
"""

from langchain_core.prompts import ChatPromptTemplate

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.utils.llm_factory import create_ll


# ============================================================
# Prompt 模板
# ============================================================

_letter_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是「心犀AI」的专属红娘文案师。
你的任务是为匹配成功的用户撰写一封温暖、真诚、有温度的「缘分推荐信」。

重要规则：
- 基于实际提供的双方资料撰写，禁止编造
- 突出双方最动人的契合点
- 语气温暖亲切，像一位真心关心朋友的红娘
- 控制在 150~250 字之间
- 可以适当加入生活化的场景想象（如"想象你们周末一起..."）
"""),
    ("human", """请为以下两位用户撰写一封缘分推荐信。

## 用户资料
- 昵称: {user_nickname}
- 关于我: {user_about_me}
- 兴趣爱好: {user_hobbies}

## 推荐对象
- 昵称: {match_nickname}
- 年龄: {match_age}岁，{match_city}
- 关于Ta: {match_about_me}
- 兴趣爱好: {match_hobbies}

## 匹配理由
{match_reason}

请撰写推荐信，让用户感受到这份缘分的独特和美好。
"""),
])


# ============================================================
# Agent 入口函数
# ============================================================

def letter_agent(state: SupervisorState) -> dict:
    """
    推荐信生成 Agent：为高分候选人撰写温暖的推荐信。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - analysis_results: 候选人的评分和分析
        - candidates: 候选人的详细 metadata

    输出（写回 State）：
        - top_matches: 最终推荐的候选人列表
        - match_letters: 推荐信列表
        - next_agent: "judge"（生成完后交给 Judge 评估质量）
    """
    user = state["user_profile"]
    analysis_results = state.get("analysis_results", [])
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append("💌 [Letter Agent] 生成缘分推荐信...")

    # 取前 N 名高分候选人
    top_matches = analysis_results[:match_config.max_top_matches]
    match_letters = []
    llm = create_ll(temperature=0.8)  # 高温度，让文字更有创意和温度

    for match in top_matches:
        # 从候选人列表中找到该用户的详细 metadata
        candidate_detail = {}
        for c in state.get("candidates", []):
            if c.get("user_id") == match.get("user_id"):
                candidate_detail = c.get("metadata", {})
                break

        prompt_messages = _letter_prompt.invoke({
            "user_nickname": user.nickname,
            "user_about_me": user.about_me,
            "user_hobbies": user.hobbies,
            "match_nickname": match.get("nickname", "未知"),
            "match_age": candidate_detail.get("age", "未知"),
            "match_city": candidate_detail.get("city", "未知"),
            "match_about_me": candidate_detail.get("about_me", "暂无描述"),
            "match_hobbies": candidate_detail.get("hobbies", "未知"),
            "match_reason": match.get("reason", ""),
        })

        response = llm.invoke(prompt_messages)
        match_letters.append(response.content)
        messages.append(f"   ✉️ 为 {match.get('nickname', '?')} 生成推荐信")

    return {
        "top_matches": top_matches,
        "match_letters": match_letters,
        "messages": messages,
        # 推荐信生成完毕后，交给 Judge 评估整体质量
        "next_agent": "judge",
        "agent_history": history + ["letter"],
        "current_agent": "letter",
    }
