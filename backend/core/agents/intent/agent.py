"""
心犀AI - 意图解析 Agent（Phase 3c 升级：Tool Calling + ReAct 循环）
=================================================================
分析用户资料和择偶期望，提取硬性过滤条件和语义搜索文本。

学习要点：
---------
在 Supervisor 模式中，每个 Agent 都是一个独立的"专家"：
  - 只关心自己的输入（从共享 State 中读取）
  - 只更新自己负责的字段（写回共享 State）
  - 不关心调度逻辑（由 Supervisor 负责）

本 Agent 对应原版 nodes.py 中的 parse_intent 节点。

Phase 3c 改造点（Tool Calling + ReAct）：
  - async 化：支持在 astream_events 异步图中运行
  - bind_tools()：让 LLM 知道它可以调用哪些工具
  - ToolNode：自动执行 tool_calls，无需手写 if-else 分支
  - ReAct 循环：Reason（LLM 推理） + Act（工具调用） 的交替执行

ReAct 循环流程图：
  ┌─────────────────────────────────────────────────────┐
  │  HumanMessage（用户资料摘要）                        │
  │         ↓                                           │
  │  LLM（带工具）→ 有 tool_calls？                     │
  │         ├── 是 → ToolNode 执行工具                  │
  │         │        追加 ToolMessage 到消息链           │
  │         │        ↑ 返回 LLM（循环，最多3次）          │
  │         └── 否 → 进入结构化提取                     │
  └─────────────────────────────────────────────────────┘

与原版的对比：
  原版（单次调用）：prompt → LLM → 结构化输出
  新版（ReAct）：   prompt → LLM → 工具调用? → 工具结果 → LLM → 结构化输出
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode

from core.agents.supervisor.state import SupervisorState
from core.models.llm_outputs import IntentParseResult
from core.utils.llm_factory import create_ll
from core.utils.json_parser import invoke_structured


# ============================================================
# Prompt 模板
# ============================================================

_SYSTEM_PROMPT = """你是「心犀AI」婚恋匹配系统的智能意图分析师。

你的任务是分析用户的个人资料和择偶期望，提取：
1. **硬性过滤条件**：性别、年龄范围、城市（可精确筛选的条件）
2. **语义搜索文本**：将感性描述重写为适合向量检索的客观特征描述

你有以下工具可以使用：
- get_my_profile: 获取用户完整资料（当资料不完整时调用）
- get_blacklist: 获取需要排除的用户ID（生成过滤条件前调用）
- get_match_history_ids: 获取历史推荐ID（避免重复推荐时调用）

重要规则：
- 如果已有足够的用户资料，不需要调用工具直接分析即可
- 如果需要额外信息（如排除黑名单、避免重复），再调用相应工具
- 最终输出必须是格式化的 JSON，包含 hard_filters 和 rewritten_query"""

_INTENT_JSON_SCHEMA = """```json
{
  "hard_filters": {
    "target_gender": "male 或 female",
    "age_min": 数字,
    "age_max": 数字,
    "city": "城市名 或 不限",
    "exclude_ids": ["可选，黑名单+历史推荐ID列表，可为空数组"]
  },
  "rewritten_query": "重写后的语义搜索文本"
}
```"""

_EXTRACTION_INSTRUCTION = """根据以上对话上下文，请提取并输出意图解析结果。

要求：
1. hard_filters：
   - target_gender: 期望对方性别（"male" 或 "female"）
   - age_min / age_max: 期望年龄范围
   - city: 期望城市（"不限" 表示无限制）
   - exclude_ids: 来自黑名单和历史推荐的用户ID列表（如果工具返回了的话，否则为空数组）

2. rewritten_query：将用户的感性描述重写为向量检索友好的特征描述
   - 包含性格特征、兴趣爱好、生活方式等软性维度
   - 将模糊描述转化为具体词簇

请严格按以下 JSON 格式输出，不要添加任何额外文本：
"""


# ============================================================
# 工具获取辅助函数（按 svc 实例缓存，避免重复创建）
# ============================================================

_tools_cache: dict = {}


def _get_tools(svc) -> list:
    """
    获取工具列表，按 svc id 缓存。

    学习要点：
    - 工具函数是 Python 闭包，每次调用 make_intent_tools(svc) 都会创建新的函数对象
    - 用 id(svc) 作为缓存 key，确保同一个 svc 实例只创建一次工具
    """
    svc_id = id(svc)
    if svc_id not in _tools_cache:
        from core.agents.intent.tools import make_intent_tools
        _tools_cache[svc_id] = make_intent_tools(svc)
    return _tools_cache[svc_id]


# ============================================================
# Agent 入口函数（async 版本）
# ============================================================

async def intent_agent(state: SupervisorState) -> dict:
    """
    意图解析 Agent（Phase 3c：Tool Calling + ReAct 循环）。

    输入（从 State 读取）：
        - user_profile: 当前用户的完整画像

    输出（写回 State）：
        - hard_filters: 硬性过滤条件字典（含 exclude_ids）
        - rewritten_query: 重写后的语义搜索文本
        - next_agent: "retrieval"（告诉 Supervisor 下一步该检索了）
        - agent_history: 追加 "intent"

    学习要点：
    ---------
    1. async def：
       在 astream_events 异步图中，节点函数应该是 async 的。
       如果是同步函数，LangGraph 会用 run_in_executor 在线程池中运行，
       但这样会失去异步事件的细粒度控制。

    2. bind_tools(tools)：
       - 把工具的 schema 注入到 LLM 的 API 调用中（作为 tools 参数）
       - LLM 可以在输出中包含 tool_calls 字段（类型：AIMessage.tool_calls）
       - tool_choice="auto" 让 LLM 自己决定是否调用工具（默认值）

    3. ToolNode（LangGraph 预置节点）：
       - 接收 {"messages": [...]} 作为输入
       - 自动执行 messages 最后一条 AIMessage 中的所有 tool_calls
       - 返回 {"messages": [ToolMessage, ...]} 包含工具执行结果

    4. ReAct 循环（最多 3 轮）：
       - 每轮用带工具的 LLM 处理当前消息链
       - 如果 AI 输出有 tool_calls → 执行工具 → 追加 ToolMessage → 下一轮
       - 如果没有 tool_calls → 退出循环，进入结构化提取
    """
    # 获取工具（通过 AppServices 单例）
    from api.deps import AppServices
    tools = _get_tools(AppServices.get_instance())
    tool_node = ToolNode(tools)

    user = state["user_profile"]
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    messages.append("🔍 [Intent Agent] 开始意图解析（Tool Calling 模式）...")

    # ========================================
    # 创建带工具的 LLM
    # ========================================
    llm = create_ll(temperature=0.3)

    # 学习要点：bind_tools() 的作用
    # 原来：llm.invoke(messages) → LLM 只会输出文本
    # 现在：llm_with_tools.invoke(messages) → LLM 还可以输出 tool_calls
    # LLM 决定是否调用工具，以及调用哪个工具、传什么参数
    llm_with_tools = llm.bind_tools(tools)

    # ========================================
    # 构建初始消息链
    # ========================================
    lc_messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"""请分析以下用户的资料和择偶需求：

用户ID: {user.user_id}
昵称: {user.nickname}
性别: {user.gender}
年龄: {user.age}
城市: {user.city}
关于我: {user.about_me}
理想的Ta: {user.ideal_partner}
兴趣爱好: {user.hobbies}

择偶要求:
- 期望对方性别: {user.target_gender}
- 期望年龄: {user.target_age_min} ~ {user.target_age_max} 岁
- 期望城市: {user.target_city}

如需获取黑名单或历史推荐记录来优化结果，请调用相应工具。"""),
    ]

    # ========================================
    # ReAct 循环（最多 3 轮工具调用）
    # ========================================
    tool_call_log: list[str] = []
    max_rounds = 3

    for round_num in range(max_rounds):
        # LLM 决策：分析当前信息，决定是否需要调用工具
        response = llm_with_tools.invoke(lc_messages)
        lc_messages.append(response)

        if not response.tool_calls:
            # 没有工具调用 → 退出 ReAct 循环，准备结构化提取
            if tool_call_log:
                messages.append(f"   ✓ 工具调用完成（{round_num} 轮），开始结构化提取")
            else:
                messages.append("   ✓ 无需工具调用，直接提取")
            break

        # 有工具调用 → 执行工具
        tool_names = [tc["name"] for tc in response.tool_calls]
        messages.append(f"   🔧 Tool Calling ({round_num + 1}/{max_rounds}): {tool_names}")
        tool_call_log.extend(tool_names)

        # 学习要点：ToolNode 的工作原理
        # 1. 读取 lc_messages 中最后一条 AIMessage 的 tool_calls
        # 2. 逐个执行对应的工具函数（get_my_profile, get_blacklist 等）
        # 3. 将每个工具的返回值包装为 ToolMessage
        # 4. 返回 {"messages": [ToolMessage, ...]}
        tool_results = tool_node.invoke({"messages": lc_messages})
        lc_messages.extend(tool_results["messages"])
        # 现在 lc_messages 包含了工具的执行结果，下一轮 LLM 可以看到这些结果

    # ========================================
    # 结构化提取（从积累的对话上下文中提取最终结果）
    # ========================================
    # 构建提取用的 prompt，把最近的对话上下文摘要进去
    context_lines = []
    for msg in lc_messages[-8:]:  # 取最近 8 条消息
        if hasattr(msg, "content") and msg.content:
            content_str = str(msg.content)[:300]
            context_lines.append(f"  {type(msg).__name__}: {content_str}")

    context_summary = "\n".join(context_lines)

    extraction_msg = HumanMessage(content=(
        _EXTRACTION_INSTRUCTION
        + _INTENT_JSON_SCHEMA
        + f"\n\n对话上下文摘要（供参考）：\n{context_summary}"
    ))

    result: IntentParseResult = invoke_structured(
        llm, [extraction_msg], IntentParseResult
    )

    hard_filters = result.hard_filters.model_dump()

    if tool_call_log:
        messages.append(f"   工具调用汇总: {tool_call_log}")
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
