"""
心犀AI - Agent 节点函数
========================
定义 LangGraph 工作流中的每个处理节点。

学习要点：
---------
- LangGraph 中每个 "Node" 就是一个普通 Python 函数
- 函数接收当前 State，返回需要更新的字段（增量更新）
- 这种设计让每个步骤都可以独立测试和替换

本文件定义了 5 个核心节点：
  1. parse_intent   - 意图解析（LLM 提取硬性条件 + 重写搜索文本）
  2. hybrid_search  - 混合检索（元数据过滤 + 向量相似度）
  3. post_analysis  - 后分析（LLM 深度评分 + 排序）
  4. reflection     - 反思（LLM 分析失败原因 + 调整策略）
  5. generate_match - 生成推荐信（LLM 撰写温暖推荐语）
"""

import json
from langchain_openai import ChatOpenAI

from config.settings import llm_config, match_config
from src.agent.state import AgentState
from src.retrieval.hybrid_retriever import HybridRetriever
from src.utils.prompts import (
    INTENT_PARSE_SYSTEM, INTENT_PARSE_USER,
    POST_ANALYSIS_SYSTEM, POST_ANALYSIS_USER,
    MATCH_LETTER_SYSTEM, MATCH_LETTER_USER,
    REFLECTION_SYSTEM, REFLECTION_USER,
)


def _create_ll(temperature: float = None) -> ChatOpenAI:
    """
    创建 LLM 实例的工厂函数。
    DeepSeek 兼容 OpenAI 的 API 协议，所以用 ChatOpenAI 即可对接。
    """
    return ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=temperature if temperature is not None else llm_config.temperature,
    )


def _safe_json_parse(text: str) -> dict | list:
    """
    安全解析 LLM 返回的 JSON。
    LLM 有时会在 JSON 前后加上 markdown 代码块标记，需要清理。
    """
    # 清理 markdown 代码块标记
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉第一行和最后一行的 ``` 标记
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


# ============================================================
# 节点1：意图解析 (Query Rewriting)
# ============================================================
def parse_intent(state: AgentState) -> dict:
    """
    让 LLM 分析用户的资料和择偶期望，输出：
    1. hard_filters: 硬性过滤条件（性别、年龄、城市）
    2. rewritten_query: 重写后的语义搜索文本

    这是整个流程的第一步——将感性的"我想找一个..."
    转化为机器可理解的过滤条件 + 向量查询文本。
    """
    user = state["user_profile"]
    messages = state.get("messages", [])
    messages.append("🔍 第一步：开始意图解析...")

    llm = _create_ll(temperature=0.3)  # 低温度，让输出更确定、更可控

    # 填充 Prompt 模板
    user_prompt = INTENT_PARSE_USER.format(
        nickname=user.nickname,
        gender=user.gender,
        age=user.age,
        city=user.city,
        about_me=user.about_me,
        ideal_partner=user.ideal_partner,
        hobbies=user.hobbies,
        target_gender=user.target_gender,
        target_age_min=user.target_age_min,
        target_age_max=user.target_age_max,
        target_city=user.target_city,
    )

    # 调用 LLM
    response = llm.invoke([
        {"role": "system", "content": INTENT_PARSE_SYSTEM},
        {"role": "user", "content": user_prompt},
    ])

    # 解析 LLM 的 JSON 输出
    try:
        result = _safe_json_parse(response.content)
    except json.JSONDecodeError:
        # 如果 LLM 返回的不是合法 JSON，使用默认值
        result = {
            "hard_filters": {
                "target_gender": user.target_gender,
                "age_min": user.target_age_min,
                "age_max": user.target_age_max,
                "city": user.target_city,
            },
            "rewritten_query": user.ideal_partner,
        }

    messages.append(f"   硬性条件: {result.get('hard_filters', {})}")
    messages.append(f"   搜索文本: {result.get('rewritten_query', '')[:80]}...")

    return {
        "hard_filters": result.get("hard_filters", {}),
        "rewritten_query": result.get("rewritten_query", user.ideal_partner),
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
    """
    user = state["user_profile"]
    query_text = state["rewritten_query"]
    loop_count = state.get("loop_count", 0)
    retry_strategy = state.get("retry_strategy", "")
    messages = state.get("messages", [])
    messages.append("📋 第二步：执行混合检索...")

    # 决定是否放宽条件
    relaxed = loop_count > 0  # 非首次检索时，启用放宽模式

    # 如果是重试且策略是 rewrite_query，使用新查询文本
    if retry_strategy == "rewrite_query" and state.get("new_query"):
        query_text = state["new_query"]
        messages.append(f"   使用重写后的搜索文本")

    # 执行检索
    candidates = retriever.retrieve(
        user=user,
        query_text=query_text,
        n_results=match_config.max_candidates,
        relaxed=relaxed,
    )

    messages.append(f"   检索到 {len(candidates)} 位候选人 (relaxed={relaxed})")

    return {
        "candidates": candidates,
        "messages": messages,
    }


# ============================================================
# 节点3：LLM 后分析与精排 (Post Analysis)
# ============================================================
def post_analysis(state: AgentState) -> dict:
    """
    将检索到的候选人交给 LLM 进行深度分析：
    - 交叉对比用户和每位候选人的资料
    - 给出 0~100 的契合指数
    - 说明匹配理由
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

    # 将候选人信息格式化为文本，供 LLM 分析
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

    user_prompt = POST_ANALYSIS_USER.format(
        nickname=user.nickname,
        gender=user.gender,
        age=user.age,
        city=user.city,
        about_me=user.about_me,
        ideal_partner=user.ideal_partner,
        hobbies=user.hobbies,
        candidates_text=candidates_text,
    )

    response = llm.invoke([
        {"role": "system", "content": POST_ANALYSIS_SYSTEM},
        {"role": "user", "content": user_prompt},
    ])

    # 解析分析结果
    try:
        analysis_results = _safe_json_parse(response.content)
    except json.JSONDecodeError:
        analysis_results = []

    # 找出最高分
    best_score = 0
    if analysis_results:
        best_score = max(r.get("score", 0) for r in analysis_results)

    # 按分数降序排列
    analysis_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    for r in analysis_results[:3]:
        messages.append(f"   {r.get('nickname', '?')} - {r.get('score', 0)}分: {r.get('reason', '')[:50]}...")

    return {
        "analysis_results": analysis_results,
        "best_score": best_score,
        "messages": messages,
    }


# ============================================================
# 节点4：Agent 反思 (Reflection)
# ============================================================
def reflection(state: AgentState) -> dict:
    """
    当检索结果不理想时，让 LLM 分析原因并调整策略。

    这是 Agentic RAG 的精髓所在——Agent 不是简单地执行一次就结束，
    而是能自主判断结果质量，并决定是否需要换个策略重试。
    """
    user = state["user_profile"]
    loop_count = state.get("loop_count", 0)
    best_score = state.get("best_score", 0)
    candidate_count = len(state.get("candidates", []))
    rewritten_query = state.get("rewritten_query", "")
    messages = state.get("messages", [])
    messages.append(f"🔄 第四步：Agent 反思（当前最高分 {best_score}，阈值 {match_config.match_threshold * 100}）...")

    llm = _create_ll(temperature=0.5)

    user_prompt = REFLECTION_USER.format(
        nickname=user.nickname,
        target_gender=user.target_gender,
        target_age_min=user.target_age_min,
        target_age_max=user.target_age_max,
        target_city=user.target_city,
        loop_count=loop_count,
        max_loops=match_config.max_agent_loops,
        best_score=best_score,
        candidate_count=candidate_count,
        rewritten_query=rewritten_query,
    )

    response = llm.invoke([
        {"role": "system", "content": REFLECTION_SYSTEM},
        {"role": "user", "content": user_prompt},
    ])

    try:
        result = _safe_json_parse(response.content)
    except json.JSONDecodeError:
        result = {"analysis": "JSON解析失败", "strategy": "relax_age", "new_query": None}

    strategy = result.get("strategy", "relax_age")
    messages.append(f"   反思结果: {result.get('analysis', '')}")
    messages.append(f"   调整策略: {strategy}")

    return {
        "loop_count": loop_count + 1,   # 反思完毕，递增循环计数
        "should_retry": True,
        "retry_strategy": strategy,
        "new_query": result.get("new_query"),
        "messages": messages,
    }


# ============================================================
# 节点5：生成匹配推荐信 (Match Letter Generation)
# ============================================================
def generate_match(state: AgentState) -> dict:
    """
    为契合度最高的候选人撰写温暖有爱的「缘分推荐信」。
    这是整个流程的"最后一公里"——把冷冰冰的分数
    转化为打动人心的文字。
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

        user_prompt = MATCH_LETTER_USER.format(
            user_nickname=user.nickname,
            user_about_me=user.about_me,
            user_hobbies=user.hobbies,
            match_nickname=match.get("nickname", "未知"),
            match_age=candidate_detail.get("age", "未知"),
            match_city=candidate_detail.get("city", "未知"),
            match_about_me=candidate_detail.get("about_me", "暂无描述"),
            match_hobbies=candidate_detail.get("hobbies", "未知"),
            match_reason=match.get("reason", ""),
        )

        response = llm.invoke([
            {"role": "system", "content": MATCH_LETTER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ])

        match_letters.append(response.content)
        messages.append(f"   ✉️ 为 {match.get('nickname', '?')} 生成推荐信")

    return {
        "top_matches": top_matches,
        "match_letters": match_letters,
        "messages": messages,
    }
