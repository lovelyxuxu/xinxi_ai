"""
心犀AI - Supervisor 路由器
==============================
Supervisor 的"大脑"——根据当前状态决定下一步执行哪个 Agent。

学习要点：
---------
路由器（Router）是 Supervisor 模式的核心组件，它有两种实现方式：

1. 规则版（Rule-based）：用 if/elif 硬编码路由逻辑
   - 优点：确定性强、易调试、速度快
   - 缺点：不够灵活，新增 Agent 时需要手动修改路由代码

2. LLM 版（LLM-based）：用 LLM 理解各 Agent 的能力，动态决策
   - 优点：灵活、可扩展（只需描述新 Agent 的能力即可）
   - 缺点：多一次 LLM 调用，有延迟和不确定性

本项目两种都实现，让你对比学习！

路由决策流程：
  1. 每个 Agent 执行完毕后，把 next_agent 设为 "supervisor"
  2. Supervisor 节点被调用，根据状态决定下一个 Agent
  3. 如果 Supervisor 返回 "FINISH"，整个流程结束
"""

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.utils.llm_factory import create_ll
from core.utils.json_parser import parse_json_response


# ============================================================
# 路由方式 A：规则版 Supervisor（推荐先用这个，稳定可靠）
# ============================================================

def rule_based_router(state: SupervisorState) -> str:
    """
    基于规则的 Supervisor 路由器。

    用 if/elif 硬编码路由逻辑，精确复现原版图的拓扑结构。

    决策逻辑：
      1. 如果某个 Agent 刚执行完且明确指定了 next_agent，直接使用
      2. 如果没有指定（或值为 "supervisor"），根据当前状态推断：
         - analysis 后：根据 best_score 决定去 letter 还是 reflection
         - reflection 后：根据 loop_count 决定重试还是放弃
         - 其他情况：按默认流程走

    返回:
        下一个 Agent 的名称（如 "retrieval"），或 "FINISH" 结束
    """
    # 先看看上一个 Agent 有没有直接指定下一步
    # （有些 Agent 如 intent/retrieval/reflection/letter 会直接指定）
    last_suggestion = state.get("next_agent", "")

    # 如果上一个 Agent 明确指定了下一个（不是 "supervisor"），直接采纳
    if last_suggestion and last_suggestion != "supervisor" and last_suggestion != "FINISH":
        return last_suggestion

    # 如果上一个 Agent 说 FINISH，就结束
    if last_suggestion == "FINISH":
        return "FINISH"

    # ============================================================
    # 以下是需要 Supervisor 自己判断的情况
    # ============================================================

    history = state.get("agent_history", [])
    last_agent = history[-1] if history else ""

    # --- 分析 Agent 刚执行完：根据分数决定去 letter 还是 reflection ---
    if last_agent == "analysis":
        best_score = state.get("best_score", 0)
        threshold = match_config.match_threshold * 100

        if best_score >= threshold:
            # 分数达标 → 生成推荐信
            return "letter"
        else:
            # 分数不达标 → 检查是否还能重试
            loop_count = state.get("loop_count", 0)
            max_loops = match_config.max_agent_loops
            if loop_count < max_loops:
                return "reflection"
            else:
                # 已达最大重试次数，用当前结果生成推荐信
                return "letter"

    # --- 检索 Agent 刚执行完：进入 HITL 等待用户确认（Phase 3c 新增）---
    # 学习要点：HITL 只在第一次检索后触发
    # 如果是 reflection_agent 触发的重试（loop_count > 0），跳过 HITL 直接分析
    # 因为用户已经确认过一次了，重试时不需要再次确认
    if last_agent == "retrieval":
        loop_count = state.get("loop_count", 0)
        if loop_count > 0:
            return "analysis"
        return "hitl"

    # --- HITL 节点完成后：进入深度分析（Phase 3c 新增）---
    if last_agent == "hitl":
        return "analysis"

    # --- 反思 Agent 刚执行完：去 retrieval 重试 ---
    if last_agent == "reflection":
        return "retrieval"

    # --- Judge 执行完：流程结束 ---
    if last_agent == "judge":
        return "FINISH"

    # --- 默认兜底：如果没有任何 agent 执行过（初始状态），从 intent 开始 ---
    if not history:
        return "intent"

    # 真正的兜底（理论上不该走到这里）
    return "FINISH"


# ============================================================
# 路由方式 B：LLM 版 Supervisor（进阶学习）
# ============================================================

# 各 Agent 的能力描述（供 LLM 理解）
AGENT_DESCRIPTIONS = {
    "intent": "意图解析：分析用户资料，提取硬性条件和语义搜索文本。通常只在流程开始时执行一次。",
    "retrieval": "混合检索：在向量数据库中搜索候选人。当需要首次检索或重试时使用。",
    "hitl": "HITL 确认：向用户展示候选人预览，等待用户确认后继续深度分析。（Phase 3c 新增）",
    "analysis": "深度分析：用 LLM 对候选人进行交叉分析和评分。在检索后执行。",
    "reflection": "策略反思：分析匹配不佳的原因，调整搜索策略。在分析分数不达标时使用。",
    "letter": "推荐信生成：为高分候选人撰写温暖的推荐信。在分析满意后执行。",
    "judge": "质量评估：用 LLM-as-Judge 评估匹配质量。在推荐信生成后执行。",
    "FINISH": "结束流程：所有 Agent 执行完毕，返回最终结果。",
}

_supervisor_prompt = """你是「心犀AI」匹配系统的调度中心（Supervisor）。
你的任务是根据当前的执行状态，决定下一步执行哪个 Agent。

## 可用的 Agent
{agent_descriptions}

## 当前状态
- 已执行的 Agent: {agent_history}
- 当前最高分: {best_score}
- 循环次数: {loop_count}/{max_loops}
- 匹配阈值: {threshold}分
- 候选人数量: {candidate_count}
- 最近操作: {last_agent}

## 决策规则
- 如果还没开始，应该先执行 intent
- intent 执行后应该去 retrieval
- retrieval 执行后应该去 analysis
- analysis 执行后：如果 best_score >= {threshold}，去 letter；否则去 reflection（如果 loop_count < {max_loops}）
- reflection 执行后应该去 retrieval（重试）
- letter 执行后应该去 judge
- judge 执行后应该 FINISH

请根据以上规则和当前状态，输出下一步的决策。
请严格按以下 JSON 格式输出：
{{
  "next_agent": "Agent名称 或 FINISH",
  "reason": "决策理由（一句话）"
}}"""


def llm_based_router(state: SupervisorState) -> str:
    """
    基于 LLM 的 Supervisor 路由器。

    将当前状态和各 Agent 的能力描述交给 LLM，让 LLM 决定下一步。

    学习要点：
    - 这是 Supervisor 模式的"完全体"，比规则版更灵活
    - 新增 Agent 时只需在 AGENT_DESCRIPTIONS 中添加描述
    - 但多一次 LLM 调用，会增加延迟和不确定性
    - 生产环境中建议：先验证规则版稳定后再尝试 LLM 版

    注意：本项目默认使用规则版（更快更稳定），LLM 版仅供学习对比。
    """
    history = state.get("agent_history", [])
    best_score = state.get("best_score", 0)
    loop_count = state.get("loop_count", 0)
    threshold = match_config.match_threshold * 100
    max_loops = match_config.max_agent_loops
    candidate_count = len(state.get("candidates", []))
    last_agent = history[-1] if history else "无"

    # 格式化 Agent 描述
    desc_text = "\n".join(f"- {name}: {desc}" for name, desc in AGENT_DESCRIPTIONS.items())

    prompt = _supervisor_prompt.format(
        agent_descriptions=desc_text,
        agent_history=" → ".join(history) if history else "无",
        best_score=best_score,
        loop_count=loop_count,
        max_loops=max_loops,
        threshold=threshold,
        candidate_count=candidate_count,
        last_agent=last_agent,
    )

    llm = create_ll(temperature=0.1)  # 极低温度，确保决策稳定
    response = llm.invoke(prompt)

    try:
        result = parse_json_response(response.content)
        next_agent = result.get("next_agent", "FINISH")
        reason = result.get("reason", "")

        # 安全校验：确保返回的是合法的 Agent 名称
        valid_names = list(AGENT_DESCRIPTIONS.keys())
        if next_agent not in valid_names:
            next_agent = "FINISH"  # 非法值，兜底结束

        messages = state.get("messages", [])
        messages.append(f"🤖 [Supervisor] 决策: {next_agent} (理由: {reason})")

        return next_agent

    except Exception:
        # LLM 解析失败，回退到规则版
        return rule_based_router(state)
