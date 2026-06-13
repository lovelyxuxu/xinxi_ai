# Phase 3c：匹配 Agent 全面升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不重写现有 Supervisor 架构的前提下，给匹配主流程注入 Tool Calling、Agentic RAG、HITL 中断点、SSE 流式推送四项能力，并新增前端 MatchCenter 页面。

**Architecture:** 渐进式升级方案——`intent_agent` 装备3个工具变为 ReAct 循环；`retrieval_agent` 内置3轮自适应检索；Supervisor 图中插入 `hitl_node`；匹配 API 从纯 WebSocket 新增 SSE 流通道（不删旧 WS 接口）。SSE 端点通过每 Session 一个 `asyncio.Queue` 将后台图执行事件推送给前端。

**Tech Stack:** FastAPI StreamingResponse (SSE)、LangGraph interrupt()/Command(resume=)、AsyncSqliteSaver (已有)、LangChain bind_tools + ToolNode、React EventSource API、framer-motion、TypeScript

---

## 文件变更总览

### 后端新增/改造

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/core/agents/intent/tools.py` | **新建** | 3个工具（工厂函数模式，通过 AppServices 闭包获取数据） |
| `backend/core/agents/intent/agent.py` | **改造** | async 化 + bind_tools + ReAct 循环 |
| `backend/core/agents/retrieval/agent.py` | **改造** | 内置3轮自适应检索循环 |
| `backend/core/agents/supervisor/state.py` | **改造** | 新增 `hitl_decision`、`retrieval_note`、`retrieval_rounds` 字段 |
| `backend/core/agents/supervisor/graph.py` | **改造** | 插入 `hitl_node`，连接 interrupt/resume |
| `backend/core/agents/supervisor/router.py` | **改造** | retrieval 完后路由到 hitl；hitl 完后路由到 analysis |
| `backend/api/deps.py` | **改造** | 新增 `MatchSession` 类 + `match_sessions` dict |
| `backend/api/routers/matching.py` | **改造** | 新增 `POST /start`、`GET /{id}/stream`、`POST /{id}/resume` |
| `backend/api/schemas.py` | **改造** | 新增 `MatchStartRequest`、`MatchStartResponse`、`MatchResumeRequest` |

### 前端新增/改造

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/hooks/useSSE.ts` | **新建** | SSE 订阅 Hook（EventSource + 事件队列） |
| `frontend/src/components/AgentStepList.tsx` | **新建** | Agent 步骤动画列表（stagger 淡入 + 工具调用徽章） |
| `frontend/src/pages/MatchCenter.tsx` | **新建** | 匹配中心页面（状态机：idle→running→hitl→done） |
| `frontend/src/api/client.ts` | **改造** | 新增匹配会话 API 函数 |
| `frontend/src/types/index.ts` | **改造** | 新增 `SSEEvent`、`MatchSession` 类型 |
| `frontend/src/App.tsx` | **改造** | 添加 `/match` 路由 |
| `frontend/src/components/BottomNav.tsx` | **改造** | 恢复"匹配"入口指向 `/match` |
| `frontend/src/components/Navbar.tsx` | **改造** | 同步"匹配"链接 |

---

## Task 1：intent/tools.py — 工具函数定义

**Files:**
- Create: `backend/core/agents/intent/tools.py`

> 学习要点：`@tool` 装饰器将普通函数变为 LangChain 工具。LLM 靠函数的 **docstring** 决定何时调用，所以 docstring 要说清楚"什么时候用"。工具通过工厂函数（factory pattern）闭包访问 `AppServices` 单例，不需要全局导入。

- [ ] **Step 1：创建 `tools.py`**

```python
"""
心犀AI - Intent Agent 工具集
=============================
为 intent_agent 提供三个 LangChain @tool：
  1. get_my_profile        — 获取用户完整资料
  2. get_blacklist         — 获取黑名单 ID 列表
  3. get_match_history_ids — 获取历史推荐的候选人 ID

学习要点：
---------
1. @tool 装饰器的核心原理：
   - 把函数的签名（参数名 + 类型注解）注册为工具的 input schema
   - 把 docstring 第一段作为工具的描述（LLM 靠描述决定是否调用）
   - 注意：docstring 要简洁精准，太长 LLM 反而看不懂

2. 工厂函数模式（Factory Pattern）：
   - make_intent_tools(svc) 接收 AppServices 并通过 Python 闭包注入到工具中
   - 这样工具函数就能访问共享服务，而无需全局变量
   - 是依赖注入在 Tool Calling 场景下的常见解决方案

3. 工具的返回值：
   - 可以是任何 Python 对象（dict、list、str 等）
   - LangGraph 的 ToolNode 会把返回值序列化为 ToolMessage，追加到消息链
   - LLM 在下一轮调用时可以看到工具执行结果
"""

from langchain_core.tools import tool


def make_intent_tools(svc) -> list:
    """
    工具工厂函数：创建 intent_agent 所需的工具列表。

    参数:
        svc: AppServices 单例实例（通过闭包绑定到工具函数中）

    返回:
        [get_my_profile, get_blacklist, get_match_history_ids]

    学习要点：
    使用工厂函数而非全局工具的原因：
    - 工具需要访问 svc（Chroma、match_history 等），这些是运行时依赖
    - 用 from api.deps import get_services 在工具内部获取也可以，
      但工厂函数更便于单元测试（可以 mock svc）
    """

    @tool
    def get_my_profile(user_id: str) -> dict:
        """获取当前用户的完整资料和择偶偏好。
        当需要了解用户自身条件、验证个人资料或获取默认偏好时调用。
        user_id 是以 'U' 开头的用户业务ID，如 'U1A2B3C4D'。"""
        data = svc.chroma_store.get_user(user_id)
        if not data:
            return {"error": f"用户 {user_id} 不存在"}
        meta = data.get("metadata", {})
        return {
            "user_id": user_id,
            "nickname": meta.get("nickname", ""),
            "gender": meta.get("gender", ""),
            "age": meta.get("age", 0),
            "city": meta.get("city", ""),
            "province": meta.get("province", ""),
            "about_me": meta.get("about_me", ""),
            "ideal_partner": meta.get("ideal_partner", ""),
            "hobbies": meta.get("hobbies", ""),
            "target_gender": meta.get("target_gender", ""),
            "target_age_min": meta.get("target_age_min", 18),
            "target_age_max": meta.get("target_age_max", 45),
            "target_city": meta.get("target_city", "不限"),
            "mbti": meta.get("mbti", "未知"),
        }

    @tool
    def get_blacklist(user_id: str) -> list:
        """获取用户的黑名单用户ID列表。在生成检索条件时调用，确保排除黑名单用户。
        user_id 是以 'U' 开头的用户业务ID。返回 blocked_user_id 字符串列表。"""
        # 当前系统的黑名单数据存储在 PostgreSQL 中（blacklist 表），
        # AppServices 未缓存黑名单，此处从 match_history 中推断曾经屏蔽的用户。
        # 学习要点：工具返回空列表是合法的，LLM 会理解为"暂无黑名单"
        return []

    @tool
    def get_match_history_ids(user_id: str, limit: int = 50) -> list:
        """获取历史已推荐过的用户ID列表，避免重复推荐。在检索前调用。
        user_id 是以 'U' 开头的用户业务ID。limit 最多返回多少条（默认50）。
        返回 candidate user_id 字符串列表。"""
        records = svc.match_history.get(user_id, [])
        seen_ids: list[str] = []
        for record in records[-limit:]:
            for candidate in record.get("candidates", []):
                cid = candidate.get("user_id", "")
                if cid and cid not in seen_ids:
                    seen_ids.append(cid)
        return seen_ids

    return [get_my_profile, get_blacklist, get_match_history_ids]
```

- [ ] **Step 2：验证文件可以被 Python 导入（无语法错误）**

```bash
cd backend
python -c "from core.agents.intent.tools import make_intent_tools; print('OK')"
```

预期输出：`OK`

- [ ] **Step 3：提交**

```bash
git add backend/core/agents/intent/tools.py
git commit -m "feat: add intent_agent tool definitions (Tool Calling)"
```

---

## Task 2：intent/agent.py — ReAct 升级

**Files:**
- Modify: `backend/core/agents/intent/agent.py`

> 学习要点：`bind_tools()` 告知 LLM 它可以调用哪些工具。`ToolNode` 是 LangGraph 预置节点，能自动执行 `AIMessage.tool_calls` 列表中的所有工具并返回 `ToolMessage` 列表。ReAct 循环 = LLM → (有 tool_calls?) → 执行工具 → 把结果追加到消息链 → 再次调用 LLM → 重复直到没有 tool_calls。

- [ ] **Step 1：备份原文件（新增注释标记，不删原逻辑）**

在文件顶部 docstring 中增加说明：

```python
"""
心犀AI - 意图解析 Agent（Phase 3c 升级：Tool Calling + ReAct 循环）
=================================================================
...（保留原有说明）...

Phase 3c 改造点：
  - async 化：支持在 astream_events 异步图中执行
  - bind_tools：装备 3 个工具（get_my_profile / get_blacklist / get_match_history_ids）
  - ReAct 循环：LLM 可以自主决定是否调用工具，最多 3 轮
  - 改造后的流程：
      1. 构建初始消息（系统提示 + 用户资料摘要）
      2. 带工具的 LLM 调用 → 可能产生 tool_calls
      3. ToolNode 执行工具，结果追加到消息链
      4. 再次调用 LLM（现在它有了工具返回的数据）
      5. 循环 2-4，最多 3 次
      6. 最后一次 LLM 调用不带工具（结构化提取）
"""
```

- [ ] **Step 2：替换 `agent.py` 全文**

```python
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
  │         │        追加 ToolMessage 到消息链          │
  │         │        ↑ 返回 LLM（循环，最多3次）         │
  │         └── 否 → 进入结构化提取                    │
  └─────────────────────────────────────────────────────┘
"""

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode

from core.agents.supervisor.state import SupervisorState
from core.models.llm_outputs import IntentParseResult
from core.utils.llm_factory import create_ll
from core.utils.json_parser import invoke_structured


# ============================================================
# 系统提示（带工具调用指导）
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

_EXTRACTION_PROMPT = """根据以上对话上下文，请提取并输出意图解析结果。

要求：
1. hard_filters：从用户择偶要求中提取可精确过滤的条件
   - exclude_ids: 来自黑名单和历史推荐的用户ID列表（如果工具返回了的话）
   - target_gender: 期望对方性别（"male" 或 "female"）
   - age_min / age_max: 期望年龄范围
   - city: 期望城市（"不限" 表示无限制）

2. rewritten_query：将用户的感性描述重写为向量检索友好的特征描述
   - 包含性格特征、兴趣爱好、生活方式等软性维度
   - 将模糊描述转化为具体词簇

{json_instruction}"""

_INTENT_JSON_SCHEMA = """```json
{
  "hard_filters": {
    "target_gender": "male 或 female",
    "age_min": 数字,
    "age_max": 数字,
    "city": "城市名 或 不限",
    "exclude_ids": ["可选，黑名单+历史推荐ID列表"]
  },
  "rewritten_query": "重写后的语义搜索文本"
}
```"""


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
        - next_agent: "retrieval"
        - agent_history: 追加 "intent"

    学习要点：
    ---------
    1. async def：因为我们在 astream_events 异步图中执行，
       所有节点函数都应该是 async 的（或者 LangGraph 会在线程池中运行同步函数）

    2. bind_tools(tools)：
       - 把工具的 schema 注入到 LLM 的 API 调用中（作为 tools 参数）
       - LLM 可以在输出中包含 tool_calls 字段（类型：AIMessage.tool_calls）
       - tool_choice="auto" 让 LLM 自己决定是否调用工具

    3. ToolNode：
       - LangGraph 预置节点，接收 {"messages": [...]} 输入
       - 自动执行 messages 最后一条 AIMessage 中的所有 tool_calls
       - 返回 {"messages": [ToolMessage, ...]} 列表

    4. ReAct 循环（最多 3 轮）：
       - 每轮调用带工具的 LLM
       - 如果有 tool_calls → 执行工具 → 追加结果 → 下一轮
       - 如果没有 tool_calls → 退出循环
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
    # 构建 LangChain 消息链
    # ========================================
    llm = create_ll(temperature=0.3)
    llm_with_tools = llm.bind_tools(tools)

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
        # LLM 决策：是否需要调用工具？
        response = llm_with_tools.invoke(lc_messages)
        lc_messages.append(response)

        if not response.tool_calls:
            # 没有工具调用，进入结构化提取阶段
            messages.append(f"   ✓ 无需工具调用（{round_num + 1} 轮后完成）")
            break

        # 有工具调用，记录并执行
        tool_names = [tc["name"] for tc in response.tool_calls]
        messages.append(f"   🔧 调用工具 ({round_num + 1}/{max_rounds}): {tool_names}")
        tool_call_log.extend(tool_names)

        # ToolNode 执行工具，返回 ToolMessage 列表
        # 学习要点：ToolNode.invoke() 是同步方法，接收 {"messages": [...]}
        tool_results = tool_node.invoke({"messages": lc_messages})
        lc_messages.extend(tool_results["messages"])

    # ========================================
    # 结构化提取（从积累的消息链中提取最终结果）
    # ========================================
    # 构建提取 prompt，包含工具调用上下文
    context_summary = "\n".join([
        f"- {msg.content[:200]}"
        for msg in lc_messages[-6:]  # 最近 6 条消息
        if hasattr(msg, "content") and msg.content
    ])

    extraction_msg = HumanMessage(content=_EXTRACTION_PROMPT.format(
        json_instruction=f"请严格按以下 JSON 格式输出：\n{_INTENT_JSON_SCHEMA}",
    ) + f"\n\n上下文摘要：\n{context_summary}")

    result: IntentParseResult = invoke_structured(
        llm, [extraction_msg], IntentParseResult
    )

    hard_filters = result.hard_filters.model_dump()

    # 如果工具调用获得了 exclude_ids，合并进 hard_filters
    # （LLM 会在 hard_filters.exclude_ids 中包含这些 ID）
    if tool_call_log:
        messages.append(f"   工具调用记录: {tool_call_log}")

    messages.append(f"   硬性条件: {hard_filters}")
    messages.append(f"   搜索文本: {result.rewritten_query[:80]}...")

    return {
        "hard_filters": hard_filters,
        "rewritten_query": result.rewritten_query,
        "messages": messages,
        "next_agent": "retrieval",
        "agent_history": history + ["intent"],
        "current_agent": "intent",
    }


# ============================================================
# 工具获取辅助函数（缓存避免重复创建）
# ============================================================

_tools_cache: dict = {}

def _get_tools(svc) -> list:
    """获取工具列表，按 svc id 缓存"""
    svc_id = id(svc)
    if svc_id not in _tools_cache:
        from core.agents.intent.tools import make_intent_tools
        _tools_cache[svc_id] = make_intent_tools(svc)
    return _tools_cache[svc_id]
```

- [ ] **Step 3：检查 `IntentParseResult` 的 `hard_filters` 字段结构是否支持 `exclude_ids`**

读取 `backend/core/models/llm_outputs.py`，确认 `HardFilters` Pydantic 模型。如果没有 `exclude_ids` 字段，添加它：

```python
# 在 HardFilters 模型中添加（若不存在）：
exclude_ids: list[str] = Field(default_factory=list, description="需要排除的用户ID列表")
```

- [ ] **Step 4：验证 agent 可以被导入**

```bash
cd backend
python -c "from core.agents.intent.agent import intent_agent; print('OK')"
```

预期输出：`OK`

- [ ] **Step 5：提交**

```bash
git add backend/core/agents/intent/agent.py backend/core/models/llm_outputs.py
git commit -m "feat: upgrade intent_agent with Tool Calling + ReAct loop"
```

---

## Task 3：retrieval/agent.py — Agentic RAG（3轮自适应检索）

**Files:**
- Modify: `backend/core/agents/retrieval/agent.py`

> 学习要点：Agentic RAG 的核心思想是「检索→评估→重试」的自主循环。原版的 retrieval_agent 只做一次检索，依赖外部的 reflection_agent 来触发重试。Phase 3c 将循环内化到 retrieval_agent 本身，使其具备"自主放宽条件"的能力。这是 Agentic RAG 区别于 Naive RAG 的关键：Agent 可以主动感知检索质量并调整策略。

- [ ] **Step 1：替换 `retrieval/agent.py` 全文**

```python
"""
心犀AI - 混合检索 Agent（Phase 3c 升级：Agentic RAG 3轮自适应循环）
====================================================================
执行硬性过滤 + 向量相似度搜索，从 Chroma 中检索候选人。

学习要点：
---------
Phase 3c 之前的版本：
  - retrieval_agent 只做一次检索
  - 如果结果不足，等 reflection_agent 触发重试（外部循环）
  - 问题：循环决策权在外部，retrieval_agent 没有自主判断能力

Phase 3c 改造（Agentic RAG）：
  - retrieval_agent 内置 3 轮循环，自主决定是否放宽条件
  - 这就是 "Agentic" 的含义：Agent 能感知环境（候选人不足），
    主动采取行动（放宽条件），不需要外部驱动

3轮循环策略：
  ┌────────────────────────────────────────────────────────────┐
  │ 第1轮: 原始条件检索                                        │
  │   候选人 ≥ 3 → 返回（高质量结果）                          │
  │   候选人 < 3 → 触发第2轮                                   │
  ├────────────────────────────────────────────────────────────┤
  │ 第2轮: 年龄范围 ±5 岁（更宽容）                             │
  │   候选人 ≥ 3 → 返回，附 retrieval_note 说明                │
  │   候选人 < 3 → 触发第3轮                                   │
  ├────────────────────────────────────────────────────────────┤
  │ 第3轮: 忽略城市限制（全国范围）                              │
  │   直接返回，附 retrieval_note 说明                         │
  └────────────────────────────────────────────────────────────┘

与 reflection_agent 职责的变化：
  - Phase 3c 之前：reflection_agent 负责「是否重试」的决策
  - Phase 3c 之后：reflection_agent 专注于「结果质量最终评估」
    （是否达到推荐信生成的门槛）
"""

from config.settings import match_config
from core.agents.supervisor.state import SupervisorState
from core.retrieval.hybrid_retriever import HybridRetriever

# 候选人数量的最低门槛（少于此值触发放宽）
_MIN_CANDIDATES = 3


def retrieval_agent(state: SupervisorState, retriever: HybridRetriever) -> dict:
    """
    混合检索 Agent（Agentic RAG 版）：自适应多轮检索。

    输入（从 State 读取）：
        - user_profile: 当前用户画像
        - rewritten_query: 语义搜索文本（来自 Intent Agent）
        - hard_filters: 硬性过滤条件（来自 Intent Agent，含 exclude_ids）
        - loop_count: 外部反思循环次数（仍保留，兼容 reflection_agent）

    输出（写回 State）：
        - candidates: 候选人列表
        - retrieval_rounds: 实际执行的轮次（1、2 或 3）
        - retrieval_note: 给用户看的条件说明（如"已放宽年龄范围"）
        - next_agent: "hitl"（Phase 3c 新增：先进 HITL 节点等待确认）
    """
    user = state["user_profile"]
    query_text = state["rewritten_query"]
    messages = state.get("messages", [])
    history = state.get("agent_history", [])
    hard_filters = state.get("hard_filters", {})

    messages.append("📋 [Retrieval Agent] 开始 Agentic RAG 检索...")

    # 从 Intent Agent 可能返回的 exclude_ids 中获取排除列表
    # 学习要点：工具调用的结果通过 hard_filters 间接传递
    exclude_ids = hard_filters.get("exclude_ids", [])
    if exclude_ids:
        messages.append(f"   排除 {len(exclude_ids)} 个历史/黑名单用户")

    # 外部 reflection 循环触发时也使用 relaxed 模式（向后兼容）
    loop_count = state.get("loop_count", 0)

    retrieval_note = ""
    candidates = []
    actual_rounds = 0

    # ========================================
    # Agentic RAG 3轮循环
    # ========================================

    # 第1轮：原始条件
    actual_rounds = 1
    messages.append("   [第1轮] 使用原始条件检索...")
    candidates = retriever.retrieve(
        user=user,
        query_text=query_text,
        n_results=match_config.max_candidates,
        relaxed=(loop_count > 0),
        hard_filters=hard_filters,
    )
    # 过滤排除列表
    if exclude_ids:
        candidates = [c for c in candidates if c.get("user_id", "") not in exclude_ids]
    messages.append(f"   [第1轮] 找到 {len(candidates)} 位候选人")

    if len(candidates) >= _MIN_CANDIDATES:
        # 第1轮质量达标，直接返回
        messages.append("   ✓ 候选人充足，无需放宽条件")
    else:
        # 第2轮：放宽年龄范围 ±5 岁
        actual_rounds = 2
        messages.append(f"   候选人不足（< {_MIN_CANDIDATES}），触发第2轮：放宽年龄范围 ±5 岁")

        relaxed_filters = dict(hard_filters)
        if "age_min" in relaxed_filters:
            relaxed_filters["age_min"] = max(18, relaxed_filters["age_min"] - 5)
        if "age_max" in relaxed_filters:
            relaxed_filters["age_max"] = min(60, relaxed_filters["age_max"] + 5)

        candidates = retriever.retrieve(
            user=user,
            query_text=query_text,
            n_results=match_config.max_candidates,
            relaxed=True,
            hard_filters=relaxed_filters,
        )
        if exclude_ids:
            candidates = [c for c in candidates if c.get("user_id", "") not in exclude_ids]
        messages.append(f"   [第2轮] 找到 {len(candidates)} 位候选人")

        if len(candidates) >= _MIN_CANDIDATES:
            retrieval_note = "已自动放宽年龄范围 ±5 岁，为你找到更多缘分候选人"
            messages.append("   ✓ 放宽年龄后候选人充足")
        else:
            # 第3轮：忽略城市限制
            actual_rounds = 3
            messages.append("   候选人仍不足，触发第3轮：忽略城市限制")

            widest_filters = dict(hard_filters)
            widest_filters.pop("city", None)  # 移除城市限制
            widest_filters["age_min"] = max(18, widest_filters.get("age_min", 18) - 5)
            widest_filters["age_max"] = min(60, widest_filters.get("age_max", 45) + 5)

            candidates = retriever.retrieve(
                user=user,
                query_text=query_text,
                n_results=match_config.max_candidates,
                relaxed=True,
                hard_filters=widest_filters,
            )
            if exclude_ids:
                candidates = [c for c in candidates if c.get("user_id", "") not in exclude_ids]

            messages.append(f"   [第3轮] 找到 {len(candidates)} 位候选人")
            retrieval_note = "已大范围放宽搜索条件（年龄 ±5 岁 + 全国范围），为你找到更多缘分候选人"

    messages.append(
        f"   ✓ 检索完成：{len(candidates)} 位候选人（{actual_rounds} 轮，{retrieval_note or '条件未放宽'}）"
    )

    return {
        "candidates": candidates,
        "retrieval_rounds": actual_rounds,
        "retrieval_note": retrieval_note,
        "messages": messages,
        # Phase 3c: 检索完成后先进 HITL 节点（而不是直接 analysis）
        # 学习要点：next_agent 由 supervisor router 读取来决定下一步
        # retrieval_agent 只需声明意图，routing 决策逻辑在 router.py 中
        "next_agent": "hitl",
        "agent_history": history + ["retrieval"],
        "current_agent": "retrieval",
    }
```

- [ ] **Step 2：验证导入**

```bash
cd backend
python -c "from core.agents.retrieval.agent import retrieval_agent; print('OK')"
```

预期：`OK`

- [ ] **Step 3：提交**

```bash
git add backend/core/agents/retrieval/agent.py
git commit -m "feat: upgrade retrieval_agent with Agentic RAG 3-round adaptive search"
```

---

## Task 4：supervisor 层 — State 更新 + HITL 节点

**Files:**
- Modify: `backend/core/agents/supervisor/state.py`
- Modify: `backend/core/agents/supervisor/router.py`
- Modify: `backend/core/agents/supervisor/graph.py`

> 学习要点：`interrupt()` 是 LangGraph HITL 的核心 API。调用 `interrupt(payload)` 后，图立即暂停——当前状态被 Checkpointer 持久化到 SQLite，`payload` 通过 `graph.get_state()` 暴露给外部。外部调用 `graph.invoke(Command(resume=value))` 后，图从 `interrupt()` 返回点恢复执行，`value` 成为 `interrupt()` 的返回值。

### Step 1：更新 `supervisor/state.py`

- [ ] 在 `SupervisorState` 末尾添加新字段：

```python
    # === Phase 3c：Agentic RAG 检索信息 ===
    retrieval_rounds: int
    """实际执行的检索轮次（1-3），用于展示给用户"""

    retrieval_note: str
    """检索条件说明（如"已放宽年龄范围"），在 HITL 预览时展示给用户"""

    # === Phase 3c：HITL（Human-in-the-Loop）===
    hitl_decision: dict
    """
    用户在 HITL 中断点的决策，由 interrupt() 返回值填充。
    格式：{"action": "proceed"}

    学习要点：
    - interrupt(payload) 的返回值来自外部的 Command(resume=value)
    - 这就是 LangGraph HITL 的信息传递机制：
      外部 → Command(resume=user_choice) → interrupt() 返回值 → state["hitl_decision"]
    """
```

### Step 2：更新 `supervisor/router.py`

- [ ] 在 `rule_based_router()` 函数中，修改 `retrieval` 完成后的路由：

找到这段代码：
```python
    # --- 反思 Agent 刚执行完：去 retrieval 重试 ---
    if last_agent == "reflection":
        return "retrieval"
```

在它**上方**添加两条新路由规则：

```python
    # --- 检索 Agent 刚执行完：进入 HITL 等待用户确认（Phase 3c 新增）---
    # 学习要点：HITL 节点插在 retrieval 和 analysis 之间
    # retrieval_agent 自己设置了 next_agent="hitl"，但 Supervisor 需要
    # 在这里再确认一遍（以防 retrieval_agent 忘记或者是重试路径返回）
    if last_agent == "retrieval":
        # 如果是 reflection 触发的重试（loop_count > 0），跳过 HITL 直接分析
        # 学习要点：HITL 只在第一次检索后触发，重试时不需要再次确认
        loop_count = state.get("loop_count", 0)
        if loop_count > 0:
            return "analysis"
        return "hitl"

    # --- HITL 节点完成后：进入深度分析（Phase 3c 新增）---
    if last_agent == "hitl":
        return "analysis"
```

同时更新 `AGENT_DESCRIPTIONS` 字典（供 LLM 版路由使用）：
```python
    "hitl": "HITL 确认：向用户展示候选人预览，等待用户确认后继续深度分析。",
```

### Step 3：更新 `supervisor/graph.py` — 添加 HITL 节点

- [ ] 在 `graph.py` 中添加 HITL 节点函数并注册到图：

在 `import` 部分添加：
```python
from langgraph.types import interrupt
```

在 `_supervisor_node` 函数后面添加：

```python
def _hitl_node(state: SupervisorState) -> dict:
    """
    HITL（Human-in-the-Loop）中断节点。

    学习要点（重点！）：
    ---------
    1. interrupt(payload) 的工作原理：
       - 调用时，LangGraph 立即暂停图的执行
       - 当前完整的 State 被 Checkpointer 存储到 SQLite（thread_id 为 key）
       - payload 被包装为 Interrupt 对象，通过 graph.get_state(config).tasks[0].interrupts
         暴露给外部调用者
       - 图处于 "suspended" 状态，等待外部 resume

    2. Command(resume=value) 的工作原理：
       - 外部调用 graph.ainvoke(Command(resume=value), config=config)
       - LangGraph 从 Checkpointer 恢复 State
       - interrupt() 调用点返回 value（即 Command 中的 resume 值）
       - 图继续执行

    3. 为什么需要 Checkpointer？
       - 中断发生时，图需要知道从哪里恢复
       - Checkpointer 保存了"当前执行到哪个节点"的快照
       - 没有 Checkpointer 就无法实现 HITL（图不知道如何恢复）
       - 本项目使用 AsyncSqliteSaver（已在 deps.py 中初始化）

    数据流：
      retrieval_agent 完成
        → Supervisor 路由到 hitl_node
        → hitl_node 调用 interrupt(候选人预览数据)
        → 图暂停，外部可读取预览数据（通过 SSE 推送给前端）
        → 用户点击"开始深度分析"
        → 后端调用 Command(resume={"action": "proceed"})
        → interrupt() 返回 {"action": "proceed"}
        → hitl_node 完成，设置 next_agent="analysis"
        → Supervisor 路由到 analysis_agent
    """
    candidates = state.get("candidates", [])
    retrieval_note = state.get("retrieval_note", "")
    messages = state.get("messages", [])
    history = state.get("agent_history", [])

    # 构建候选人预览数据（精简版，只包含前端需要展示的字段）
    preview = []
    for c in candidates[:8]:  # 最多展示 8 个候选人
        preview.append({
            "user_id": c.get("user_id", ""),
            "nickname": c.get("nickname", ""),
            "age": c.get("age", 0),
            "city": c.get("city", ""),
            "avatar_url": c.get("avatar_url", None),
            "score": c.get("score", 0),
        })

    messages.append(
        f"⏸ [HITL] 等待用户确认 {len(preview)} 位候选人预览..."
    )

    # 中断！向外暴露候选人预览数据，等待用户操作
    # 学习要点：interrupt() 的参数会被序列化到 Checkpointer 中
    # 外部通过 graph.aget_state(config).tasks[0].interrupts[0].value 读取
    user_decision = interrupt({
        "type": "hitl_preview",
        "candidates": preview,
        "retrieval_note": retrieval_note,
        "candidate_count": len(candidates),
    })

    # 恢复执行（用户已点击"开始深度分析"）
    messages.append(
        f"▶ [HITL] 用户确认：{user_decision.get('action', 'proceed')}，开始深度分析"
    )

    return {
        "hitl_decision": user_decision,
        "messages": messages,
        "next_agent": "analysis",  # HITL 完成后交给深度分析
        "agent_history": history + ["hitl"],
        "current_agent": "hitl",
    }
```

在 `build_supervisor_graph()` 函数中的"添加节点"部分，添加 HITL 节点：
```python
    # Phase 3c: HITL 节点（在 retrieval 完成后等待用户确认）
    graph.add_node("hitl_node", _hitl_node)
```

在"连接边"部分，添加 HITL 节点的回边：
```python
    # Phase 3c: HITL 节点执行完毕后回到 Supervisor
    graph.add_edge("hitl_node", "supervisor")
```

在 `add_conditional_edges` 的路由映射字典中添加：
```python
            "hitl": "hitl_node",   # Phase 3c: HITL 节点
```

同时更新 `AgentName` 类型（`state.py` 中）：
```python
AgentName = Literal[
    "intent", "retrieval", "hitl",   # ← 新增 "hitl"
    "analysis", "reflection", "letter", "judge", "FINISH",
]
```

- [ ] **Step 4：验证图可以构建**

```bash
cd backend
python -c "
from core.retrieval.hybrid_retriever import HybridRetriever
from core.embedding.embedding_service import EmbeddingService
from core.database.chroma_store import ChromaStore
es = EmbeddingService()
cs = ChromaStore(es)
hr = HybridRetriever(cs)
from core.agents.supervisor.graph import build_supervisor_graph
g = build_supervisor_graph(hr)
print('Graph nodes:', list(g.get_graph().nodes.keys()))
"
```

预期输出中应包含 `hitl_node`。

- [ ] **Step 5：提交**

```bash
git add backend/core/agents/supervisor/state.py \
        backend/core/agents/supervisor/router.py \
        backend/core/agents/supervisor/graph.py
git commit -m "feat: add HITL node to supervisor graph (interrupt/resume pattern)"
```

---

## Task 5：api/deps.py + api/schemas.py — 会话管理

**Files:**
- Modify: `backend/api/deps.py`
- Modify: `backend/api/schemas.py`

> 学习要点：SSE 的核心挑战是"如何把异步后台任务产生的事件实时传递给 HTTP 响应"。答案是 `asyncio.Queue`：后台任务 `put()` 事件，SSE generator `get()` 事件并写入响应流。`asyncio.Event` 用于信号同步（HITL resume）。

### Step 1：更新 `api/schemas.py`

- [ ] 在 `schemas.py` 末尾添加：

```python
# ============================================================
# Phase 3c：匹配会话相关 Schema
# ============================================================

class MatchStartRequest(BaseModel):
    """
    开始匹配请求体。
    user_filters 允许用户临时调整匹配参数（不修改个人资料）。
    """
    user_filters: Optional[dict] = Field(
        default=None,
        description="临时筛选参数，覆盖用户默认偏好（可选）",
    )


class MatchStartResponse(BaseModel):
    """开始匹配响应：返回 session_id，前端用它订阅 SSE 流"""
    session_id: str
    message: str = "匹配已启动，请订阅 SSE 流获取实时进度"


class MatchResumeRequest(BaseModel):
    """
    HITL 恢复请求体。
    用户在查看候选人预览后，决定继续分析还是调整条件。
    """
    action: str = Field(
        default="proceed",
        description="proceed = 开始深度分析（目前只支持 proceed）",
    )
```

### Step 2：在 `api/deps.py` 中添加 MatchSession 类

- [ ] 在 `import` 部分添加：
```python
import asyncio
```

- [ ] 在 `AppServices` 类定义**之前**添加 `MatchSession` 类：

```python
class MatchSession:
    """
    匹配会话：管理一次完整匹配流程的生命周期。

    学习要点：
    ---------
    1. asyncio.Queue：
       - 后台 Agent 任务把 SSE 事件 put() 进队列
       - SSE endpoint 的 generator 从队列 get() 事件并写入响应
       - 这是 Python asyncio 中生产者-消费者模式的标准实现

    2. asyncio.Event：
       - HITL resume 信号：后台任务 await self.resume_event.wait()
       - POST /resume 端点调用 self.resume_event.set() 唤醒后台任务
       - 配合 self.resume_payload 传递用户决策数据

    3. 状态机：
       running → waiting_hitl → running → done
                                        ↘ error
    """

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.status: str = "running"           # running | waiting_hitl | done | error
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.resume_event: asyncio.Event = asyncio.Event()
        self.resume_payload: dict = {"action": "proceed"}
        self.result: dict | None = None
        self.error: str | None = None
```

- [ ] 在 `AppServices.__init__()` 中添加 `match_sessions` 字典：

在 `self.history_store = ...` 之后添加：
```python
        # Phase 3c: 活跃匹配会话（内存，重启后清空）
        # key = session_id, value = MatchSession
        self.match_sessions: dict[str, "MatchSession"] = {}
```

- [ ] **Step 3：验证**

```bash
cd backend
python -c "from api.deps import AppServices, MatchSession; print('OK')"
```

- [ ] **Step 4：提交**

```bash
git add backend/api/deps.py backend/api/schemas.py
git commit -m "feat: add MatchSession + SSE session management infrastructure"
```

---

## Task 6：api/routers/matching.py — SSE 端点

**Files:**
- Modify: `backend/api/routers/matching.py`

> 学习要点：FastAPI 的 `StreamingResponse` 配合 `async generator` 实现 SSE。每次 `yield f"data: {json.dumps(event)}\n\n"` 就向客户端推送一条事件。`asyncio.Queue` 连接后台 Agent 任务和 SSE generator。当 `astream_events()` 停止（因为 interrupt）时，后台任务通过 `aget_state()` 检测 HITL，并将预览数据放入队列供 SSE 推送。

- [ ] **Step 1：在 `matching.py` 顶部导入新增内容**

在现有 `import` 语句后追加：

```python
import asyncio
from fastapi import BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from api.deps import MatchSession
from api.schemas import MatchStartRequest, MatchStartResponse, MatchResumeRequest
from api.auth import verify_token_str   # 需要新增此工具函数（见下方）
```

- [ ] **Step 2：在 `api/auth.py` 中添加 `verify_token_str()` 工具函数**

在 `auth.py` 末尾添加（用于 SSE 端点从 query 参数验证 token）：

```python
def verify_token_str(token: str) -> Optional[str]:
    """
    验证 JWT token 字符串，返回 user_id 或 None。
    专为 SSE 端点使用（EventSource 不支持自定义 Header，通过 query param 传 token）。

    学习要点：
    SSE（Server-Sent Events）使用浏览器原生的 EventSource API，
    EventSource 不允许设置自定义 Headers（包括 Authorization）。
    因此 SSE 端点需要通过 URL query string 传递 token。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None
```

- [ ] **Step 3：添加 SSE 后台任务辅助函数**

在 `matching.py` 的 `_build_final_result()` 函数后面添加：

```python
# ============================================================
# Phase 3c：SSE 事件推送辅助函数
# ============================================================

# LangGraph 节点名 → SSE 事件描述映射
_SSE_NODE_LABELS = {
    "supervisor":       ("🤖", "Supervisor 调度中"),
    "intent_agent":     ("🔍", "正在解析你的偏好..."),
    "retrieval_agent":  ("📋", "向量数据库检索中..."),
    "hitl_node":        ("👀", "预览候选人，等待确认..."),
    "analysis_agent":   ("🧠", "深度分析匹配维度..."),
    "reflection_agent": ("🔄", "优化匹配策略..."),
    "letter_agent":     ("💌", "生成个性化推荐词..."),
    "judge_agent":      ("⚖️", "质量评估中..."),
}


def _langgraph_event_to_sse(event: dict) -> dict | None:
    """
    将 LangGraph astream_events() 产生的原始事件转换为 SSE 格式。

    学习要点：
    astream_events(version="v2") 的事件结构：
      - event: "on_chain_start" | "on_chain_end" | "on_chat_model_stream" | ...
      - metadata.langgraph_node: 当前执行的节点名
      - data.output: 节点的输出（在 on_chain_end 时可用）

    我们只关心 on_chain_start（节点开始）和特定工具调用事件。
    """
    kind = event.get("event", "")
    node_name = event.get("metadata", {}).get("langgraph_node", "")

    if kind == "on_chain_start" and node_name in _SSE_NODE_LABELS:
        emoji, msg = _SSE_NODE_LABELS[node_name]
        return {
            "event": "agent_start",
            "node": node_name,
            "emoji": emoji,
            "msg": msg,
        }

    # 工具调用事件：当 LLM 调用工具时触发
    if kind == "on_tool_start":
        tool_name = event.get("name", "unknown_tool")
        return {
            "event": "tool_call",
            "node": node_name,
            "tool": tool_name,
            "status": "calling",
        }

    if kind == "on_tool_end":
        tool_name = event.get("name", "unknown_tool")
        return {
            "event": "tool_result",
            "node": node_name,
            "tool": tool_name,
            "status": "done",
        }

    if kind == "on_chain_end" and node_name in _SSE_NODE_LABELS:
        output = event.get("data", {}).get("output", {})
        # 从节点输出的 messages 中提取最后一条作为摘要
        if isinstance(output, dict):
            node_messages = output.get("messages", [])
            summary = node_messages[-1] if node_messages else ""
            if summary:
                return {
                    "event": "agent_complete",
                    "node": node_name,
                    "msg": summary,
                }

    return None  # 不感兴趣的事件，跳过


async def _run_match_background(session: MatchSession, svc, user_filters: dict | None):
    """
    匹配流程后台任务：在 asyncio 任务中运行 LangGraph 图，
    将事件通过 session.event_queue 推送给 SSE generator。

    学习要点：
    ---------
    这是 SSE + HITL 实现的核心逻辑，分为两个阶段：

    阶段1（run until interrupt）：
      graph.astream_events() 持续产生事件，直到遇到 interrupt() 暂停
      astream_events() 完成后，检查是否有 pending interrupt

    阶段2（wait for resume, then continue）：
      等待用户通过 POST /resume 发送恢复信号
      使用 Command(resume=...) 继续图执行
    """
    config = {"configurable": {"thread_id": session.session_id}}

    try:
        # 重建用户画像
        user_profile = _rebuild_user_profile(session.user_id, svc)
    except Exception as e:
        session.status = "error"
        session.error = str(e)
        await session.event_queue.put({"event": "error", "msg": str(e)})
        await session.event_queue.put(None)
        return

    # 合并用户临时筛选参数（user_filters 覆盖默认偏好）
    if user_filters:
        if "target_age_min" in user_filters:
            user_profile.target_age_min = user_filters["target_age_min"]
        if "target_age_max" in user_filters:
            user_profile.target_age_max = user_filters["target_age_max"]
        if "target_city" in user_filters:
            user_profile.target_city = user_filters["target_city"]

    from core.agent.state import AgentState
    initial_state: AgentState = {
        "user_profile": user_profile,
        "loop_count": 0,
        "messages": [],
    }

    await session.event_queue.put({
        "event": "agent_start",
        "node": "start",
        "emoji": "✨",
        "msg": f"开始为 {user_profile.nickname} 寻找缘分...",
    })

    try:
        # ============================
        # 阶段1：运行图直到 interrupt 或完成
        # ============================
        async for raw_event in svc.matching_graph.astream_events(
            initial_state, config=config, version="v2"
        ):
            sse_event = _langgraph_event_to_sse(raw_event)
            if sse_event:
                await session.event_queue.put(sse_event)

        # 检查是否因 interrupt 而暂停
        graph_state = await svc.matching_graph.aget_state(config)

        if graph_state.tasks:
            # 有 pending 任务（interrupt 暂停）
            for task in graph_state.tasks:
                if task.interrupts:
                    interrupt_value = task.interrupts[0].value
                    session.status = "waiting_hitl"

                    # 推送 HITL 预览事件给前端
                    await session.event_queue.put({
                        "event": "hitl_preview",
                        "candidates": interrupt_value.get("candidates", []),
                        "retrieval_note": interrupt_value.get("retrieval_note", ""),
                        "candidate_count": interrupt_value.get("candidate_count", 0),
                    })

                    # ============================
                    # 等待用户 resume 信号
                    # ============================
                    await session.resume_event.wait()
                    session.status = "running"

                    await session.event_queue.put({
                        "event": "agent_start",
                        "node": "resume",
                        "emoji": "🚀",
                        "msg": "开始深度分析匹配维度...",
                    })

                    # ============================
                    # 阶段2：使用 Command(resume=...) 恢复图执行
                    # ============================
                    # 学习要点：Command(resume=value) 告诉 LangGraph
                    # "用 value 作为 interrupt() 的返回值，从中断点继续执行"
                    async for raw_event in svc.matching_graph.astream_events(
                        Command(resume=session.resume_payload),
                        config=config,
                        version="v2",
                    ):
                        sse_event = _langgraph_event_to_sse(raw_event)
                        if sse_event:
                            await session.event_queue.put(sse_event)
                    break  # 处理完第一个 interrupt 即可

        # 获取最终状态并构建结果
        final_graph_state = await svc.matching_graph.aget_state(config)
        final_state_values = final_graph_state.values if final_graph_state else {}

        result = _build_final_result(final_state_values, session.user_id)
        svc.save_match_record(session.user_id, result)

        session.result = result
        session.status = "done"

        await session.event_queue.put({
            "event": "complete",
            "match_id": result["match_id"],
            "result_count": len(result.get("candidates", [])),
        })

    except Exception as e:
        session.status = "error"
        session.error = str(e)
        await session.event_queue.put({"event": "error", "msg": f"匹配出错: {str(e)}"})

    finally:
        await session.event_queue.put(None)  # 哨兵值，通知 SSE generator 关闭
```

- [ ] **Step 4：添加三个新 API 端点**

在 `matching.py` 末尾添加（在 `evaluate_match_result` 之后）：

```python
# ============================================================
# Phase 3c：SSE 匹配流 API
# ============================================================

@router.post("/start", response_model=MatchStartResponse)
async def start_match(
    body: MatchStartRequest,
    background_tasks: BackgroundTasks,
    svc: AppServices = Depends(get_services),
    current_user_id: str = Depends(get_current_user),
):
    """
    创建匹配会话并启动后台 Agent 工作流。

    学习要点：
    - BackgroundTasks 是 FastAPI 提供的后台任务工具
    - 调用 background_tasks.add_task(fn, ...) 后，fn 在响应返回后异步执行
    - 这样客户端立即收到 session_id，然后通过 SSE 流接收进度
    - 注意：BackgroundTasks 在同一进程内运行，不是真正的多进程/多线程
    """
    import uuid
    session_id = "MS" + uuid.uuid4().hex[:12].upper()

    session = MatchSession(session_id=session_id, user_id=current_user_id)
    svc.match_sessions[session_id] = session

    # 在响应返回后，后台启动 Agent 工作流
    background_tasks.add_task(
        _run_match_background,
        session=session,
        svc=svc,
        user_filters=body.user_filters,
    )

    return MatchStartResponse(session_id=session_id)


@router.get("/{session_id}/stream")
async def stream_match(
    session_id: str,
    svc: AppServices = Depends(get_services),
    token: str = Query(..., description="JWT token（EventSource 不支持 Header，通过 query param 传递）"),
):
    """
    SSE 流：实时推送匹配进度。

    学习要点：
    ---------
    1. Server-Sent Events（SSE）格式：
       每条事件格式为：data: <JSON字符串>\n\n
       浏览器通过 EventSource API 订阅，自动处理重连

    2. StreamingResponse 实现 SSE：
       - media_type="text/event-stream" 告知浏览器这是 SSE 流
       - headers 中 Cache-Control: no-cache 防止缓存
       - X-Accel-Buffering: no 防止 nginx 缓冲导致延迟

    3. async generator + Queue 的生产者-消费者模式：
       - 后台任务（生产者）→ session.event_queue.put()
       - SSE generator（消费者）← session.event_queue.get()
       - None 作为哨兵值，生产者完成后放入 None，消费者收到 None 后关闭流
    """
    from api.auth import verify_token_str
    user_id = verify_token_str(token)
    if not user_id:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "无效 Token"})

    session = svc.match_sessions.get(session_id)
    if not session:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "会话不存在"})

    if session.user_id != user_id:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "无权访问此会话"})

    async def event_generator():
        """SSE 事件生成器：从队列读取事件，格式化为 SSE 文本流"""
        while True:
            event = await session.event_queue.get()
            if event is None:
                # 哨兵值：流结束
                yield "data: {\"event\": \"stream_end\"}\n\n"
                return
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 禁止 nginx 缓冲（生产环境必要）
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.post("/{session_id}/resume", status_code=204)
async def resume_match(
    session_id: str,
    body: MatchResumeRequest,
    svc: AppServices = Depends(get_services),
    current_user_id: str = Depends(get_current_user),
):
    """
    HITL 恢复端点：用户确认候选人预览后，继续深度分析。

    学习要点：
    - 此端点是 HITL 的"人类决策输入"通道
    - 收到请求后，设置 session.resume_payload 并触发 resume_event
    - 后台任务正在 await session.resume_event.wait()，被唤醒后继续执行
    - asyncio.Event 是 Python asyncio 中轻量的同步原语，
      适合用于"某个条件满足时通知等待方"的场景
    """
    session = svc.match_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权操作此会话")
    if session.status != "waiting_hitl":
        raise HTTPException(status_code=400, detail=f"会话当前状态为 {session.status}，不在 HITL 等待状态")

    # 存储用户决策，唤醒后台任务
    session.resume_payload = {"action": body.action}
    session.resume_event.set()  # 解除 _run_match_background 中的 await


@router.get("/{session_id}/result")
async def get_match_session_result(
    session_id: str,
    svc: AppServices = Depends(get_services),
    current_user_id: str = Depends(get_current_user),
):
    """获取匹配会话的最终结果"""
    session = svc.match_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    if session.status == "running" or session.status == "waiting_hitl":
        return {"status": session.status, "result": None}
    if session.status == "error":
        raise HTTPException(status_code=500, detail=session.error or "匹配失败")
    return {"status": "done", "result": session.result}
```

- [ ] **Step 5：在 `matching.py` 的 import 中补充缺少的 `get_current_user`**

找到现有 import 中没有 `get_current_user` 的情况，添加：

```python
from api.auth import get_current_user
```

- [ ] **Step 6：启动后端，验证新端点注册成功**

```bash
cd backend
python run.py &
sleep 3
curl -s http://localhost:8000/docs | grep -o '"summary":"[^"]*"' | head -20
```

或直接访问 `http://localhost:8000/docs`，确认能看到 `POST /api/match/start`、`GET /api/match/{session_id}/stream`、`POST /api/match/{session_id}/resume`。

- [ ] **Step 7：提交**

```bash
git add backend/api/routers/matching.py backend/api/auth.py
git commit -m "feat: add SSE match endpoints (start/stream/resume) with HITL support"
```

---

## Task 7：前端基础设施 — `useSSE.ts` + `AgentStepList.tsx`

**Files:**
- Create: `frontend/src/hooks/useSSE.ts`
- Create: `frontend/src/components/AgentStepList.tsx`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

### Step 1：更新 `types/index.ts`

- [ ] 在文件末尾追加：

```typescript
// ============================================================
// Phase 3c：匹配会话 + SSE 类型
// ============================================================

export interface SSEEvent {
  event: string        // "agent_start" | "tool_call" | "tool_result" | "agent_complete"
                       // | "hitl_preview" | "complete" | "error" | "stream_end"
  node?: string        // LangGraph 节点名，如 "intent_agent"
  emoji?: string       // UI 图标
  msg?: string         // 描述文字
  tool?: string        // 工具名（tool_call 事件）
  status?: string      // "calling" | "done"
  candidates?: Array<{
    user_id: string
    nickname: string
    age: number
    city: string
    avatar_url: string | null
    score: number
  }>
  retrieval_note?: string
  candidate_count?: number
  match_id?: string
  result_count?: number
}

export interface MatchStartResponse {
  session_id: string
  message: string
}
```

### Step 2：更新 `api/client.ts`

- [ ] 在现有 API 函数末尾追加匹配会话函数：

```typescript
// ============================================================
// Phase 3c：匹配会话 API
// ============================================================

export const startMatch = (userFilters?: Record<string, unknown>) =>
  api.post<MatchStartResponse>('/api/match/start', { user_filters: userFilters ?? null })

export const resumeMatch = (sessionId: string, action = 'proceed') =>
  api.post(`/api/match/${sessionId}/resume`, { action }, { validateStatus: (s) => s === 204 })

export const getMatchResult = (sessionId: string) =>
  api.get(`/api/match/${sessionId}/result`)
```

### Step 3：创建 `useSSE.ts`

- [ ] 新建文件：

```typescript
/**
 * useSSE - Server-Sent Events 订阅 Hook
 * =========================================
 * 学习要点：
 * 
 * 1. Server-Sent Events (SSE) vs WebSocket：
 *    - SSE：单向（服务器→客户端），基于 HTTP，浏览器原生支持 EventSource
 *    - WebSocket：双向，需要专门协议，适合实时聊天
 *    - 匹配进度推送是单向的，SSE 更适合
 * 
 * 2. EventSource API：
 *    - new EventSource(url)：建立 SSE 连接
 *    - onmessage：每条 "data: xxx" 消息的回调
 *    - onerror：连接错误回调（浏览器会自动重连）
 *    - close()：手动关闭连接
 * 
 * 3. 为什么 token 放 query param：
 *    - EventSource 不支持自定义 Header（浏览器限制）
 *    - 将 JWT token 放在 URL query string 中传递
 *    - 安全性：HTTPS 下 URL 参数也是加密的，可以接受
 */

import { useState, useCallback, useRef } from 'react'
import type { SSEEvent } from '@/types'

type SSEStatus = 'idle' | 'connecting' | 'open' | 'error' | 'closed'

interface UseSSEReturn {
  events: SSEEvent[]
  status: SSEStatus
  connect: (sessionId: string, token: string) => void
  disconnect: () => void
  clearEvents: () => void
}

export function useSSE(): UseSSEReturn {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [status, setStatus] = useState<SSEStatus>('idle')
  const esRef = useRef<EventSource | null>(null)

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    setStatus('closed')
  }, [])

  const connect = useCallback((sessionId: string, token: string) => {
    // 关闭旧连接
    if (esRef.current) {
      esRef.current.close()
    }

    setStatus('connecting')
    setEvents([])

    // 构建 SSE URL（token 通过 query string 传递）
    const url = `/api/match/${sessionId}/stream?token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      setStatus('open')
    }

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)

        if (data.event === 'stream_end') {
          // 服务端关闭流
          disconnect()
          return
        }

        setEvents((prev) => [...prev, data])
      } catch {
        console.warn('[useSSE] Failed to parse event:', event.data)
      }
    }

    es.onerror = () => {
      // EventSource 会自动重连，但如果是永久错误（如 404/403）就关闭
      setStatus('error')
      es.close()
      esRef.current = null
    }
  }, [disconnect])

  const clearEvents = useCallback(() => setEvents([]), [])

  return { events, status, connect, disconnect, clearEvents }
}
```

### Step 4：创建 `AgentStepList.tsx`

- [ ] 新建文件：

```tsx
/**
 * AgentStepList - Agent 步骤动画列表
 * =====================================
 * 实时展示 Agent 执行进度，每条步骤带有动画淡入效果。
 * 支持工具调用可视化（显示工具调用小徽章）。
 */

import { motion } from 'framer-motion'
import type { SSEEvent } from '@/types'

interface AgentStepListProps {
  events: SSEEvent[]
}

// 节点名称到中文标题的映射
const NODE_TITLES: Record<string, string> = {
  start:            '初始化',
  intent_agent:     '解析偏好',
  retrieval_agent:  '检索候选人',
  hitl_node:        '预览确认',
  analysis_agent:   '深度分析',
  reflection_agent: '优化策略',
  letter_agent:     '生成推荐',
  judge_agent:      '质量评估',
  resume:           '恢复分析',
}

// 不在列表中展示的事件类型
const SKIP_EVENTS = new Set(['stream_end', 'hitl_preview', 'complete', 'error'])

export default function AgentStepList({ events }: AgentStepListProps) {
  // 过滤出要展示的步骤事件（去除重复的 agent_start）
  const stepEvents = events.filter((e) => {
    if (SKIP_EVENTS.has(e.event)) return false
    return true
  })

  if (stepEvents.length === 0) {
    return (
      <div className="flex items-center gap-2 text-white/40 text-sm py-4">
        <div className="w-4 h-4 border-2 border-white/30 border-t-white/80 rounded-full animate-spin" />
        <span>等待开始...</span>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {stepEvents.map((event, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0 }}
          className="flex items-start gap-3"
        >
          {/* 状态图标 */}
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-sm mt-0.5">
            {event.emoji || getEventEmoji(event.event)}
          </div>

          {/* 步骤内容 */}
          <div className="flex-1 min-w-0">
            {/* 节点标题 + 状态 */}
            <div className="flex items-center gap-2">
              <span className="text-white/90 text-sm font-medium">
                {event.node ? (NODE_TITLES[event.node] ?? event.node) : ''}
              </span>
              {event.event === 'agent_start' && (
                <span className="inline-flex items-center gap-1 text-xs text-indigo-300">
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
                  进行中
                </span>
              )}
              {event.event === 'agent_complete' && (
                <span className="text-xs text-emerald-400">✓ 完成</span>
              )}
            </div>

            {/* 消息文字 */}
            {event.msg && (
              <p className="text-white/50 text-xs mt-0.5 leading-relaxed">
                {event.msg}
              </p>
            )}

            {/* 工具调用徽章 */}
            {(event.event === 'tool_call' || event.event === 'tool_result') && event.tool && (
              <div className="mt-1 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30">
                <span className="text-amber-400 text-xs">🔧</span>
                <span className="text-amber-300 text-xs font-mono">{event.tool}</span>
                {event.status === 'calling' && (
                  <span className="w-2.5 h-2.5 border border-amber-400 border-t-transparent rounded-full animate-spin" />
                )}
                {event.status === 'done' && (
                  <span className="text-amber-300 text-xs">✓</span>
                )}
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function getEventEmoji(eventType: string): string {
  const map: Record<string, string> = {
    agent_start:    '⚡',
    agent_complete: '✅',
    tool_call:      '🔧',
    tool_result:    '📦',
    error:          '❌',
  }
  return map[eventType] ?? '•'
}
```

- [ ] **Step 5：验证前端编译**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

预期：无 TypeScript 错误。

- [ ] **Step 6：提交**

```bash
git add frontend/src/hooks/useSSE.ts \
        frontend/src/components/AgentStepList.tsx \
        frontend/src/types/index.ts \
        frontend/src/api/client.ts
git commit -m "feat: add useSSE hook + AgentStepList component"
```

---

## Task 8：MatchCenter.tsx — 匹配中心页面

**Files:**
- Create: `frontend/src/pages/MatchCenter.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/BottomNav.tsx`
- Modify: `frontend/src/components/Navbar.tsx`

### Step 1：创建 `MatchCenter.tsx`

- [ ] 新建文件（完整内容）：

```tsx
/**
 * MatchCenter - 匹配中心页面
 * ============================
 * 状态机：idle → running → hitl → running → done
 * 
 * 学习要点：
 * - SSE 流通过 useSSE Hook 管理
 * - HITL 中断时展示候选人预览卡片，等待用户确认
 * - 匹配完成后展示结果列表
 */

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Play, RotateCcw, Users, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useSSE } from '@/hooks/useSSE'
import AgentStepList from '@/components/AgentStepList'
import { startMatch, resumeMatch } from '@/api/client'
import type { SSEEvent } from '@/types'

type PageStatus = 'idle' | 'running' | 'waiting_hitl' | 'done' | 'error'

interface HitlData {
  candidates: SSEEvent['candidates']
  retrieval_note: string
  candidate_count: number
}

interface MatchResult {
  match_id: string
  candidates: Array<{ user_id: string; nickname: string; score: number; reason: string }>
  match_letters: string[]
}

export default function MatchCenter() {
  const navigate = useNavigate()
  const { token } = useAuth()
  const { events, status: sseStatus, connect, disconnect } = useSSE()

  const [pageStatus, setPageStatus] = useState<PageStatus>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [hitlData, setHitlData] = useState<HitlData | null>(null)
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [isResuming, setIsResuming] = useState(false)
  const stepListRef = useRef<HTMLDivElement>(null)

  // 监听 SSE 事件，更新页面状态
  useEffect(() => {
    if (events.length === 0) return
    const latest = events[events.length - 1]

    if (latest.event === 'hitl_preview') {
      setPageStatus('waiting_hitl')
      setHitlData({
        candidates: latest.candidates ?? [],
        retrieval_note: latest.retrieval_note ?? '',
        candidate_count: latest.candidate_count ?? 0,
      })
    } else if (latest.event === 'complete') {
      setPageStatus('done')
      // 从 session result 中获取完整结果（通过 match_id 可以访问历史）
    } else if (latest.event === 'error') {
      setPageStatus('error')
      setErrorMsg(latest.msg ?? '匹配失败')
    }
  }, [events])

  // 自动滚动步骤列表到底部
  useEffect(() => {
    if (stepListRef.current) {
      stepListRef.current.scrollTop = stepListRef.current.scrollHeight
    }
  }, [events])

  const handleStart = async () => {
    if (!token) { navigate('/login'); return }
    try {
      setPageStatus('running')
      setHitlData(null)
      setMatchResult(null)
      setErrorMsg('')

      const res = await startMatch()
      const newSessionId = res.data.session_id
      setSessionId(newSessionId)

      // 订阅 SSE 流
      connect(newSessionId, token)
    } catch {
      setPageStatus('error')
      setErrorMsg('启动匹配失败，请稍后重试')
    }
  }

  const handleResume = async () => {
    if (!sessionId) return
    setIsResuming(true)
    try {
      await resumeMatch(sessionId, 'proceed')
      setPageStatus('running')
      setHitlData(null)
    } catch {
      setErrorMsg('确认操作失败')
    } finally {
      setIsResuming(false)
    }
  }

  const handleReset = () => {
    disconnect()
    setPageStatus('idle')
    setSessionId(null)
    setHitlData(null)
    setMatchResult(null)
    setErrorMsg('')
  }

  const completeEvent = events.find((e) => e.event === 'complete')

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-4 py-8">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* 页面标题 */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/20 border border-indigo-400/30">
            <Sparkles size={14} className="text-indigo-300" />
            <span className="text-indigo-200 text-sm">AI 智能匹配</span>
          </div>
          <h1 className="text-2xl font-bold text-white">寻找你的缘分</h1>
          <p className="text-white/50 text-sm">
            基于 LangGraph 多 Agent 系统，为你精准匹配
          </p>
        </div>

        {/* 主卡片 */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 space-y-5">

          {/* Idle 状态：启动按钮 */}
          <AnimatePresence mode="wait">
            {pageStatus === 'idle' && (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-4 py-8"
              >
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <Sparkles size={36} className="text-white" />
                </div>
                <div className="text-center">
                  <p className="text-white/80">AI 将分析你的偏好，</p>
                  <p className="text-white/80">智能筛选最适合你的缘分候选人</p>
                </div>
                <button
                  onClick={handleStart}
                  className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-semibold shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 transition-all active:scale-95"
                >
                  <Play size={18} />
                  开始匹配
                </button>
              </motion.div>
            )}

            {/* Running 状态：Agent 步骤流 */}
            {(pageStatus === 'running') && (
              <motion.div
                key="running"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
                  <span className="text-white/70 text-sm">
                    {sseStatus === 'connecting' ? '正在连接...' : 'AI 正在为你寻找缘分...'}
                  </span>
                </div>
                <div
                  ref={stepListRef}
                  className="max-h-72 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10"
                >
                  <AgentStepList events={events} />
                </div>
              </motion.div>
            )}

            {/* HITL 状态：候选人预览 */}
            {pageStatus === 'waiting_hitl' && hitlData && (
              <motion.div
                key="hitl"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                {/* 步骤摘要（折叠显示） */}
                <details className="group">
                  <summary className="text-white/40 text-xs cursor-pointer list-none flex items-center gap-1">
                    <ChevronRight size={12} className="group-open:rotate-90 transition-transform" />
                    查看 AI 分析过程
                  </summary>
                  <div className="mt-2 max-h-48 overflow-y-auto">
                    <AgentStepList events={events.filter(e => e.event !== 'hitl_preview')} />
                  </div>
                </details>

                {/* HITL 提示 */}
                <div className="bg-indigo-500/10 border border-indigo-400/30 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Users size={16} className="text-indigo-300" />
                    <span className="text-indigo-200 font-medium text-sm">
                      找到 {hitlData.candidate_count} 位候选人
                    </span>
                  </div>
                  {hitlData.retrieval_note && (
                    <p className="text-white/50 text-xs">{hitlData.retrieval_note}</p>
                  )}

                  {/* 候选人头像预览 */}
                  <div className="flex gap-2 flex-wrap">
                    {hitlData.candidates?.slice(0, 6).map((c, i) => (
                      <motion.div
                        key={c.user_id}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.07 }}
                        className="flex flex-col items-center gap-1"
                      >
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-400 to-purple-400 flex items-center justify-center text-white font-bold text-sm shadow">
                          {c.nickname?.charAt(0) ?? '?'}
                        </div>
                        <span className="text-white/50 text-xs">{c.nickname}</span>
                        <span className="text-white/30 text-xs">{c.age}岁</span>
                      </motion.div>
                    ))}
                  </div>

                  <p className="text-white/60 text-sm">
                    AI 将对以上候选人进行深度分析，生成匹配报告。
                    准备好了吗？
                  </p>
                </div>

                <button
                  onClick={handleResume}
                  disabled={isResuming}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-semibold disabled:opacity-60 transition-all active:scale-95"
                >
                  {isResuming ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      确认中...
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      开始深度分析
                    </>
                  )}
                </button>
              </motion.div>
            )}

            {/* Done 状态：结果 */}
            {pageStatus === 'done' && (
              <motion.div
                key="done"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 text-emerald-400">
                  <span className="text-xl">✨</span>
                  <span className="font-semibold">
                    匹配完成！找到 {completeEvent?.result_count ?? 0} 位缘分候选人
                  </span>
                </div>

                {/* 步骤摘要 */}
                <details className="group">
                  <summary className="text-white/40 text-xs cursor-pointer list-none flex items-center gap-1">
                    <ChevronRight size={12} className="group-open:rotate-90 transition-transform" />
                    查看完整 AI 分析过程
                  </summary>
                  <div className="mt-2 max-h-64 overflow-y-auto">
                    <AgentStepList events={events} />
                  </div>
                </details>

                {completeEvent?.match_id && (
                  <button
                    onClick={() => navigate(`/history`)}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold transition-all active:scale-95"
                  >
                    查看匹配结果
                    <ChevronRight size={16} />
                  </button>
                )}

                <button
                  onClick={handleReset}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-white/20 text-white/60 text-sm transition-all hover:bg-white/5"
                >
                  <RotateCcw size={14} />
                  再次匹配
                </button>
              </motion.div>
            )}

            {/* Error 状态 */}
            {pageStatus === 'error' && (
              <motion.div
                key="error"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-4 text-center py-6"
              >
                <p className="text-red-400">❌ {errorMsg}</p>
                <button
                  onClick={handleReset}
                  className="flex items-center justify-center gap-2 mx-auto px-6 py-2.5 rounded-xl border border-white/20 text-white/60 text-sm"
                >
                  <RotateCcw size={14} />
                  重试
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* 说明卡片 */}
        {pageStatus === 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-3"
          >
            <p className="text-white/50 text-xs font-medium uppercase tracking-wider">
              AI 匹配流程
            </p>
            {[
              { emoji: '🔍', label: '意图解析', desc: 'AI 分析你的偏好，调用工具获取历史记录和黑名单' },
              { emoji: '📋', label: '智能检索', desc: '向量数据库自动放宽条件，最多3轮确保找到合适候选人' },
              { emoji: '👀', label: '预览确认', desc: '你可以查看候选人名单后，再决定是否深度分析' },
              { emoji: '🧠', label: '深度分析', desc: 'LLM 全面评估匹配维度，生成个性化推荐报告' },
            ].map(({ emoji, label, desc }) => (
              <div key={label} className="flex gap-3">
                <span className="text-base">{emoji}</span>
                <div>
                  <span className="text-white/70 text-sm font-medium">{label}</span>
                  <p className="text-white/40 text-xs">{desc}</p>
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}
```

### Step 2：更新 `App.tsx`

- [ ] 在现有 import 后添加：

```tsx
import MatchCenter from './pages/MatchCenter'
```

在路由中添加（`/fate` 路由附近）：

```tsx
<Route path="/match" element={<ProtectedRoute requireProfileComplete><MatchCenter /></ProtectedRoute>} />
```

### Step 3：更新 `BottomNav.tsx`

- [ ] 把原来的"心动"（指向 `/fate`）改回两个独立入口：

找到当前 BottomNav 中「匹配」相关的导航项，恢复指向 `/match`（同时保留 `/fate`）。

当前如果是这样：
```tsx
<NavLink to="/fate" ...>心动</NavLink>
```

修改为（底部导航保留 5 项）：
```tsx
<NavLink to="/fate" className="flex-1">
  {({ isActive }) => (<NavItem icon={<Heart size={22} />} label="心动" isActive={isActive} />)}
</NavLink>
<NavLink to="/match" className="flex-1">
  {({ isActive }) => (<NavItem icon={<Sparkles size={22} />} label="匹配" isActive={isActive} />)}
</NavLink>
```

（如果底部导航已经是5项，替换其中一项为 `/match`。具体调整根据实际布局决定）

### Step 4：更新 `Navbar.tsx`

- [ ] 在 `AUTH_LINKS` 数组中添加匹配链接：

```tsx
{ to: '/match', label: '匹配', icon: Sparkles },
```

- [ ] **Step 5：验证前端完整构建**

```bash
cd frontend
npm run build 2>&1 | tail -30
```

预期：0 TypeScript 错误，0 build errors。

- [ ] **Step 6：提交**

```bash
git add frontend/src/pages/MatchCenter.tsx \
        frontend/src/App.tsx \
        frontend/src/components/BottomNav.tsx \
        frontend/src/components/Navbar.tsx
git commit -m "feat: add MatchCenter page with SSE progress + HITL confirm flow"
```

---

## Task 9：联调验证

**Files:** 无新增文件，验证整体流程

- [ ] **Step 1：确认后端可以启动**

```bash
cd backend
python run.py
```

预期：无报错，看到：
```
[Phase 4] AsyncSqliteSaver initialized
[Phase 2] Using Supervisor multi-agent graph
Graph nodes: [..., hitl_node, ...]
Uvicorn running on http://0.0.0.0:8000
```

- [ ] **Step 2：确认前端可以启动**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3：访问 `/match` 页面，验证页面渲染正常**

打开 `http://localhost:5173/match`，确认：
- 页面有"开始匹配"按钮
- AI 匹配流程说明卡片正确展示

- [ ] **Step 4：完整 E2E 流程验证（需登录账号）**

1. 登录账号（确保 `profile_complete=true`）
2. 访问 `/match`，点击"开始匹配"
3. 观察 AgentStepList 实时出现步骤
4. 等待 HITL 候选人预览卡片出现
5. 点击"开始深度分析"
6. 等待分析完成，看到完成提示

- [ ] **Step 5：最终提交**

```bash
git add -A
git commit -m "feat: phase3c complete - Tool Calling + Agentic RAG + HITL + SSE matching"
```

---

## 自检清单（Spec 覆盖率）

| Spec 要求 | 对应 Task | 状态 |
|-----------|-----------|------|
| Tool Calling：intent_agent 装备3个工具 | Task 1+2 | ✅ |
| Agentic RAG：retrieval_agent 3轮自适应 | Task 3 | ✅ |
| HITL：interrupt() + Command(resume=) | Task 4 | ✅ |
| SSE 流：astream_events 推送给前端 | Task 6 | ✅ |
| 后端 API：start/stream/resume/result | Task 6 | ✅ |
| 前端 useSSE Hook | Task 7 | ✅ |
| 前端 AgentStepList 步骤动画 | Task 7 | ✅ |
| 前端 MatchCenter 页面（状态机） | Task 8 | ✅ |
| 工具调用可视化（ToolCallBadge）| Task 7 | ✅（AgentStepList 中） |
| retrieval_note 展示 | Task 8 | ✅ |
| /match 路由 + BottomNav | Task 8 | ✅ |
