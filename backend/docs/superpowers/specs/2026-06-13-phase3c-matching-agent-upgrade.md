# Phase 3c：匹配 Agent 全面升级设计文档

> **所属项目**：心犀AI v3.0
> **设计日期**：2026-06-13
> **状态**：用户已批准，进入规划阶段
> **方案**：渐进式升级（方案 A）——保留 Supervisor 图结构，逐层注入新能力

---

## 一、目标与范围

本阶段目标：在不重写现有架构的前提下，将匹配主流程升级为具备以下能力的 Agent 系统：

| 技术 | 实现位置 | 学习要点 |
|------|---------|---------|
| **Tool Calling** | `intent_agent` | `bind_tools()`、`ToolNode`、ReAct 循环 |
| **Agentic RAG** | `retrieval_agent` | 自适应多轮检索、条件自动放宽 |
| **HITL 中断点** | `supervisor/graph.py` 新增节点 | `interrupt()`、Checkpointer、`Command(resume=...)` |
| **SSE 流式推送** | `api/routers/matching.py` | `astream_events()`、`StreamingResponse` |
| **MatchCenter 前端** | `frontend/src/pages/MatchCenter.tsx` | `useSSE` Hook、实时步骤流、HITL 交互 |

---

## 二、整体通信协议

```
前端                          后端 (FastAPI)            LangGraph
  │                                │                         │
  │ POST /api/match/start          │                         │
  │ ──────────────────────────→   │  创建 session_id        │
  │ ←── { session_id }            │  启动 graph (background)│
  │                                │                         │
  │ GET /api/match/{id}/stream     │                         │
  │ ──────────────────────────→   │  SSE 连接               │
  │ ← event: agent_start          │  ←── astream_events()   │
  │ ← event: tool_call            │                         │
  │ ← event: agent_complete       │                         │
  │ ← event: hitl_preview ──────────────── interrupt() ─── │
  │                                │                         │  ⏸ 暂停
  │ POST /api/match/{id}/resume    │                         │
  │ ──────────────────────────→   │  Command(resume=...)    │
  │ ← event: agent_start          │  ─────────────────────→ │  ▶ 恢复
  │ ← event: complete             │                         │
```

**关键设计决策**：使用 SSE（Server-Sent Events）做服务器到客户端的进度推流，使用独立的 `POST /resume` 端点做客户端到服务器的 HITL 决策回传。这比纯 WebSocket 在实现和错误处理上更简洁，适合单向流式 + 偶发交互的场景。

---

## 三、后端改造

### 3.1 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/match/start` | 创建匹配会话，返回 `{ session_id }`，后台启动 graph |
| `GET` | `/api/match/{session_id}/stream` | SSE 流（`Content-Type: text/event-stream`） |
| `POST` | `/api/match/{session_id}/resume` | HITL 恢复决策，body: `{ "action": "proceed" \| "adjust" }` |
| `GET` | `/api/match/{session_id}/result` | 获取完整匹配结果 |

### 3.2 SSE 事件格式

所有事件均为 `data: <JSON>\n\n` 格式。

```jsonc
// Agent 节点开始
{ "event": "agent_start",    "node": "intent_agent",    "msg": "正在解析你的偏好..." }

// 工具调用（Tool Calling 可视化）
{ "event": "tool_call",      "node": "intent_agent",    "tool": "get_my_profile",      "status": "calling" }
{ "event": "tool_result",    "node": "intent_agent",    "tool": "get_my_profile",      "status": "done" }

// Agent 节点完成
{ "event": "agent_complete", "node": "intent_agent",    "msg": "已锁定 5 个筛选条件" }
{ "event": "agent_complete", "node": "retrieval_agent", "msg": "检索到 8 位候选人（第2轮，已放宽年龄）" }

// HITL 中断——前端渲染预览卡片并等待用户操作
{
  "event": "hitl_preview",
  "candidates": [{ "id": "...", "nickname": "...", "age": 28, "avatar_url": "..." }],
  "retrieval_note": "已自动放宽年龄范围 ±5 岁"
}

// 深度分析阶段
{ "event": "agent_start",    "node": "analysis_agent", "msg": "深度分析匹配维度..." }
{ "event": "agent_start",    "node": "letter_agent",   "msg": "生成个性化推荐词..." }

// 完成
{ "event": "complete", "match_id": "M001", "result_count": 5 }

// 错误
{ "event": "error", "msg": "..." }
```

### 3.3 Checkpointer 配置

使用项目现有的 `checkpoints.db`（SQLite）作为 LangGraph Checkpointer，`thread_id = session_id`。HITL 中断时状态自动持久化，`resume` 端点调用 `Command(resume={"action": "proceed"})` 恢复执行。

---

## 四、Agent 层改造

### 4.1 Tool Calling：intent_agent 改造

#### 新建 `core/agents/intent/tools.py`

三个工具，配合 `@tool` 装饰器，每个工具附带详细 docstring（LLM 靠 docstring 决定是否调用）：

```python
@tool
def get_my_profile(user_id: str) -> dict:
    """获取当前用户完整资料和择偶偏好。
    当需要了解用户自身条件或默认偏好时调用。"""
    # 从 PostgreSQL users 表异步查询

@tool
def get_blacklist(user_id: str) -> list[str]:
    """获取用户的黑名单用户ID列表。
    在生成检索条件时调用，确保排除黑名单用户。"""
    # 查询 block_list 表

@tool
def get_match_history_ids(user_id: str, limit: int = 50) -> list[str]:
    """获取历史已推荐过的用户ID列表，避免重复推荐。
    在检索前调用。"""
    # 查询 match_results 表取最近 limit 条
```

#### 改造 `core/agents/intent/agent.py`

```
原来（单次调用）：prompt → LLM → 结构化输出

改造后（ReAct 循环）：
  1. llm.bind_tools([get_my_profile, get_blacklist, get_match_history_ids])
  2. LLM 决定是否调用工具
  3. ToolNode 自动执行工具，结果追加到消息链
  4. 再次调用 LLM → 最终 IntentParseResult
  （最多 3 轮工具循环，由 while tool_calls 循环控制）
```

`intent_agent` 内部变为一个**小子图**结构：`call_llm → (有工具调用?) → execute_tools → call_llm → 结束`

### 4.2 Agentic RAG：retrieval_agent 改造

内置3轮自适应检索循环，不再依赖 `reflection_agent` 外部触发重试：

```
第 1 轮：按原始 hard_filters 检索
  候选 ≥ 3？
    ✓ → 返回，进入 HITL 节点
    ✗ → 记录失败原因，触发第 2 轮

第 2 轮：年龄范围 ±5 岁放宽
  候选 ≥ 3？
    ✓ → 返回，附 retrieval_note = "已自动放宽年龄范围 ±5 岁"
    ✗ → 触发第 3 轮

第 3 轮：忽略城市限制，全国范围检索
  直接返回，附 retrieval_note = "已大范围放宽搜索条件"
```

State 新增字段：
- `retrieval_rounds: int`：实际执行轮次
- `retrieval_note: str`：给用户看的放宽说明

`reflection_agent` 角色调整：从"触发重试决策者"变为"最终结果质量评估者"（评估是否要进入推荐信生成阶段）。

### 4.3 HITL 节点：supervisor/graph.py

在 `retrieval_agent` 和 `analysis_agent` 之间插入 `hitl_node`：

```python
from langgraph.types import interrupt

def hitl_node(state: SupervisorState) -> dict:
    """
    HITL 中断节点：暂停流程，等待用户确认候选人预览。
    
    学习要点：
    - interrupt() 向外暴露数据并暂停执行（抛出 GraphInterrupt）
    - LangGraph Checkpointer 自动保存当前完整 State 到 SQLite
    - 外部通过 Command(resume=value) 恢复，value 会成为 interrupt() 的返回值
    - 这是 HITL 的核心机制：让 Agent 在关键节点等待人类决策
    """
    preview = build_candidate_preview(state["candidates"])
    
    # 中断，向 SSE 流暴露预览数据
    user_decision = interrupt({
        "type": "hitl_preview",
        "candidates": preview,
        "retrieval_note": state.get("retrieval_note", "")
    })
    
    # 恢复后继续执行
    return {
        "hitl_decision": user_decision,
        "next_agent": "analysis"
    }
```

图结构变化：
```
旧：intent → retrieval → analysis → reflection → letter → judge
新：intent → retrieval → hitl_node → analysis → reflection → letter → judge
                               ↑ interrupt()
```

---

## 五、前端改造

### 5.1 新增文件

| 文件 | 说明 |
|------|------|
| `src/pages/MatchCenter.tsx` | 匹配中心页（路由 `/match`） |
| `src/hooks/useSSE.ts` | SSE 订阅 Hook |
| `src/components/AgentStepList.tsx` | Agent 步骤动画列表 |

### 5.2 MatchCenter 页面状态机

```
idle
  ↓ 点击"开始匹配"
loading（启动中）
  ↓ SSE 连接建立
running（进行中）  ←→ AgentStepList 步骤逐条淡入
  ↓ 收到 hitl_preview
hitl（等待确认）   ←→ 候选预览卡片 + "开始深度分析" / "调整条件" 按钮
  ↓ 点击"开始深度分析"
running（继续）
  ↓ 收到 complete
done（展示结果）
```

### 5.3 useSSE Hook 接口

```typescript
interface SSEEvent {
  event: string       // "agent_start" | "tool_call" | "hitl_preview" | "complete" | "error"
  node?: string
  msg?: string
  tool?: string
  status?: string
  candidates?: CandidatePreview[]
  retrieval_note?: string
  match_id?: string
  result_count?: number
}

const { events, status, connect, disconnect } = useSSE(sessionId?: string)
// status: 'idle' | 'connecting' | 'open' | 'error' | 'closed'
// events: SSEEvent[]  累积所有到达的事件
```

### 5.4 AgentStepList 组件

- 每条步骤：节点图标 + 文字 + 状态徽章（running spinner / done checkmark）
- `tool_call` 事件：在对应步骤下挂一个小徽章，显示正在调用的工具名
- 所有步骤用 `framer-motion` stagger 100ms 逐条淡入

### 5.5 App.tsx 路由更新

```tsx
<Route path="/match" element={<ProtectedRoute requireProfileComplete><MatchCenter /></ProtectedRoute>} />
```

Navbar 和 BottomNav 的"心动"入口维持 `/fate`，"匹配"入口改回 `/match`（当前 BottomNav 已将匹配改为了 `/fate`，需要恢复并区分两个入口）。

---

## 六、数据库变更

### 新增 `match_sessions` 表

```sql
CREATE TABLE match_sessions (
    id          VARCHAR(36) PRIMARY KEY,   -- UUID, 同 LangGraph thread_id
    user_id     VARCHAR(36) NOT NULL,
    status      VARCHAR(20) DEFAULT 'running',  -- running | waiting_hitl | done | error
    params      JSONB,                      -- 用户临时调整的筛选参数
    result_id   VARCHAR(36),               -- 完成后指向 match_results 记录
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

（通过 Alembic 迁移，编号 003）

---

## 七、改造文件清单

### 后端

| 文件 | 类型 | 改动说明 |
|------|------|---------|
| `core/agents/intent/tools.py` | 新建 | 3个工具函数 |
| `core/agents/intent/agent.py` | 改造 | bind_tools + ReAct 子图 |
| `core/agents/retrieval/agent.py` | 改造 | 内置3轮重试循环 |
| `core/agents/supervisor/graph.py` | 改造 | 插入 hitl_node，配置 interrupt |
| `core/agents/supervisor/state.py` | 改造 | 新增 hitl_* / retrieval_* 字段 |
| `api/routers/matching.py` | 改造 | 新增 start/stream/resume/result 端点 |
| `api/schemas.py` | 改造 | 新增 MatchSessionCreate、MatchResumeRequest |
| `core/database/models.py` | 改造 | 新增 MatchSession 模型 |
| `alembic/versions/003_*.py` | 新建 | match_sessions 表迁移 |

### 前端

| 文件 | 类型 | 改动说明 |
|------|------|---------|
| `src/pages/MatchCenter.tsx` | 新建 | 匹配中心页 |
| `src/hooks/useSSE.ts` | 新建 | SSE Hook |
| `src/components/AgentStepList.tsx` | 新建 | 步骤动画列表 |
| `src/api/client.ts` | 改造 | 新增匹配会话 API 函数 |
| `src/types/index.ts` | 改造 | 新增 SSEEvent、MatchSession 类型 |
| `src/App.tsx` | 改造 | 添加 /match 路由 |
| `src/components/BottomNav.tsx` | 改造 | 恢复"匹配"入口至 /match |
| `src/components/Navbar.tsx` | 改造 | 同步"匹配"链接 |

---

## 八、实现顺序建议

1. Alembic 迁移（match_sessions 表）
2. `intent/tools.py` + `intent/agent.py` 改造（Tool Calling）
3. `retrieval/agent.py` 改造（Agentic RAG）
4. `supervisor/state.py` + `supervisor/graph.py` 改造（HITL 节点）
5. `api/routers/matching.py` 改造（SSE + resume 端点）
6. 前端 `useSSE.ts` + `AgentStepList.tsx`
7. 前端 `MatchCenter.tsx`
8. 路由 + 导航收尾

---

## 九、验收标准

- [ ] 启动匹配后，前端 AgentStepList 实时显示各 Agent 节点执行状态
- [ ] Tool Calling 可视化：可以看到 `get_my_profile` 等工具调用徽章
- [ ] 检索候选人不足时，自动放宽条件，前端显示 `retrieval_note`
- [ ] 检索完成后前端显示候选人预览卡片，并停留在 HITL 等待状态
- [ ] 点击"开始深度分析"后，流程恢复并完成
- [ ] 最终匹配结果正确展示
