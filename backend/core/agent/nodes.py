"""
心犀AI - Agent 节点函数（v3: 兼容 DeepSeek thinking mode）
==========================================================
定义 LangGraph 工作流中的每个处理节点。

学习要点：
---------
v2 → v3 的变更：
  DeepSeek V4 Flash 的 thinking mode 不支持 with_structured_output()
  （function calling / json_schema 均不可用）。
  因此改为：在 Prompt 中要求 LLM 返回 JSON，然后手动解析并用 Pydantic 校验。

  核心模式：
    1. ChatPromptTemplate 管理 Prompt（保留 v2 的优势）
    2. Prompt 末尾追加 JSON 格式要求
    3. _parse_json_response() 从 LLM 回复中提取 JSON（兼容 thinking 输出）
    4. Pydantic model_validate 做类型校验

本文件定义了 5 个核心节点：
  1. parse_intent   - 意图解析（LLM 提取硬性条件 + 重写搜索文本）
  2. hybrid_search  - 混合检索（元数据过滤 + 向量相似度）
  3. post_analysis  - 后分析（LLM 深度评分 + 排序）
  4. reflection     - 反思（LLM 分析失败原因 + 调整策略）
  5. generate_match - 生成推荐信（LLM 撰写温暖推荐语）
"""

import json
import re
from functools import partial

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config.settings import llm_config, match_config
from core.agent.state import AgentState
from core.retrieval.hybrid_retriever import HybridRetriever
from core.models.llm_outputs import (
    IntentParseResult,
    AnalysisResultList,
    ReflectionResult,
)
# 【重构】从共享工具模块导入，消除三处重复的工厂函数和解析器
from core.utils.llm_factory import create_ll as _create_ll
from core.utils.json_parser import parse_json_response as _parse_json_response, JSON_SUFFIX as _JSON_SUFFIX


def _invoke_structured(llm: ChatOpenAI, prompt_messages, model_class):
    """
    调用 LLM 并将回复解析为 Pydantic 模型。

    这是替代 with_structured_output() 的兼容方案：
    1. 在 prompt 末尾追加 JSON 格式说明
    2. 调用 LLM 获取自由文本回复
    3. 从回复中提取 JSON（使用共享的 _parse_json_response）
    4. 用 Pydantic model_validate 校验并构造模型实例

    学习要点：
    - 这种方式虽然没有 function calling 那么"结构化"，但更灵活
    - 适用于不支持 tool calling 的模型（如 DeepSeek thinking 系列）
    - Pydantic 仍然提供类型校验，确保数据结构正确
    """
    response = llm.invoke(prompt_messages)
    raw_text = response.content
    data = _parse_json_response(raw_text)
    return model_class.model_validate(data)


# ============================================================
# 节点1：意图解析 (Query Rewriting)
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


def parse_intent(state: AgentState) -> dict:
    """
    让 LLM 分析用户的资料和择偶期望，输出：
    1. hard_filters: 硬性过滤条件（性别、年龄、城市）
    2. rewritten_query: 重写后的语义搜索文本

    【v3 方式】在 Prompt 中要求 JSON 输出 + 手动解析 + Pydantic 校验
    （兼容 DeepSeek thinking mode，不使用 with_structured_output）
    """
    user = state["user_profile"]
    messages = state.get("messages", [])
    messages.append("🔍 第一步：开始意图解析...")

    llm = _create_ll(temperature=0.3)

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
        "json_instruction": _JSON_SUFFIX.format(json_schema=_INTENT_JSON_SCHEMA),
    })

    result: IntentParseResult = _invoke_structured(llm, prompt_messages, IntentParseResult)

    hard_filters = result.hard_filters.model_dump()
    messages.append(f"   硬性条件: {hard_filters}")
    messages.append(f"   搜索文本: {result.rewritten_query[:80]}...")

    return {
        "hard_filters": hard_filters,
        "rewritten_query": result.rewritten_query,
        "messages": messages,
    }


# ============================================================
# 节点2：混合检索 (Hybrid Search)
# ============================================================
def hybrid_search(state: AgentState, retriever: HybridRetriever) -> dict:
    """
    执行混合检索：硬性过滤 + 向量相似度搜索。

    注意：这个节点需要外部注入 retriever 实例，
    我们会用 functools.partial 在 graph.py 中绑定它。

    学习要点：
    - hard_filters 来自 parse_intent 节点的 LLM 分析结果
    - 将 hard_filters 传给 retriever，让 LLM 的智能分析真正影响检索过滤
    - 这比直接从 UserProfile 读原始字段更"智能"，因为 LLM 可能做了推理调整
    """
    user = state["user_profile"]
    query_text = state["rewritten_query"]
    loop_count = state.get("loop_count", 0)
    retry_strategy = state.get("retry_strategy", "")
    messages = state.get("messages", [])
    messages.append("📋 第二步：执行混合检索...")

    # 从状态中获取 LLM 提取的硬性过滤条件
    # 如果 parse_intent 节点已执行，这里会有 LLM 分析的 hard_filters
    hard_filters = state.get("hard_filters")
    if hard_filters:
        messages.append(f"   使用 LLM 提取的硬性条件: {hard_filters}")

    # 决定是否放宽条件
    relaxed = loop_count > 0  # 非首次检索时，启用放宽模式

    # 如果是重试且策略是 rewrite_query，使用新查询文本
    if retry_strategy == "rewrite_query" and state.get("new_query"):
        query_text = state["new_query"]
        messages.append("   使用重写后的搜索文本")

    # 执行检索（传入 hard_filters 让 LLM 的智能分析生效）
    candidates = retriever.retrieve(
        user=user,
        query_text=query_text,
        n_results=match_config.max_candidates,
        relaxed=relaxed,
        hard_filters=hard_filters,
    )

    messages.append(f"   检索到 {len(candidates)} 位候选人 (relaxed={relaxed})")

    return {
        "candidates": candidates,
        "messages": messages,
    }


# ============================================================
# 节点3：LLM 后分析与精排 (Post Analysis)
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


def post_analysis(state: AgentState) -> dict:
    """
    将检索到的候选人交给 LLM 进行深度分析：
    - 交叉对比用户和每位候选人的资料
    - 给出 0~100 的契合指数
    - 说明匹配理由

    【v3 方式】Prompt 要求 JSON + 手动解析 + Pydantic 校验
    """
    user = state["user_profile"]
    candidates = state.get("candidates", [])
    messages = state.get("messages", [])
    messages.append("🧠 第三步：LLM 深度分析与评分...")

    if not candidates:
        messages.append("   ⚠️ 无候选人，跳过分析")
        return {
            "analysis_results": [],
            "best_score": 0,
            "messages": messages,
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

    llm = _create_ll(temperature=0.3)

    prompt_messages = _analysis_prompt.invoke({
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "about_me": user.about_me,
        "ideal_partner": user.ideal_partner,
        "hobbies": user.hobbies,
        "candidates_text": candidates_text,
        "json_instruction": _JSON_SUFFIX.format(json_schema=_ANALYSIS_JSON_SCHEMA),
    })

    result: AnalysisResultList = _invoke_structured(llm, prompt_messages, AnalysisResultList)

    analysis_results = [c.model_dump() for c in result.candidates]

    # 找出最高分
    best_score = max((r["score"] for r in analysis_results), default=0)

    # 按分数降序排列
    analysis_results.sort(key=lambda x: x["score"], reverse=True)

    for r in analysis_results[:3]:
        messages.append(f"   {r['nickname']} - {r['score']}分: {r['reason'][:50]}...")

    return {
        "analysis_results": analysis_results,
        "best_score": best_score,
        "messages": messages,
    }


# ============================================================
# 节点4：Agent 反思 (Reflection)
# ============================================================

_reflection_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是「心犀AI」的策略优化分析师。
当前的婚恋匹配检索结果不理想（契合度低于阈值），你需要分析原因并提出改进策略。

可选的调整策略：
1. relax_age - 放宽年龄范围（各扩展 3 岁）
2. relax_city - 放宽地域限制（从同城扩展到同省）
3. rewrite_query - 重写语义搜索文本（扩大兴趣范围）

请分析当前情况，选择最合理的策略。

{json_instruction}"""),
    ("human", """## 当前用户
- 昵称: {nickname}
- 择偶要求: {target_gender}，{target_age_min}~{target_age_max}岁，城市: {target_city}

## 当前检索结果
- 已尝试次数: {loop_count}/{max_loops}
- 最高契合分: {best_score}
- 候选人数量: {candidate_count}

## 当前搜索文本
{rewritten_query}
"""),
])

_REFLECTION_JSON_SCHEMA = """```json
{
  "analysis": "简要分析当前匹配不佳的原因",
  "strategy": "relax_age 或 relax_city 或 rewrite_query",
  "new_query": "如果strategy为rewrite_query则提供新搜索文本，否则为null"
}
```"""


def reflection(state: AgentState) -> dict:
    """
    当检索结果不理想时，让 LLM 分析原因并调整策略。

    这是 Agentic RAG 的精髓所在——Agent 不是简单地执行一次就结束，
    而是能自主判断结果质量，并决定是否需要换个策略重试。

    【v3 方式】Prompt 要求 JSON + 手动解析 + Pydantic 校验
    """
    user = state["user_profile"]
    loop_count = state.get("loop_count", 0)
    best_score = state.get("best_score", 0)
    candidate_count = len(state.get("candidates", []))
    rewritten_query = state.get("rewritten_query", "")
    messages = state.get("messages", [])
    messages.append(f"🔄 第四步：Agent 反思（当前最高分 {best_score}，阈值 {match_config.match_threshold * 100}）...")

    llm = _create_ll(temperature=0.5)

    prompt_messages = _reflection_prompt.invoke({
        "nickname": user.nickname,
        "target_gender": user.target_gender,
        "target_age_min": user.target_age_min,
        "target_age_max": user.target_age_max,
        "target_city": user.target_city,
        "loop_count": loop_count,
        "max_loops": match_config.max_agent_loops,
        "best_score": best_score,
        "candidate_count": candidate_count,
        "rewritten_query": rewritten_query,
        "json_instruction": _JSON_SUFFIX.format(json_schema=_REFLECTION_JSON_SCHEMA),
    })

    result: ReflectionResult = _invoke_structured(llm, prompt_messages, ReflectionResult)

    messages.append(f"   反思结果: {result.analysis}")
    messages.append(f"   调整策略: {result.strategy}")

    return {
        "loop_count": loop_count + 1,
        "should_retry": True,
        "retry_strategy": result.strategy,
        "new_query": result.new_query,
        "messages": messages,
    }


# ============================================================
# 节点5：生成匹配推荐信 (Match Letter Generation)
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


def generate_match(state: AgentState) -> dict:
    """
    为契合度最高的候选人撰写温暖有爱的「缘分推荐信」。
    这是整个流程的"最后一公里"——把冷冰冰的分数
    转化为打动人心的文字。

    注意：推荐信是自由文本，不需要结构化输出。
    这里用 ChatPromptTemplate 来管理 Prompt 即可。
    """
    user = state["user_profile"]
    analysis_results = state.get("analysis_results", [])
    messages = state.get("messages", [])
    messages.append("💌 第五步：生成缘分推荐信...")

    # 取前 N 名高分候选人
    top_matches = analysis_results[:match_config.max_top_matches]
    match_letters = []
    llm = _create_ll(temperature=0.8)  # 高温度，让文字更有创意和温度

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
    }


# ============================================================
# 节点6：人工反馈 (Human-in-the-loop) —— Phase 6
# ============================================================

def human_feedback(state: AgentState) -> dict:
    """
    Human-in-the-loop 节点：暂停匹配流程，等待用户反馈。

    学习要点：
    ---------
    LangGraph 的 interrupt() 函数可以暂停图的执行，
    将数据"推"给用户，然后等待用户的"拉"（反馈）。

    工作流程：
    1. interrupt() 暂停执行，返回当前分析结果给用户
    2. 用户审查候选人，提供反馈（approve / reject / adjust）
    3. Command(resume=feedback) 恢复执行
    4. 本函数收到 feedback，根据反馈更新状态

    反馈类型：
    - approve: 用户满意，直接生成推荐信
    - reject: 用户不满意，触发反思重试
    - adjust: 用户提供具体调整意见（如"年龄再大一点"）
    """
    from langgraph.types import interrupt

    analysis_results = state.get("analysis_results", [])
    messages = state.get("messages", [])
    messages.append("👤 第六步：等待用户反馈...")

    # 构造展示给用户的候选人摘要
    candidate_summary = []
    for r in analysis_results[:5]:
        candidate_summary.append({
            "user_id": r.get("user_id", ""),
            "nickname": r.get("nickname", ""),
            "score": r.get("score", 0),
            "reason": r.get("reason", ""),
        })

    # interrupt() 暂停图的执行，将数据发送给用户
    # 用户通过 Command(resume=feedback_data) 恢复执行
    # feedback_data 就是 interrupt() 的返回值
    feedback = interrupt({
        "type": "request_feedback",
        "message": "请审核以下候选人，告诉我你的想法：",
        "candidates": candidate_summary,
        "options": ["approve", "reject", "adjust"],
    })

    # 处理用户的反馈
    feedback_type = feedback.get("type", "approve") if isinstance(feedback, dict) else "approve"
    feedback_detail = feedback.get("detail", "") if isinstance(feedback, dict) else str(feedback)

    messages.append(f"   用户反馈: {feedback_type}" + (f" - {feedback_detail}" if feedback_detail else ""))

    if feedback_type == "approve":
        # 用户满意，直接进入 generate_match
        messages.append("   ✅ 用户满意，开始生成推荐信")
        return {
            "should_retry": False,
            "messages": messages,
        }
    elif feedback_type == "reject":
        # 用户不满意，触发反思重试
        messages.append("   🔄 用户不满意，触发策略调整")
        return {
            "should_retry": True,
            "best_score": 0,  # 强制进入反思
            "retry_strategy": "rewrite_query",
            "messages": messages,
        }
    elif feedback_type == "adjust":
        # 用户提供具体调整意见
        messages.append(f"   📝 根据用户反馈调整: {feedback_detail}")
        return {
            "should_retry": True,
            "best_score": 0,
            "retry_strategy": "rewrite_query",
            "new_query": feedback_detail,
            "messages": messages,
        }
    else:
        # 未知反馈类型，默认继续
        return {
            "should_retry": False,
            "messages": messages,
        }
