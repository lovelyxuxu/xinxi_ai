# 心犀AI v3.0 全量设计文档

> **项目定位**：基于 LangChain + LangGraph 的智能婚恋匹配系统（学习项目）
> **设计方案**：方案 C —— 三层平行推进（UI 全面现代化 + 功能完整迭代 + Agent 新技术有机融入）
> **设计日期**：2026-06-13
> **状态**：用户已审批，准备进入实施阶段

---

## 一、整体架构

### 三层职责分离

```
┌─────────────────────────────────────────────────────────┐
│  🎨 表现层  frontend/src/                               │
│  · 设计系统（颜色/字体/动效）统一管理                   │
│  · 每个页面只关心"怎么展示"                             │
│  · 通过 API Client 调用后端，不直接碰业务逻辑           │
├─────────────────────────────────────────────────────────┤
│  🔧 功能层  backend/api/                                │
│  · FastAPI 路由 + 鉴权 + 数据 CRUD                     │
│  · 每个 router 只关心"接口契约"                         │
│  · 调用 Agent 层时，只传入参数、拿回结果                │
├─────────────────────────────────────────────────────────┤
│  🤖 Agent 层  backend/core/agents/                      │
│  · LangGraph 图 + 各 Agent 节点（保留详细学习注释）     │
│  · 每个新技术隔离在独立模块                             │
│  · 通过 AgentState 与功能层交互                         │
└─────────────────────────────────────────────────────────┘
```

### 层间接口约定

| 接口 | 方向 | 形式 |
|---|---|---|
| 前端 → 后端 | REST + WebSocket + SSE | JSON / JWT Bearer |
| 后端 → Agent | Python 函数调用 | `AgentState` TypedDict |
| Agent → DB | SQLAlchemy async session（通过 Tool） | ORM 模型 |
| Agent → 前端（实时） | Server-Sent Events（SSE） | `StreamingResponse` |

### 新增技术依赖

| 层 | 新增依赖 | 用途 |
|---|---|---|
| 前端 | `framer-motion` | 卡片动效、页面切换动画 |
| 前端 | `zustand` | 全局状态（匹配进度、消息未读数） |
| 前端 | `lucide-react`（已内置 shadcn） | 替换所有 emoji 图标 |
| 前端 | `browser-image-compression` | 上传前压缩图片 |
| 后端 | `python-multipart`（已有） | 图片上传 |
| Agent | LangGraph `interrupt()` | HITL 中断点 |
| Agent | LangChain `@tool` 装饰器 | Tool Calling |

---

## 二、UI 设计系统

### 设计语言

Mobile First + 暗色渐变 + 磨砂玻璃 + 小红书/Soul 风格。
技术栈不变（shadcn/ui + Tailwind），重做主题层（CSS 变量 + Tailwind 扩展）。

### 色彩系统

| 变量 | 值 | 用途 |
|---|---|---|
| `--bg-primary` | `#0a0a0f` | 主背景（深空黑） |
| `--bg-card` | `rgba(255,255,255,0.04)` | 卡片背景（磨砂玻璃） |
| `--color-primary` | `#e91e8c` → `#9c27b0` | 主色调渐变（玫红 → 紫） |
| `--color-accent` | `#ff6b9d` | 强调色（亮粉） |
| `--text-primary` | `#f0f0f5` | 主文字 |
| `--text-muted` | `#8b8b9e` | 辅助文字 |
| `--border` | `rgba(255,255,255,0.08)` | 分隔线 |

### 动效规范（framer-motion）

| 场景 | 动效 | 时长 |
|---|---|---|
| 页面切换 | 淡入 + 向上 8px | 200ms ease-out |
| 卡片悬浮 | scale(1.02) + shadow 加深 | 150ms |
| Agent 步骤逐条出现 | stagger 100ms/条淡入 | — |
| 匹配结果卡片 | 逐卡从下滑入 | stagger 80ms/卡 |

### 图标系统

全部使用 `lucide-react`，禁止 emoji 作为功能性图标。

| 场景 | 图标 |
|---|---|
| 导航-发现 | `<Compass />` |
| 导航-匹配 | `<Heart />` |
| 导航-AI访谈 | `<Sparkles />` |
| 导航-消息 | `<MessageCircle />` |
| 导航-我的 | `<User />` |
| 操作-关注 | `<UserPlus />` |
| 操作-私信 | `<Send />` |
| 操作-上传 | `<Upload />` |
| 操作-编辑 | `<Pencil />` |
| 操作-设置 | `<Settings />` |

### 移动端布局

- **底部导航栏**（手机专属，桌面隐藏）：`[发现] [匹配] [＋AI访谈凸起] [消息] [我的]`
- **首页**：双列瀑布流卡片（手机 2 列，平板 3 列，桌面 4 列）
- **断点**：`sm:640px` / `md:768px` / `lg:1024px`

### 页面清单

| 状态 | 路径 | 页面 | 说明 |
|---|---|---|---|
| 改造 | `/` | `Home` | 发现页：双列瀑布流 |
| 改造 | — | `Navbar` | 桌面导航，已登录态完善 |
| 新增 | — | `BottomNav` | 移动端底部导航 |
| 改造 | `/login` | `Login` | 暗色主题适配 |
| 改造 | `/register` | `Register` | 暗色主题适配 |
| 新增 | `/profile` | `MyProfile` | 个人中心 |
| 新增 | `/profile/edit` | `EditProfile` | 编辑资料 |
| 新增 | `/match` | `MatchCenter` | 匹配中心（含 Agent 进度流） |
| 新增 | `/history` | `MyHistory` | 我的匹配历史 |
| 新增 | `/social` | `Social` | 关注/粉丝 |
| 新增 | `/chat` | `ChatList` | 消息列表 |
| 新增 | `/chat/:convId` | `ChatRoom` | 聊天室 + AI 破冰 |
| 新增 | `/settings` | `Settings` | 设置 |

---

## 三、功能层 Phase 路线图

### Phase 2：用户中心 + UI 全面升级（当前阶段）

**后端新增接口**

| 方法 | 路径 | 说明 |
|---|---|---|
| PUT | `/api/auth/me` | 编辑个人资料（基本信息 + 择偶偏好） |
| PUT | `/api/auth/password` | 修改密码 |
| POST | `/api/auth/me/avatar` | 上传头像（multipart） |
| POST | `/api/auth/me/photos` | 上传照片（最多 6 张） |
| DELETE | `/api/auth/me/photos/{index}` | 删除指定照片 |
| GET | `/api/users` | 用户发现列表（分页 + 性别/城市筛选） |
| GET | `/api/users/{user_id}` | 用户公开主页 |

**数据库变更**

- `users` 表新增 `photos JSONB DEFAULT '[]'` 字段（Alembic 迁移 002）

**ChromaDB 同步**

- 编辑资料保存后，通过 FastAPI `BackgroundTask` 异步更新向量（不阻塞响应）

**静态文件**

- `backend/uploads/avatars/` 和 `backend/uploads/photos/` 目录
- FastAPI `StaticFiles` 挂载到 `/uploads`

### Phase 3：匹配增强（下一阶段）

- WebSocket 接收 `user_filters` 参数
- Agent 升级：Tool Calling + Agentic RAG + HITL 中断点
- 匹配记录迁移到 PostgreSQL
- SSE 流式推送 Agent 执行状态
- `MatchCenter` 前端页面（参数面板 + Agent 进度可视化 + HITL 交互）
- `MyHistory` 页面（仅自己可见）

### Phase 4：社交 + AI 访谈增强

- 关注/取关 API + 前端
- 私信系统（会话 + 消息 + WebSocket）
- AI 访谈增强：`recommend_agent`（对话中实时推荐用户 + 引导功能）
- Memory Agent：跨会话偏好记忆（preference_evolution 表）
- `ChatList` + `ChatRoom`（含 AI 破冰助手）
- `Social` 页面

### Phase 5：体验优化 + MCP

- 设置页面（修改密码 + 黑名单管理）
- MCP Server：将匹配工具标准化为 MCP 工具接口
- Agent Dashboard（LangFuse 链接或内嵌简版）

---

## 四、Agent 层技术映射

### 现有架构（保留）

```
Supervisor → intent_agent → retrieval_agent → analysis_agent
         → reflection_agent → letter_agent → judge_agent
```

所有节点保留并扩展详细学习注释。

### Phase 3 新增：Tool Calling

改造 `intent_agent`，装备 3 个工具（LangChain `@tool`）：

```python
@tool
def get_my_profile(user_id: str) -> dict:
    """获取当前用户完整资料和择偶偏好。
    当需要了解用户自身条件或默认偏好时调用。"""

@tool
def get_blacklist(user_id: str) -> list[str]:
    """获取用户的黑名单用户ID列表。
    在生成检索条件时调用，确保排除黑名单用户。"""

@tool
def get_match_history_ids(user_id: str, limit: int = 50) -> list[str]:
    """获取历史已推荐过的用户ID列表。
    避免重复推荐，在检索前调用。"""
```

### Phase 3 新增：Agentic RAG

改造 `retrieval_agent`，支持最多 3 轮自动重试：

```
第1轮: 按原始 hard_filters 检索
  候选数 >= 3 且质量达标 → 返回
  候选不足 → 放宽年龄范围 ±5 岁，进入第2轮
第2轮: 放宽条件检索
  候选数 >= 3 → 返回
  仍然不足 → 扩大地域到省份，进入第3轮
第3轮: 最宽松条件
  返回最终结果，附注"已放宽搜索条件"
```

### Phase 3 新增：HITL 中断点

在 `retrieval_agent` 完成后插入 LangGraph `interrupt()`：

```
retrieval_agent 完成
→ SSE 推送候选预览 {"type": "hitl_preview", "candidates": [...]}
→ 前端展示预览卡片 + "开始深度分析" + "调整条件" 按钮
→ 用户操作 → WebSocket 发送 {"type": "resume", "exclude_ids": [...]}
→ LangGraph Command(resume=value) 恢复执行
→ analysis_agent → letter_agent → judge_agent
```

### Phase 3 新增：Streaming SSE

所有节点通过 LangGraph `astream_events()` 推送执行状态：

```python
{"event": "agent_start",    "node": "intent_agent",    "msg": "正在解析你的偏好..."}
{"event": "tool_call",      "node": "intent_agent",    "tool": "get_my_profile"}
{"event": "agent_complete", "node": "intent_agent",    "msg": "已锁定 5 个筛选条件"}
{"event": "agent_start",    "node": "retrieval_agent", "msg": "向量数据库检索中..."}
{"event": "hitl_preview",   "node": "retrieval_agent", "candidates": [...]}
{"event": "agent_start",    "node": "analysis_agent",  "msg": "深度分析匹配维度..."}
{"event": "complete",       "match_id": "M001",        "results": [...]}
```

### Phase 4 新增：Memory Agent

```python
# 每次匹配结束后静默运行
memory_agent:
  1. 读取匹配结果（得分分布、用户是否 liked 某候选人）
  2. 更新 preference_evolution 表（JSONB 偏好记录）
  3. 下次匹配时 intent_agent 通过 get_preference_memory 工具读取
```

### Phase 4 新增：访谈实时推荐（recommend_agent）

```
每轮对话后:
  recommend_agent 分析对话内容
  ├── 检测意图信号: "我喜欢爱运动的"
  │   → 查 ChromaDB → 推送用户卡片到前端
  └── 检测功能引导信号: "我想改资料"
      → 推送 {"type": "feature_hint", "action": "go_edit_profile"}
```

### Phase 4 新增：Tool 工具集完整清单

**匹配 Agent 工具集（Phase 3）**

| 工具 | 所属 Agent | 说明 |
|---|---|---|
| `get_my_profile` | intent_agent | 获取自身资料 + 择偶偏好 |
| `get_blacklist` | intent_agent | 获取黑名单 |
| `get_match_history_ids` | intent_agent | 获取历史推荐 ID |
| `search_candidates` | retrieval_agent | ChromaDB 向量检索（封装现有逻辑） |
| `get_preference_memory` | intent_agent | 读取长期偏好记忆（Phase 4） |

**访谈 Agent 工具集（Phase 4）**

| 工具 | 说明 |
|---|---|
| `recommend_users_inline` | 对话中实时推荐用户 |
| `hint_feature` | 引导用户去某功能页 |
| `query_user_count_by_filter` | 告知"符合条件的有 XX 人" |
| `save_interview_preference` | 把偏好存入记忆 |

---

## 五、媒体与存储

### 图片存储

- 存储位置：`backend/uploads/avatars/` 和 `backend/uploads/photos/`
- 访问 URL：`http://localhost:8000/uploads/avatars/{user_id}.jpg`
- 前端压缩：`browser-image-compression`，上传前压缩到 ≤800px、≤500KB
- 格式：统一转为 JPEG（节省存储）
- 头像：1 张，覆盖式更新（文件名 = `{user_id}.jpg`）
- 照片：最多 6 张，存 URL 数组到 `users.photos JSONB`

### 视频（暂不支持）

Phase 5 可考虑支持短视频，当前阶段不实现。

---

## 六、完整文件变更预览

### 后端新增/改造

```
backend/
├── alembic/versions/
│   └── 002_add_photos_field.py          【新增】添加 photos 字段迁移
├── api/
│   ├── routers/
│   │   ├── auth.py                       【改造】新增编辑、头像、照片接口
│   │   ├── users.py                      【改造】发现列表 + 用户详情
│   │   ├── matching.py                   【改造 Phase3】WebSocket + SSE
│   │   └── social.py                     【新增 Phase4】关注 + 私信
│   └── schemas.py                        【改造】新增 UserUpdate、PhotoUpload
├── core/
│   ├── database/models.py                【改造】新增 photos 字段
│   ├── tasks/
│   │   └── chroma_sync.py               【新增】ChromaDB 异步同步任务
│   └── agents/
│       ├── intent/agent.py               【改造 Phase3】Tool Calling
│       ├── retrieval/agent.py            【改造 Phase3】Agentic RAG
│       ├── memory/                       【新增 Phase4】记忆 Agent
│       │   ├── agent.py
│       │   └── preference_store.py
│       ├── recommend/                    【新增 Phase4】实时推荐 Agent
│       │   └── agent.py
│       └── supervisor/graph.py           【改造 Phase4】增加新节点
└── uploads/                              【新增】静态文件目录
    ├── avatars/
    └── photos/
```

### 前端新增/改造

```
frontend/src/
├── styles/
│   └── theme.css                         【新增】CSS 变量主题系统
├── components/
│   ├── BottomNav.tsx                     【新增】移动端底部导航
│   ├── ImageUpload.tsx                   【新增】图片上传组件
│   ├── UserCard.tsx                      【改造】暗色主题 + 双列适配
│   ├── Navbar.tsx                        【改造】Lucide 图标 + 完善登录态
│   ├── MatchProgressPanel.tsx            【改造 Phase3】Agent SSE 进度流
│   ├── FollowButton.tsx                  【新增 Phase4】关注按钮
│   └── AgentStepList.tsx                 【新增 Phase3】Agent 步骤动画列表
├── pages/
│   ├── Home.tsx                          【改造】双列瀑布流
│   ├── MyProfile.tsx                     【新增】个人中心
│   ├── EditProfile.tsx                   【新增】编辑资料
│   ├── MatchCenter.tsx                   【新增 Phase3】匹配中心
│   ├── MyHistory.tsx                     【改造 Phase3】仅自己可见
│   ├── Social.tsx                        【新增 Phase4】关注/粉丝
│   ├── ChatList.tsx                      【新增 Phase4】消息列表
│   ├── ChatRoom.tsx                      【新增 Phase4】聊天室
│   └── Settings.tsx                      【新增 Phase5】设置
├── stores/
│   └── appStore.ts                       【新增】Zustand 全局状态
├── hooks/
│   └── useSSE.ts                         【新增 Phase3】SSE 订阅 Hook
└── App.tsx                               【改造】完整路由 + 底部导航
```
