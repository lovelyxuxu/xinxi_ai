# 心犀AI v2.0 - 企业级架构设计文档

> **项目定位**：基于 LangChain + LangGraph 的智能婚恋匹配系统（学习项目）
> **核心关注**：Agent 开发实践、企业级用户体验、数据持久化
> **更新日期**：2026-06-13

---

## 一、现有问题分析与重构目标

### 1.1 当前问题清单

| 编号 | 问题 | 严重度 | 说明 |
|------|------|--------|------|
| P1 | 无登录注册系统 | 高 | 所有接口无鉴权，游客可直接操作 |
| P2 | 用户无法编辑自身信息 | 高 | 缺少个人中心编辑功能 |
| P3 | 匹配参数不可调节 | 中 | 用户无法在匹配前自定义筛选条件 |
| P4 | 历史隐私问题 | 高 | 任何用户可查看他人匹配历史 |
| P5 | 导航栏逻辑不合理 | 中 | 已登录用户仍显示"注册"按钮 |
| P6 | 数据存储在内存/ChromaDB | 高 | 无正式关系型数据库，数据不完整 |
| P7 | 无社交功能 | 中 | 缺少关注、私信等用户间互动 |
| P8 | 界面过于简单 | 中 | 缺少设置、退出等企业级交互 |

### 1.2 重构目标

- **数据层**：PostgreSQL 作为主数据库（利用 LangFuse 已有的 PG 实例）
- **认证层**：JWT Token 认证，支持登录/注册/退出
- **用户层**：个人资料可编辑，匹配参数可调，历史仅自己可见
- **社交层**：关注/粉丝系统 + 用户间私信
- **Agent 层**：匹配流程集成用户自定义参数，增强智能推荐
- **学习层**：所有代码保留详尽注释，着重 Agent 开发实践

---

## 二、数据库设计（PostgreSQL）

### 2.1 ER 关系图

```
users (用户表)
  ├── 1:N → match_records (匹配记录)
  │         └── 1:N → match_candidates (匹配候选人)
  ├── 1:N → follow_relationships (关注关系, as follower)
  ├── 1:N → follow_relationships (关注关系, as following)
  ├── 1:N → conversations (会话, as participant)
  └── 1:N → messages (消息)

conversations (会话)
  └── 1:N → messages (消息)

blacklist (黑名单)
  └── N:1 → users (被屏蔽用户)
```

### 2.2 表结构详细设计

#### users - 用户表

```sql
-- 【学习要点】
-- 用户表是整个系统的核心，存储所有个人信息和择偶偏好。
-- password_hash 使用 bcrypt 加密，绝不存储明文密码。
-- 择偶偏好字段（target_*）会被 Agent 的 parse_intent 节点读取，
-- 作为混合检索的 metadata filter 条件。
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(20) UNIQUE NOT NULL,  -- 业务ID: "U" + 8位随机
    nickname        VARCHAR(50) NOT NULL,
    gender          VARCHAR(10) NOT NULL CHECK (gender IN ('male', 'female')),
    age             INTEGER NOT NULL CHECK (age BETWEEN 18 AND 80),
    city            VARCHAR(50) NOT NULL,
    province        VARCHAR(50) NOT NULL,
    education       VARCHAR(20) DEFAULT '本科',
    annual_income   VARCHAR(30) DEFAULT '未填写',
    marital_status  VARCHAR(20) DEFAULT '未婚',
    mbti            VARCHAR(10) DEFAULT '未知',
    height_cm       INTEGER,                      -- 身高（cm），用于筛选
    about_me        TEXT DEFAULT '',
    ideal_partner   TEXT DEFAULT '',
    hobbies         TEXT DEFAULT '',

    -- 择偶偏好（Agent 会读取这些字段构建搜索条件）
    target_gender   VARCHAR(10) NOT NULL,
    target_age_min  INTEGER DEFAULT 18,
    target_age_max  INTEGER DEFAULT 45,
    target_city     VARCHAR(50) DEFAULT '不限',
    target_height_min INTEGER,                    -- 最低身高要求
    target_height_max INTEGER,                    -- 最高身高要求
    target_education VARCHAR(20),                 -- 最低学历要求

    -- 认证字段
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(100) UNIQUE,
    phone           VARCHAR(20) UNIQUE,

    -- 元数据
    is_active       BOOLEAN DEFAULT TRUE,
    avatar_url      VARCHAR(500),
    last_login_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_gender_city ON users(gender, city);
CREATE INDEX idx_users_user_id ON users(user_id);
```

#### match_records - 匹配记录表

```sql
-- 【学习要点】
-- 每条匹配记录对应一次完整的 Agent 工作流执行。
-- thread_id 关联 LangGraph 的检查点（checkpoint），可回溯 Agent 执行过程。
-- user_filters 存储用户本次匹配时自定义的筛选参数（JSON），
-- 这样 Agent 的 parse_intent 节点可以优先使用用户显式指定的条件。
CREATE TABLE match_records (
    id              SERIAL PRIMARY KEY,
    match_id        VARCHAR(20) UNIQUE NOT NULL,
    user_id         VARCHAR(20) NOT NULL REFERENCES users(user_id),
    thread_id       VARCHAR(100),                -- LangGraph checkpoint thread_id
    user_filters    JSONB DEFAULT '{}',          -- 用户自定义筛选参数
    match_letters   JSONB DEFAULT '[]',          -- 推荐信列表
    status          VARCHAR(20) DEFAULT 'completed', -- pending/completed/failed
    evaluation      JSONB,                       -- LLM-as-Judge 评估结果
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_records_user_id ON match_records(user_id);
CREATE INDEX idx_match_records_created_at ON match_records(created_at DESC);
```

#### match_candidates - 匹配候选人表

```sql
-- 【学习要点】
-- 将候选人从 match_records 中拆出，实现一对多关系。
-- 这样可以在数据库层面做统计分析（如：某用户被推荐了多少次）。
CREATE TABLE match_candidates (
    id              SERIAL PRIMARY KEY,
    match_id        VARCHAR(20) NOT NULL REFERENCES match_records(match_id),
    candidate_id    VARCHAR(20) NOT NULL REFERENCES users(user_id),
    score           INTEGER DEFAULT 0,           -- 契合指数 0-100
    reason          TEXT DEFAULT '',              -- LLM 生成的匹配理由
    rank            INTEGER DEFAULT 0,            -- 排名（1=最佳）
    is_viewed       BOOLEAN DEFAULT FALSE,        -- 用户是否查看过
    is_liked        BOOLEAN DEFAULT FALSE,        -- 用户是否喜欢
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_candidates_match_id ON match_candidates(match_id);
CREATE INDEX idx_match_candidates_candidate_id ON match_candidates(candidate_id);
```

#### follow_relationships - 关注关系表

```sql
-- 【学习要点】
-- 类似抖音/小红书的关注系统。
-- 使用 (follower_id, following_id) 联合唯一索引防止重复关注。
-- 查询某人的粉丝数：SELECT COUNT(*) FROM follow_relationships WHERE following_id = ?
-- 查询某人关注了谁：SELECT * FROM follow_relationships WHERE follower_id = ?
CREATE TABLE follow_relationships (
    id              SERIAL PRIMARY KEY,
    follower_id     VARCHAR(20) NOT NULL REFERENCES users(user_id),  -- 关注者
    following_id    VARCHAR(20) NOT NULL REFERENCES users(user_id),  -- 被关注者
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(follower_id, following_id),
    CHECK (follower_id != following_id)  -- 不能关注自己
);

CREATE INDEX idx_follow_follower ON follow_relationships(follower_id);
CREATE INDEX idx_follow_following ON follow_relationships(following_id);
```

#### conversations - 会话表

```sql
-- 【学习要点】
-- 用户间私信系统。每个会话是两个人之间的对话通道。
-- participant_a 和 participant_b 存储两个用户ID，
-- 约定 participant_a < participant_b（字典序），保证唯一性。
-- 这样同一对用户只有一个会话，避免重复创建。
CREATE TABLE conversations (
    id              SERIAL PRIMARY KEY,
    conversation_id VARCHAR(40) UNIQUE NOT NULL,  -- "conv_" + hash(a, b)
    participant_a   VARCHAR(20) NOT NULL REFERENCES users(user_id),
    participant_b   VARCHAR(20) NOT NULL REFERENCES users(user_id),
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(participant_a, participant_b),
    CHECK (participant_a < participant_b)  -- 字典序保证唯一
);
```

#### messages - 消息表

```sql
-- 【学习要点】
-- 消息表存储所有私信内容。
-- is_read 标记用于实现"未读消息"提醒功能。
-- sender_id 关联 users 表，可以快速查询某用户发送的所有消息。
CREATE TABLE messages (
    id              SERIAL PRIMARY KEY,
    message_id      VARCHAR(20) UNIQUE NOT NULL,
    conversation_id VARCHAR(40) NOT NULL REFERENCES conversations(conversation_id),
    sender_id       VARCHAR(20) NOT NULL REFERENCES users(user_id),
    content         TEXT NOT NULL,
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id);
```

#### blacklist - 黑名单表

```sql
-- 【学习要点】
-- 黑名单用于在匹配时排除特定用户。
-- Agent 的 retrieval_agent 在检索候选人时会查询此表，
-- 将黑名单用户从搜索结果中过滤掉。
CREATE TABLE blacklist (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(20) NOT NULL REFERENCES users(user_id),  -- 设置者
    blocked_user_id VARCHAR(20) NOT NULL REFERENCES users(user_id),  -- 被屏蔽者
    reason          VARCHAR(200) DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, blocked_user_id),
    CHECK (user_id != blocked_user_id)
);
```

### 2.3 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| ORM | **SQLAlchemy 2.0** (async) | Python 最成熟的 ORM，支持异步 |
| 迁移 | **Alembic** | 自动生成数据库迁移脚本 |
| 连接池 | **asyncpg** | 高性能异步 PostgreSQL 驱动 |
| 向量库 | **ChromaDB**（保留） | 仅用于向量搜索，用户元数据由 PG 管理 |

---

## 三、认证系统设计

### 3.1 认证流程

```
注册:
  用户填写表单 → POST /api/auth/register → bcrypt 加密密码 → 存入 PG → 返回 JWT

登录:
  用户输入账号密码 → POST /api/auth/login → 验证 bcrypt → 生成 JWT → 返回 Token

鉴权:
  前端请求 → Authorization: Bearer <token> → FastAPI Depends(get_current_user) → 解码 JWT → 注入 user

刷新:
  Token 过期 → POST /api/auth/refresh → 验证旧 Token → 签发新 Token
```

### 3.2 JWT Token 设计

```python
# Token Payload 结构
{
    "sub": "F002",              # user_id
    "nickname": "雨桐",
    "exp": 1718400000,          # 过期时间（2小时）
    "iat": 1718392800,          # 签发时间
    "type": "access"            # access / refresh
}
```

### 3.3 前端认证状态管理

```typescript
// 使用 React Context 管理全局认证状态
interface AuthContext {
  user: UserProfile | null       // 当前登录用户
  token: string | null           // JWT Token
  login: (email, password) => Promise<void>
  register: (data) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

// 路由守卫：未登录用户自动跳转到登录页
// 已登录用户隐藏"注册"按钮，显示头像+下拉菜单
```

### 3.4 API 鉴权中间件

```python
# 【学习要点】
# FastAPI 的 Depends() 机制实现依赖注入：
# - get_current_user: 从 JWT 解析当前用户，未登录抛 401
# - get_optional_user: 尝试解析，未登录返回 None（用于公开页面）
# 这样每个路由可以灵活选择是否需要登录。

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """必须登录才能访问的接口"""
    payload = decode_jwt(token)
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(401, "用户不存在或已禁用")
    return user

async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选登录（游客也能访问，但登录用户有更多功能）"""
    if not token:
        return None
    payload = decode_jwt(token)
    return await db.get(User, payload["sub"])
```

---

## 四、API 接口设计

### 4.1 认证模块 `/api/auth`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册新用户 | 无 |
| POST | `/api/auth/login` | 登录 | 无 |
| POST | `/api/auth/refresh` | 刷新 Token | refresh_token |
| GET | `/api/auth/me` | 获取当前用户信息 | JWT |
| PUT | `/api/auth/me` | 编辑个人资料 | JWT |
| PUT | `/api/auth/password` | 修改密码 | JWT |

### 4.2 用户模块 `/api/users`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/users` | 用户列表（发现页） | 可选 |
| GET | `/api/users/{user_id}` | 用户详情 | 可选 |
| PUT | `/api/users/me` | 编辑自己的资料 | JWT |
| DELETE | `/api/users/me` | 注销账号 | JWT |
| GET | `/api/users/me/followers` | 我的粉丝列表 | JWT |
| GET | `/api/users/me/following` | 我的关注列表 | JWT |

### 4.3 匹配模块 `/api/match`（仅自己可见）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| WS | `/api/match/ws` | 实时匹配（WebSocket） | JWT（query param） |
| GET | `/api/match/history` | **我的**匹配历史 | JWT |
| GET | `/api/match/{match_id}` | 匹配详情 | JWT（仅本人） |
| POST | `/api/match/evaluate/{match_id}` | LLM-as-Judge 评估 | JWT |

**WebSocket 匹配参数扩展**：

```json
// 客户端连接时发送的匹配参数
{
    "type": "start_match",
    "filters": {
        "age_min": 25,
        "age_max": 35,
        "city": "上海",
        "height_min": 170,
        "education": "本科",
        "exclude_ids": ["M003", "M005"],
        "custom_query": "喜欢户外运动的"
    }
}
```

### 4.4 社交模块 `/api/social`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/social/follow/{user_id}` | 关注用户 | JWT |
| DELETE | `/api/social/follow/{user_id}` | 取消关注 | JWT |
| GET | `/api/social/followers/{user_id}` | 粉丝列表 | 可选 |
| GET | `/api/social/following/{user_id}` | 关注列表 | 可选 |
| GET | `/api/social/conversations` | 我的会话列表 | JWT |
| GET | `/api/social/conversations/{conv_id}/messages` | 会话消息 | JWT（仅参与者） |
| WS | `/api/social/chat/{conv_id}` | 实时聊天 | JWT |
| POST | `/api/social/conversations` | 创建/获取会话 | JWT |
| POST | `/api/social/blacklist/{user_id}` | 加入黑名单 | JWT |
| DELETE | `/api/social/blacklist/{user_id}` | 移除黑名单 | JWT |

### 4.5 访谈模块 `/api/interview`（保留现有）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| WS | `/api/interview/ws` | AI 红娘访谈 | JWT |

---

## 五、前端页面设计

### 5.1 路由结构

```tsx
// 公开页面（无需登录）
<Route path="/" element={<Home />} />                   // 发现页
<Route path="/login" element={<Login />} />             // 登录
<Route path="/register" element={<Register />} />      // 注册
<Route path="/user/:userId" element={<UserDetail />} /> // 用户详情

// 受保护页面（需要登录，使用 <ProtectedRoute> 包裹）
<Route path="/profile" element={<MyProfile />} />         // 个人中心
<Route path="/profile/edit" element={<EditProfile />} />  // 编辑资料
<Route path="/match" element={<MatchCenter />} />         // 匹配中心（含参数调节）
<Route path="/history" element={<MyHistory />} />         // 我的匹配历史
<Route path="/social" element={<Social />} />             // 社交（关注/粉丝）
<Route path="/chat" element={<ChatList />} />             // 消息列表
<Route path="/chat/:convId" element={<ChatRoom />} />     // 聊天室
<Route path="/settings" element={<Settings />} />         // 设置
```

### 5.2 导航栏设计（已登录态 vs 未登录态）

```
未登录:
  [💕 心犀AI]   [🏠 发现]  [🔑 登录]  [✨ 注册]

已登录:
  [💕 心犀AI]   [🏠 发现]  [💕 匹配]  [💬 消息(3)]  [👤 头像▼]
                                                      └─ 个人中心
                                                      └─ 我的关注
                                                      └─ 设置
                                                      └─ 退出登录
```

### 5.3 页面功能说明

#### 个人中心（MyProfile）
- 头像 + 基本资料展示
- **编辑资料**按钮 → 跳转编辑页
- 数据统计：匹配次数、关注数、粉丝数
- 快捷入口：寻找缘分、AI 访谈、消息

#### 编辑资料（EditProfile）
- 分区块表单：基本信息 / 择偶偏好 / 自我介绍
- 表单验证（zod + react-hook-form）
- 保存后自动更新 ChromaDB 向量（用于后续匹配）

#### 匹配中心（MatchCenter）
- **参数调节面板**：年龄范围、城市、身高、学历等筛选条件
- 自定义搜索文本（"我想找一个..."）
- 黑名单管理
- 一键开始匹配（WebSocket 实时进度）
- 匹配结果展示（评分 + 推荐信 + 关注/私信按钮）

#### 消息（ChatList + ChatRoom）
- 会话列表：最近联系人 + 未读数
- 聊天室：实时消息（WebSocket）+ 历史消息加载

---

## 六、Agent 集成改造

### 6.1 匹配流程增强

```
用户点击"寻找缘分" + 自定义筛选参数
  │
  ▼
parse_intent 节点改造:
  - 读取 user_filters（用户显式指定的条件）
  - 读取 user profile 的 target_* 字段（用户默认偏好）
  - LLM 综合分析，生成最终的 hard_filters + rewritten_query
  - 【优先级】用户本次参数 > 用户默认偏好 > LLM 推断
  │
  ▼
hybrid_search (retrieval_agent) 改造:
  - metadata filter 增加: height_cm, education 等字段
  - 排除黑名单用户 (NOT IN blacklist)
  - 排除已推荐过的用户 (NOT IN match_candidates)
  - 排除用户指定的 exclude_ids
  │
  ▼
后续节点不变（post_analysis → reflection → letter → judge）
```

### 6.2 AgentState 扩展

```python
class AgentState(TypedDict, total=False):
    user_profile: UserProfile
    user_filters: dict          # 【新增】用户自定义筛选参数
    hard_filters: dict
    rewritten_query: str
    candidates: list[dict]
    exclude_user_ids: list[str] # 【新增】需排除的用户ID列表
    analysis_results: list[dict]
    best_score: float
    loop_count: int
    should_retry: bool
    retry_strategy: str
    new_query: Optional[str]
    top_matches: list[dict]
    match_letters: list[str]
    messages: list[str]
    # ... supervisor 字段
```

### 6.3 智能提示 Agent（新增可选）

```python
# 【学习要点】
# 这是一个可选的增强 Agent，用于分析用户行为并给出个性化提示。
# 例如：用户连续3天没有匹配，可以提示"要不要放宽年龄范围？"
# 这展示了 Agent 在推荐系统中的应用——不只是匹配，还能做用户运营。

class SuggestionAgent:
    """智能提示 Agent - 分析用户行为，生成个性化建议"""

    def analyze(self, user_id: str, match_history: list) -> list[str]:
        """
        分析维度：
        1. 匹配频率：是否过于频繁/稀少
        2. 参数变化：是否一直用相同条件
        3. 成功率：匹配分数是否持续偏低
        4. 时间间隔：上次匹配距今多久
        """
        # ... LLM 分析 + 生成建议
```

---

## 七、实施阶段规划

### Phase 1: 数据库 + 认证基础
**核心产出**：PostgreSQL 集成 + JWT 认证 + 用户注册/登录

- [x] 设计 PG 表结构（本文档）
- [ ] 集成 SQLAlchemy + Alembic
- [ ] 实现 auth 模块（register/login/refresh/me）
- [ ] JWT 中间件 + get_current_user 依赖注入
- [ ] 前端：Login/Register 页面
- [ ] 前端：AuthContext + ProtectedRoute + Token 管理
- [ ] 导航栏：登录态/未登录态切换

### Phase 2: 用户中心 + 资料编辑
**核心产出**：个人中心 + 资料编辑 + 数据同步 ChromaDB

- [ ] PUT /api/auth/me 编辑接口
- [ ] 编辑资料页面（表单 + 验证）
- [ ] 编辑后自动更新 ChromaDB 向量
- [ ] 个人中心页面重构

### Phase 3: 匹配增强 + 历史隐私
**核心产出**：匹配参数调节 + 历史仅自己可见 + 黑名单

- [ ] WebSocket 匹配参数传递
- [ ] parse_intent 节点改造（读取 user_filters）
- [ ] retrieval_agent 改造（排除黑名单/已推荐）
- [ ] 匹配中心页面（参数面板 + 实时匹配）
- [ ] 历史接口改造（仅返回当前用户）
- [ ] 匹配记录存入 PG（替代 SQLite history_store）

### Phase 4: 社交功能
**核心产出**：关注系统 + 私信聊天

- [ ] 关注/取关 API + 前端按钮
- [ ] 关注列表 / 粉丝列表页面
- [ ] 私信系统（会话 + 消息 + WebSocket）
- [ ] 消息列表页面 + 聊天室页面
- [ ] 未读消息提醒

### Phase 5: 体验优化 + 测试
**核心产出**：企业级 UX + 全面测试

- [ ] 设置页面（修改密码、黑名单管理）
- [ ] 智能提示 Agent（可选）
- [ ] 全面 E2E 测试
- [ ] 代码注释和学习文档完善

---

## 八、技术栈变更

### 新增依赖（Backend）

```
# requirements.txt 新增
sqlalchemy[asyncio] >= 2.0    # 异步 ORM
asyncpg >= 0.29               # PostgreSQL 异步驱动
alembic >= 1.13               # 数据库迁移
python-jose[cryptography] >= 3.3  # JWT 编解码
passlib[bcrypt] >= 1.7        # 密码加密
python-multipart >= 0.0.6     # 文件上传（头像）
```

### 新增依赖（Frontend）

```json
// package.json 新增
"zustand": "^5.0.0"           // 轻量状态管理（替代 Context 的复杂场景）
"socket.io-client": "^4.7.0"  // 如果用 Socket.IO（可选，原生 WebSocket 也可）
```

### 环境变量新增

```bash
# .env 新增
DATABASE_URL=postgresql+asyncpg://langfuse:langfuse@localhost:5432/langfuse
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 九、保留不变的部分

以下组件经过验证，保持现有实现：

| 组件 | 文件 | 说明 |
|------|------|------|
| ChromaDB 向量搜索 | `chroma_store.py` | 仅用于语义搜索，元数据改由 PG 管理 |
| Embedding 服务 | `embedding_service.py` | bge-m3 嵌入不变 |
| Agent 节点核心逻辑 | `nodes.py` | parse_intent 等核心逻辑保留，仅扩展参数 |
| Supervisor 图 | `supervisor/graph.py` | 多 Agent 架构不变 |
| Interview 子图 | `interview/` | 访谈流程不变 |
| LLM-as-Judge | `evaluation/judge.py` | 评估模块不变 |
| LangFuse 可观测性 | `observability.py` | 追踪不变 |
| JSON 解析工具 | `json_parser.py` | DeepSeek 兼容不变 |

---

## 十、文件结构变更预览

```
backend/
├── api/
│   ├── app.py                    # 新增 CORS + DB session middleware
│   ├── deps.py                   # 改造：PG session 注入替代 AppServices
│   ├── auth.py                   # 【新增】JWT 工具 + get_current_user
│   ├── schemas.py                # 扩展：新增 Auth/社交相关 Schema
│   └── routers/
│       ├── auth.py               # 【新增】认证路由
│       ├── users.py              # 改造：加入鉴权
│       ├── matching.py           # 改造：匹配参数 + PG 存储
│       ├── interview.py          # 改造：加入鉴权
│       └── social.py             # 【新增】社交路由（关注/消息/黑名单）
├── core/
│   ├── database/
│   │   ├── models.py             # 【新增】SQLAlchemy ORM 模型
│   │   ├── session.py            # 【新增】PG 异步会话工厂
│   │   ├── chroma_store.py       # 保留
│   │   └── history_store.py      # 废弃（改用 PG）
│   └── agent/
│       ├── state.py              # 扩展：user_filters, exclude_user_ids
│       └── nodes.py              # 改造：parse_intent 读取 user_filters
├── alembic/                      # 【新增】数据库迁移目录
│   ├── env.py
│   └── versions/
└── alembic.ini                   # 【新增】Alembic 配置

frontend/src/
├── App.tsx                       # 扩展路由 + AuthProvider
├── contexts/
│   └── AuthContext.tsx            # 【新增】认证状态管理
├── hooks/
│   └── useAuth.ts                # 【新增】认证 Hook
├── pages/
│   ├── Login.tsx                 # 【新增】登录页
│   ├── Register.tsx              # 【重构】注册页
│   ├── MyProfile.tsx             # 【新增】个人中心
│   ├── EditProfile.tsx           # 【新增】编辑资料
│   ├── MatchCenter.tsx           # 【新增】匹配中心（含参数）
│   ├── MyHistory.tsx             # 【重构】我的历史（仅自己）
│   ├── Social.tsx                # 【新增】关注/粉丝
│   ├── ChatList.tsx              # 【新增】消息列表
│   ├── ChatRoom.tsx              # 【新增】聊天室
│   └── Settings.tsx              # 【新增】设置页
├── components/
│   ├── Navbar.tsx                # 重构：登录态切换
│   ├── ProtectedRoute.tsx        # 【新增】路由守卫
│   ├── FollowButton.tsx          # 【新增】关注按钮
│   ├── MatchFilterPanel.tsx      # 【新增】匹配参数面板
│   └── MessageBadge.tsx          # 【新增】未读消息角标
└── api/
    ├── client.ts                 # 扩展：Token 自动附加
    └── types.ts                  # 扩展：新增类型定义
```
