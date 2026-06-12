"""
心犀AI - 用户访谈 Subgraph 节点函数
=====================================
定义访谈流程中的核心逻辑节点。
"""

import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage

from config.settings import llm_config
from core.agent.interview.state import InterviewState
from core.models.llm_outputs import InterviewExtraction


def _create_ll(temperature: float = 0.7) -> ChatOpenAI:
    """创建 LLM 实例"""
    return ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=temperature,
    )


def _parse_json_response(text: str) -> dict:
    """从回复中提取 JSON"""
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        return json.loads(code_block.group(1).strip())
    
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        return json.loads(text[first_brace:last_brace + 1])
    
    raise ValueError(f"无法解析 JSON: {text[:200]}")


# ============================================================
# 节点 1：生成问题 (Generate Question)
# ============================================================
_question_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是「心犀AI」的资深红娘。
你的任务是与新用户聊天，帮助他们完善个人画像。
目前你手里有一份画像草稿，请分析哪些关键信息（如性格、爱好、理想型）还不够丰满，
然后用一种温暖、自然的方式向用户提问。

要求：
- 每次只问一个问题。
- 不要像查户口一样生硬，要像朋友聊天一样自然切换话题。
- 如果用户已经提供了一些信息，请先给予正面反馈，再切入下一个话题。
- 重点关注字段：about_me (性格生活), ideal_partner (理想型), hobbies (爱好)。
"""),
    ("placeholder", "{messages}"),
])

def generate_question(state: InterviewState) -> dict:
    """
    分析当前画像，生成下一个引导问题。
    如果已完成，则生成结束语。
    """
    llm = _create_ll(temperature=0.8)
    
    if state.get("is_complete"):
        response = llm.invoke([
            AIMessage(content="太棒了！我已经完全了解你的情况了。现在我可以为你进行更精准的匹配。准备好开始寻找缘分了吗？")
        ])
    else:
        # 构造 Prompt，包含之前的聊天记录
        prompt = _question_prompt.format_messages(messages=state["messages"])
        response = llm.invoke(prompt)
    
    # 将 AI 的问题存入 messages
    return {
        "messages": [response]
    }


# ============================================================
# 节点 2：解析回答 (Parse Answer)
# ============================================================
_parse_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是数据提取专家。
请分析用户的回答，提取出对个人画像有帮助的信息。

可更新字段（Pydantic 模型字段）：
- hobbies: 兴趣爱好
- about_me: 关于我的性格、生活方式描述
- ideal_partner: 对理想另一半的描述
- mbti: 如果提到了
- education/annual_income: 如果提到了

你需要输出：
1. updated_fields: 字典格式，包含要更新的字段及内容。
2. is_complete: 布尔值，判断核心字段（about_me, ideal_partner）是否都已经有足够详细的内容（通常指字数足够且有实质内容）。
3. analysis: 简短说明你的判断。

请以 JSON 格式输出。
"""),
    ("human", "问题：{question}\n用户回答：{answer}")
])

_PARSE_JSON_SCHEMA = """```json
{
  "updated_fields": {"字段名": "内容"},
  "is_complete": true/false,
  "analysis": "说明"
}
```"""

def parse_answer(state: InterviewState) -> dict:
    """
    解析用户的最新回答，更新状态。
    """
    if not state["messages"] or not isinstance(state["messages"][-1], HumanMessage):
        return {} # 没有新回答

    last_human_msg = state["messages"][-1].content
    # 找到上一个 AI 的问题
    last_ai_msg = ""
    for m in reversed(state["messages"][:-1]):
        if isinstance(m, AIMessage):
            last_ai_msg = m.content
            break

    llm = _create_ll(temperature=0.2)
    prompt = _parse_prompt.format_messages(
        question=last_ai_msg,
        answer=last_human_msg
    )
    
    # 附加 JSON 要求
    prompt.append(HumanMessage(content=f"请按照以下格式输出：\n{_PARSE_JSON_SCHEMA}"))
    
    response = llm.invoke(prompt)
    data = _parse_json_response(response.content)
    result = InterviewExtraction.model_validate(data)
    
    # 更新 UserProfile 草稿
    draft = state["draft_profile"]
    for field, value in result.updated_fields.items():
        if hasattr(draft, field):
            setattr(draft, field, value)
            
    return {
        "draft_profile": draft,
        "is_complete": result.is_complete
    }
