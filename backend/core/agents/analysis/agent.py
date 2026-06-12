"""
心犀AI - 深度分析 Agent
=========================
用 LLM 对候选人进行交叉分析，评估与用户的契合度。

学习要点：
---------
这个 Agent 是整个流程中"最有技术含量"的 LLM 调用之一：
  - 它需要理解用户和候选人双方的资料
  - 输出结构化的评分（0-100）和匹配理由
  - 评分结果直接决定了后续的推荐和反思策略

本 Agent 对应原版 nodes.py 中的 post_analysis 节点。
"""

from langchain_core.prompts import ChatPromptTemplate

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.models.llm_outputs import AnalysisResultList
from core.utils.llm_factory import create_ll
from core.utils.json_parser import invoke_structured


# ============================================================
# Prompt 模板
# ============================================================

_analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是「心犀AI」的资深婚恋顾问。
你将收到一位用户的资料和若干候选人的资料，你的任务是：

1. 对每位候选人进行深度交叉分析，评估与用户的契合度
2. 给出 0~100 的契合指数评分
3. 简要说明匹配理由（聚焦于三观、性格、兴趣的契合点）

重要规则：
- 只能基于提供的资料进行分析，禁止编造用户未提及的信息
- 评分要综合考量：性格互补/契合度、兴趣重叠度、生活节奏匹配度、价值观一致性
- 如果候选人资料与用户资料存在明显矛盾，应扣分

{json_instruction}"""),
    ("human", """## 当前用户
- 昵称: {nickname}，{gender}，{age}岁，{city}
- 关于我: {about_me}
- 理想的Ta: {ideal_partner}
- 兴趣爱好: {hobbies}

## 候选人列表
{candidates_text}
"""),
])

_ANALYSIS_JSON_SCHEMA = """```json
{
  "candidates": [
    {
      "user_id": "候选人ID",
      "nickname": "候选人昵称",
      "score": 0到100的整数,
      "reason": "匹配理由（2-3句话）"
    }
  ]
}
```"""


# ============================================================
# Agent 入口函数
# ============================================================

def analysis_agent(state: SupervisorState) -> dict:
    """
    深度分析 Agent：LLM 交叉分析候选人契合度。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - candidates: 候选人列表（来自 Retrieval Agent）

    输出（写回 State）：
        - analysis_results: 每位候选人的评分和分析
        - best_score: 最高契合分数
        - next_agent: 根据 best_score 决定去 "letter" 还是 "reflection"
          （注意：在 Supervisor 模式中，这个决策由 Supervisor 做出，
           Agent 自己不做路由判断，这里设为 "supervisor" 回到调度中心）
    """
    user = state["user_profile"]
    candidates = state.get("candidates", [])
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append("🧠 [Analysis Agent] LLM 深度分析与评分...")

    if not candidates:
        messages.append("   ⚠️ 无候选人，跳过分析")
        return {
            "analysis_results": [],
            "best_score": 0,
            "messages": messages,
            "next_agent": "supervisor",  # 回到 Supervisor 决定下一步
            "agent_history": history + ["analysis"],
            "current_agent": "analysis",
        }

    # 将候选人信息格式化为文本
    candidates_text_parts = []
    for i, c in enumerate(candidates, 1):
        meta = c.get("metadata", {})
        part = f"""候选人{i}:
- ID: {c.get('user_id', '未知')}
- 昵称: {meta.get('nickname', '未知')}，{meta.get('gender', '')}，{meta.get('age', '')}岁，{meta.get('city', '')}
- 关于Ta: {meta.get('about_me', '无描述')}
- 理想的Ta: {meta.get('ideal_partner', '无描述')}
- 兴趣爱好: {meta.get('hobbies', '无')}
- 向量相似度距离: {c.get('distance', 'N/A')}"""
        candidates_text_parts.append(part)
    candidates_text = "\n\n".join(candidates_text_parts)

    llm = create_ll(temperature=0.3)

    prompt_messages = _analysis_prompt.invoke({
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "about_me": user.about_me,
        "ideal_partner": user.ideal_partner,
        "hobbies": user.hobbies,
        "candidates_text": candidates_text,
        "json_instruction": f"请严格按照以下 JSON 格式输出，不要添加任何额外文本或解释：\n{_ANALYSIS_JSON_SCHEMA}",
    })

    result: AnalysisResultList = invoke_structured(llm, prompt_messages, AnalysisResultList)

    analysis_results = [c.model_dump() for c in result.candidates]
    best_score = max((r["score"] for r in analysis_results), default=0)
    analysis_results.sort(key=lambda x: x["score"], reverse=True)

    for r in analysis_results[:3]:
        messages.append(f"   {r['nickname']} - {r['score']}分: {r['reason'][:50]}...")

    return {
        "analysis_results": analysis_results,
        "best_score": best_score,
        "messages": messages,
        # 回到 Supervisor，让它根据 best_score 决定下一步
        "next_agent": "supervisor",
        "agent_history": history + ["analysis"],
        "current_agent": "analysis",
    }
