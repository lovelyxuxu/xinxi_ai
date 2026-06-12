"""
心犀AI - 意图解析 Agent
=========================
分析用户资料和择偶期望，提取硬性过滤条件和语义搜索文本。

学习要点：
---------
在 Supervisor 模式中，每个 Agent 都是一个独立的"专家"：
  - 只关心自己的输入（从共享 State 中读取）
  - 只更新自己负责的字段（写回共享 State）
  - 不关心调度逻辑（由 Supervisor 负责）

本 Agent 对应原版 nodes.py 中的 parse_intent 节点。
改造点：
  - 接收 SupervisorState 而非 AgentState
  - 在返回值中设置 next_agent（告知 Supervisor "我做完了"）
  - 在 agent_history 中记录自己的执行
"""

from langchain_core.prompts import ChatPromptTemplate

from core.agents.supervisor.state import SupervisorState
from core.models.llm_outputs import IntentParseResult
from core.utils.llm_factory import create_ll
from core.utils.json_parser import invoke_structured


# ============================================================
# Prompt 模板
# ============================================================

_intent_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是「心犀AI」婚恋匹配系统的智能分析师。
你的任务是分析用户的个人资料和择偶期望，将其拆解为两部分：

1. **硬性过滤条件**：提取可以用结构化字段精确筛选的条件（性别、年龄范围、城市）。
2. **语义搜索文本**：将用户的感性描述重写为适合向量检索的客观特征描述。

重要规则：
- 硬性条件必须严格基于用户的择偶要求字段
- 语义文本应包含性格特征、兴趣爱好、生活方式等软性维度
- 将模糊描述转化为具体的特征词簇，例如"宅"→"喜欢室内活动、阅读、看电影"

{json_instruction}"""),
    ("human", """请分析以下用户的资料，生成意图解析结果。

## 当前用户资料
- 昵称: {nickname}
- 性别: {gender}
- 年龄: {age}
- 城市: {city}
- 关于我: {about_me}
- 理想的Ta: {ideal_partner}
- 兴趣爱好: {hobbies}

## 择偶硬性要求
- 期望对方性别: {target_gender}
- 期望对方年龄范围: {target_age_min} ~ {target_age_max}
- 期望对方城市: {target_city}
"""),
])

_INTENT_JSON_SCHEMA = """```json
{
  "hard_filters": {
    "target_gender": "male 或 female",
    "age_min": 数字,
    "age_max": 数字,
    "city": "城市名 或 不限"
  },
  "rewritten_query": "重写后的语义搜索文本"
}
```"""


# ============================================================
# Agent 入口函数
# ============================================================

def intent_agent(state: SupervisorState) -> dict:
    """
    意图解析 Agent：让 LLM 分析用户资料，输出硬性条件和语义搜索文本。

    输入（从 State 读取）：
        - user_profile: 当前用户的完整画像

    输出（写回 State）：
        - hard_filters: 硬性过滤条件字典
        - rewritten_query: 重写后的语义搜索文本
        - next_agent: "retrieval"（告诉 Supervisor 下一步该检索了）
        - agent_history: 追加 "intent"

    学习要点：
    - 使用共享的 create_ll() 创建 LLM 实例，而非本地工厂函数
    - 使用共享的 invoke_structured() 完成 JSON 解析 + Pydantic 校验
    """
    user = state["user_profile"]
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append("🔍 [Intent Agent] 开始意图解析...")

    llm = create_ll(temperature=0.3)

    prompt_messages = _intent_prompt.invoke({
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "about_me": user.about_me,
        "ideal_partner": user.ideal_partner,
        "hobbies": user.hobbies,
        "target_gender": user.target_gender,
        "target_age_min": user.target_age_min,
        "target_age_max": user.target_age_max,
        "target_city": user.target_city,
        "json_instruction": f"请严格按照以下 JSON 格式输出，不要添加任何额外文本或解释：\n{_INTENT_JSON_SCHEMA}",
    })

    result: IntentParseResult = invoke_structured(llm, prompt_messages, IntentParseResult)

    hard_filters = result.hard_filters.model_dump()
    messages.append(f"   硬性条件: {hard_filters}")
    messages.append(f"   搜索文本: {result.rewritten_query[:80]}...")

    return {
        "hard_filters": hard_filters,
        "rewritten_query": result.rewritten_query,
        "messages": messages,
        # Supervisor 调度字段
        "next_agent": "retrieval",   # 意图解析完成后，下一步是检索
        "agent_history": history + ["intent"],
        "current_agent": "intent",
    }
