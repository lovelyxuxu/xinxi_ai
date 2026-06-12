"""
心犀AI - 策略反思 Agent
=========================
当匹配结果不理想时，分析原因并调整搜索策略。

学习要点：
---------
反思（Reflection）是 Agentic RAG 的精髓所在：
  - 传统 RAG：检索一次就结束，结果不好也没办法
  - Agentic RAG：Agent 能自主判断结果质量，决定是否需要换个策略重试

  这种"自我纠错"能力是 Agent 区别于简单 pipeline 的关键特征！

可选策略：
  1. relax_age   — 放宽年龄范围（各扩展 3 岁）
  2. relax_city  — 放宽地域限制（从同城扩展到同省）
  3. rewrite_query — 重写语义搜索文本（扩大兴趣范围）

本 Agent 对应原版 nodes.py 中的 reflection 节点。
"""

from langchain_core.prompts import ChatPromptTemplate

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.models.llm_outputs import ReflectionResult
from core.utils.llm_factory import create_ll
from core.utils.json_parser import invoke_structured


# ============================================================
# Prompt 模板
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


# ============================================================
# Agent 入口函数
# ============================================================

def reflection_agent(state: SupervisorState) -> dict:
    """
    策略反思 Agent：分析匹配失败原因，调整搜索策略。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - loop_count: 已尝试次数
        - best_score: 当前最高分
        - candidates: 候选人列表
        - rewritten_query: 当前搜索文本

    输出（写回 State）：
        - loop_count: +1
        - should_retry: True
        - retry_strategy: 调整策略名称
        - new_query: 如果是 rewrite_query，提供新文本
        - next_agent: "retrieval"（反思完后重新检索）
    """
    user = state["user_profile"]
    loop_count = state.get("loop_count", 0)
    best_score = state.get("best_score", 0)
    candidate_count = len(state.get("candidates", []))
    rewritten_query = state.get("rewritten_query", "")
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append(f"🔄 [Reflection Agent] 策略反思（最高分 {best_score}，阈值 {match_config.match_threshold * 100}）...")

    llm = create_ll(temperature=0.5)

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
        "json_instruction": f"请严格按照以下 JSON 格式输出，不要添加任何额外文本或解释：\n{_REFLECTION_JSON_SCHEMA}",
    })

    result: ReflectionResult = invoke_structured(llm, prompt_messages, ReflectionResult)

    messages.append(f"   反思结果: {result.analysis}")
    messages.append(f"   调整策略: {result.strategy}")

    return {
        "loop_count": loop_count + 1,
        "should_retry": True,
        "retry_strategy": result.strategy,
        "new_query": result.new_query,
        "messages": messages,
        # 反思完后重新检索
        "next_agent": "retrieval",
        "agent_history": history + ["reflection"],
        "current_agent": "reflection",
    }
