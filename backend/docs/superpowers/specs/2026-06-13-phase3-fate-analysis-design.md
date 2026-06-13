# 心犀 AI — Phase 3 设计文档
# 缘分分析 · UI 重构 · AI 扩展

**版本:** v3.1
**日期:** 2026-06-13
**状态:** 已批准，待实施

---

## 一、背景与目标

本阶段（Phase 3）在 Phase 2（用户中心 + 资料编辑）基础上，完成以下目标：

1. **种入 20 位测试用户**，为系统提供可演示的真实数据
2. **修复 UI 可读性**，由过暗的纯黑换为 INS 风深靛蓝 + 紫粉渐变
3. **简化注册流程**，降低用户入门门槛
4. **实现权限管控**，未登录/未完善资料用户限制操作
5. **"心动 TA 们"功能**，用户可收藏候选者并发起缘分分析
6. **两层缘分分析 Agent**，融合星座/属相/MBTI/爱情语言/能量频率
7. **扩展 AI 功能**，引入红娘推荐、聊天辅助、双向心动通知等

---

## 二、数据模型

### 2.1 users 表新增字段

```sql
profile_complete  BOOLEAN   DEFAULT FALSE   -- 是否完成资料填写（决定能否被发现/发起匹配）
birth_date        DATE      NULL            -- 生日，用于自动计算星座和属相
zodiac_sign       VARCHAR(10) NULL          -- 星座（由 birth_date 计算，后端自动写入）
chinese_zodiac    VARCHAR(10) NULL          -- 属相（由 birth_date 计算，后端自动写入）
age               INTEGER   NULL            -- 改为可空（注册时不填，编辑资料后自动更新）
```

**profile_complete 判定规则：**
以下字段全部非空时自动设为 True：`nickname, gender, age, city, about_me, ideal_partner`

**zodiac_sign / chinese_zodiac 自动计算：**
`PUT /api/auth/me` 更新 birth_date 时，后端通过纯 Python 计算（无需外部 API）并写入。

### 2.2 新增表：fate_candidates（心动 TA 们清单）

```sql
CREATE TABLE xinxi.fate_candidates (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(20) NOT NULL REFERENCES xinxi.users(user_id),
    candidate_id    VARCHAR(20) NOT NULL REFERENCES xinxi.users(user_id),
    note            VARCHAR(200),                   -- 用户自定义备注
    added_at        TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, candidate_id),
    CHECK(user_id != candidate_id)
);
CREATE INDEX idx_fate_candidates_user ON xinxi.fate_candidates(user_id, added_at DESC);
```

### 2.3 新增表：fate_analyses（缘分分析记录）

```sql
CREATE TABLE xinxi.fate_analyses (
    id                     SERIAL PRIMARY KEY,
    analysis_id            VARCHAR(40) UNIQUE NOT NULL,
    initiator_id           VARCHAR(20) NOT NULL REFERENCES xinxi.users(user_id),
    analysis_type          VARCHAR(30) NOT NULL,
        -- 'group_overview'       一层分析：全量洞察
        -- 'deep_compatibility'   二层：深度相性（属相+星座+MBTI）
        -- 'comm_advice'          二层：沟通开场建议
        -- 'comparison'           二层：横向对比报告
    candidate_ids          JSONB NOT NULL,           -- 参与分析的候选者 user_id 列表
    result                 JSONB,                    -- AI 报告（Markdown + 结构化评分）
    match_params_snapshot  JSONB,                    -- 发起时的偏好参数快照（用于复盘）
    status                 VARCHAR(20) DEFAULT 'pending',  -- pending/done/failed
    created_at             TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_fate_analyses_initiator ON xinxi.fate_analyses(initiator_id, created_at DESC);
```

### 2.4 新增表：notifications（通知）

```sql
CREATE TABLE xinxi.notifications (
    id           SERIAL PRIMARY KEY,
    notif_id     VARCHAR(40) UNIQUE NOT NULL,
    recipient_id VARCHAR(20) NOT NULL REFERENCES xinxi.users(user_id),
    type         VARCHAR(30) NOT NULL,
        -- 'fate_added'     有人把你加入心动清单
        -- 'mutual_fate'    双向心动（你也把对方加了）
        -- 'analysis_done'  缘分分析完成
        -- 'new_message'    新私信
    actor_id     VARCHAR(20) REFERENCES xinxi.users(user_id),
    payload      JSONB DEFAULT '{}',
    is_read      BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_notifications_recipient ON xinxi.notifications(recipient_id, is_read, created_at DESC);
```

### 2.5 已有表（保留不变）

| 表名 | 用途 |
|------|------|
| `match_records` | AI 搜索匹配记录（寻找缘分功能） |
| `match_candidates` | 每次搜索结果中的候选人 |
| `follow_relationships` | 关注关系 |
| `conversations` + `messages` | 私信系统 |
| `blacklist` | 拉黑 |

---

## 三、UI 设计系统（INS 风格）

### 3.1 色彩系统

```css
/* 主背景：深靛蓝，不是纯黑 */
--bg-base:      #0f0c29;
--bg-elevated:  #1a1040;
--bg-deep:      #1e0a3c;

/* 主渐变：蓝紫（按钮、高亮、卡片边框） */
--gradient-primary:  linear-gradient(135deg, #667eea, #764ba2);

/* 心动渐变：粉玫瑰（心动操作专用） */
--gradient-heart:    linear-gradient(135deg, #f093fb, #f5576c);

/* AI 渐变：青蓝（分析标签、AI 徽章） */
--gradient-ai:       linear-gradient(135deg, #4facfe, #00f2fe);

/* 文字 */
--text-primary:   #f0f0f8;   /* 主文字，暖白 */
--text-secondary: #a0a0c0;   /* 辅助文字，不刺眼 */
--text-muted:     #6060a0;   /* 淡化文字 */

/* 卡片（玻璃态） */
--card-bg:     rgba(255, 255, 255, 0.07);
--card-border: rgba(255, 255, 255, 0.12);
--card-blur:   blur(16px);
```

### 3.2 字体规范

| 元素 | 字号 | 字重 |
|------|------|------|
| 页面主标题 | 26-32px | 700 |
| 区块标题 | 18-22px | 600 |
| 卡片标题 | 16-18px | 600 |
| 正文 | 15px（移动端 16px） | 400 |
| 辅助说明 | 13px | 400 |
| 行高 | 1.6 | — |

### 3.3 用户卡片规范

- 封面图占卡片高度 **65%**，无图时用渐变占位（`--gradient-primary`）+ 居中头像
- 图片区底部叠加渐变遮罩（透明 → `rgba(0,0,0,0.7)`），文字叠在其上
- 右下角 ❤️ 心动按钮：
  - 未心动：透明白边 ghost 按钮
  - 已心动：`--gradient-heart` 填充 + 脉冲动画
- 左上角状态标签：绿点"已完善" / 灰点"待完善"
- Hover 效果：渐变发光边框（`box-shadow: 0 0 0 1.5px transparent`，hover 变渐变色）

### 3.4 首页布局

- PC（≥1280px）：**3 列瀑布流**
- 平板（768-1279px）：**2 列**
- 移动端（<768px）：**1 列 + 固定底部导航栏**
- 顶部 Hero 区（未登录可见）：大标语 + 渐变描边按钮 + 细粒子漂浮背景

### 3.5 潮流 UI 元素

| 元素 | 位置 | 效果 |
|------|------|------|
| 渐变描边卡片 | 所有卡片 hover | 流光渐变 1.5px 边框 |
| 数字滚动动效 | 缘分值展示 | 从 0 滚动到最终分 |
| Bento Grid | 分析报告页 | 不规则格子排版 |
| 毛玻璃弹窗 | 所有 Modal/Drawer | backdrop-blur + 半透明 |
| 星星粒子背景 | 首页 Hero 区域 | 细小粒子浮动，宇宙感 |

---

## 四、功能设计

### 4.1 权限矩阵

| 操作 | 游客 | 登录+未完善资料 | 登录+已完善资料 |
|------|------|----------------|----------------|
| 浏览首页列表 | ✅ | ✅ | ✅ |
| 查看用户详情 | ✅ | ✅ | ✅ |
| 加入心动 TA 们 | ❌ → 登录 | ✅ | ✅ |
| 寻找缘分（AI 匹配） | ❌ → 登录 | ❌ → 提示完善资料 | ✅ |
| 发起缘分分析 | ❌ → 登录 | ❌ → 提示完善资料 | ✅ |
| 发送私信 | ❌ → 登录 | ✅ | ✅ |

**首页用户列表仅展示 `profile_complete=True` 的用户**，保护未完善资料的用户隐私。

### 4.2 注册流程（简化）

注册只需 4 个字段：**昵称 + 性别 + 手机号 + 密码**

```
POST /api/auth/register
{
  "nickname": "...",
  "gender": "男|女",
  "phone": "138...",
  "password": "..."
}
```

注册成功后：
- 自动登录，返回 JWT token
- `profile_complete = False`
- 跳转首页，顶部显示「✨ 完善资料，解锁寻找缘分」引导横幅

### 4.3 心动 TA 们功能

**API 端点：**

```
POST   /api/fate/candidates           # 加入心动清单
DELETE /api/fate/candidates/{cand_id} # 取消心动
GET    /api/fate/candidates           # 获取我的心动清单（含候选者详情）
```

**前端流程：**
1. 首页卡片右下角 ❤️ 点击 → 立即响应（乐观更新）→ 后台调 API
2. 加入成功后触发通知（`fate_added` → 对方收到通知）
3. 若双方互相心动 → 触发 `mutual_fate` 通知 + 解锁私信快捷入口
4. 导航栏「心动 TA 们」入口显示未分析候选者数量角标

**心动清单页面：**
- 候选者卡片列表（缩略式）
- 每人右侧：「立即分析」（一对一）
- 底部固定：「统一缘分分析」（全部候选者）
- 卡片支持备注（可选）和删除

### 4.4 缘分分析流程

**第一层：全量洞察 (group_overview)**

```
POST /api/fate/analyses
{
  "analysis_type": "group_overview",
  "candidate_ids": ["U001", "U002", ...],
  "match_params_override": {...}  // 可选
}
```

FateAnalysisAgent 输出：
- 用户择偶偏好洞察（基于选择模式）
- 每位候选者匹配概要（全量展示，含星座/属相/MBTI 标签，按综合分降序）
- AI 推荐理由（自然语言叙述）
- 能量频率描述（"你们的能量场..."）

**第二层：升级分析（用户选路径后触发）**

```
POST /api/fate/analyses
{
  "analysis_type": "deep_compatibility|comm_advice|comparison",
  "candidate_ids": ["U001", "U002"],  // 用户从第一层结果中筛选
  "parent_analysis_id": "..."          // 关联第一层
}
```

| 路径 | 内容 |
|------|------|
| `deep_compatibility` | 星座配对 · 属相相性 · MBTI 互补 · 爱情语言匹配 · 潜在摩擦点 |
| `comm_advice` | 第一次约会话题建议 · 破冰方式 · 根据对方 MBTI/兴趣个性化 |
| `comparison` | 多人维度对比 Bento 表格（外貌/学历/兴趣/价值观/地理距离） |

**分析结果展示：**
- Streaming 逐字输出（`GET /api/fate/analyses/{id}/stream`）
- 结果末尾附「缘分塔罗一牌」（AI 随机抽取 + 趣味解读，装饰性）
- 报告可分享为图片名片（截图卡片）

### 4.5 缘分参数临时调整（HITL）

点击「寻找缘分」时，先弹出底部抽屉（Drawer）：

| 参数 | 控件 | 范围 |
|------|------|------|
| 年龄范围 | 双滑块 | 18–60 |
| 身高范围 | 双滑块 | 145–195 cm |
| 城市 | 下拉选择 | 不限 / 同城 / 指定城市 |
| 学历要求 | 单选 | 不限 / 大专及以上 / 本科及以上 / 硕士及以上 |
| MBTI | 多选 tag | 16 种 |

底部说明文字：「仅本次有效，不改变你的默认设置」

---

## 五、AI Agent 架构

### 5.1 Agent 清单

| Agent | 文件位置 | 触发方式 | 使用技术 |
|-------|----------|----------|----------|
| `FateAnalysisAgent` | `backend/core/agents/fate/agent.py` | 用户发起缘分分析 | LangGraph 状态机 + Tool Calling + Streaming |
| `RecommendAgent` | `backend/core/agents/recommend/agent.py` | 每日定时（APScheduler） | LangGraph + Agentic RAG |
| `MatchingAgent` | `backend/core/agents/matching/agent.py` | 用户点击「寻找缘分」 | 已有，继续扩展 |
| `ChatAssistAgent` | `backend/core/agents/chat_assist/agent.py` | 私聊侧边栏触发 | Tool Calling + Memory |
| `MatchmakerAgent` | `backend/core/agents/matchmaker/agent.py` | 用户与 AI 红娘对话 | LangGraph + Agentic RAG + HITL |

### 5.2 FateAnalysisAgent 工具集

```python
tools = [
    get_user_profile,          # 获取完整用户画像
    calc_zodiac_compatibility,  # 计算西方星座配对（内置规则库）
    calc_chinese_zodiac_compat, # 计算属相合婚（内置规则库）
    calc_mbti_compatibility,    # 计算 MBTI 相性（内置规则库）
    extract_love_language,      # NLP 提取爱情语言（GPT function）
    semantic_similarity,        # ChromaDB 向量相似度
    generate_tarot_card,        # 随机抽取塔罗牌 + 缘分解读（纯 GPT）
]
```

### 5.3 AI 分析维度

| 维度 | 数据来源 | 权重 |
|------|----------|------|
| 星座配对 | zodiac_sign（双方） | 15% |
| 属相相性 | chinese_zodiac（双方） | 10% |
| MBTI 互补 | mbti（双方） | 20% |
| 爱情语言匹配 | about_me + ideal_partner（NLP 提取） | 20% |
| 语义相似度 | ChromaDB 向量距离 | 20% |
| 价值观对齐 | hobbies + about_me（关键词） | 10% |
| 基础条件 | 年龄/城市/学历匹配 | 5% |

### 5.4 Agent 技术学习映射

| LangChain/LangGraph 技术 | 对应功能 | 学习价值 |
|--------------------------|----------|----------|
| **Tool Calling** | FateAnalysisAgent 的星座/MBTI 工具 | 核心 |
| **Agentic RAG** | 从 ChromaDB 检索相似用户画像 | 核心 |
| **LangGraph 状态机** | 两层分析流程（overview → 路径 → deep） | 核心 |
| **HITL** | 参数调整抽屉（用户在 Agent 前介入） | 重要 |
| **Memory Agent** | 记住用户历史分析偏好 | 重要 |
| **Streaming** | 分析报告逐字流式输出 | 重要 |
| **定时 Agent** | RecommendAgent 每日推送 | 进阶 |
| **MCP** | 扩展工具集（黄历/天气等） | 进阶 |

---

## 六、潮流元素

### 6.1 功能层面

| 元素 | 体现方式 |
|------|----------|
| **缘分指数** | 每对用户展示 0–100 的综合分，带粒子光环动画 |
| **星座今日运势** | 首页顶部轮播，AI 生成当日「[星座]缘分运势」 |
| **MBTI 相性标签** | 卡片显示「INFJ × ENFP = 灵魂共鸣」等 |
| **能量颜色** | 每个用户有专属「能量色」（AI 基于画像生成），卡片渐变边框色 |
| **塔罗今日一牌** | 分析报告末尾附趣味塔罗解读 |
| **心动热力图** | 个人主页展示「本周被心动次数」 |

### 6.2 UI 层面

| 元素 | 实现方式 |
|------|----------|
| Bento Grid | 分析报告页不规则格子，CSS Grid area |
| 渐变描边动画 | `@keyframes border-glow` 流光效果 |
| 数字滚动 | `countUp.js` 或 CSS `@property` 动画 |
| 毛玻璃弹窗 | `backdrop-filter: blur(20px)` |
| 星星粒子背景 | 轻量 Canvas 粒子（或纯 CSS 伪元素） |

---

## 七、种子数据：20 位用户

覆盖条件：男 10 / 女 10，年龄 22–38，城市涵盖上海/北京/广州/成都/杭州，职业多样，MBTI 覆盖主要 8 种，均设 `profile_complete=True`，带 zodiac_sign + chinese_zodiac，密码统一为 `Test@123456`。

---

## 八、扩展功能路线图（后续 Phase）

| 优先级 | 功能 | 涉及技术 |
|--------|------|---------|
| 🔥 高 | 双向心动通知 + 私信快捷入口 | WebSocket / 通知推送 |
| 🔥 高 | AI 红娘每日主动推荐（RecommendAgent） | APScheduler + LangGraph |
| 🟡 中 | 缘分日历（基于星座/属相） | LLM 生成 + 前端日历组件 |
| 🟡 中 | 分享名片（生成漂亮图片卡） | html2canvas / puppeteer |
| 🟡 中 | 查看谁看过我（足迹） | 用户行为日志表 |
| 🔵 低 | AI 聊天辅助（ChatAssistAgent） | Memory + Tool Calling |
| 🔵 低 | AI 红娘对话角色（MatchmakerAgent） | LangGraph + HITL |
