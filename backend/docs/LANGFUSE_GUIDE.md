# LangFuse 可观测性指南

## 概述

本文档介绍如何在心犀AI项目中集成 LangFuse，实现 LLM 应用的可观测性。

可观测性（Observability）是从"Demo"到"生产"的关键一步。
没有它，你无法回答这些核心问题：
- 每次匹配花了多少 token？多少钱？
- 哪个 Agent 最慢？瓶颈在哪里？
- 匹配质量是在提升还是下降？
- 改了 Prompt 后效果变好了还是变差了？

有了 LangFuse，所有答案都在 Dashboard 上一目了然。

## 核心概念

### Trace（追踪）

一次完整的用户请求链路就是一个 Trace。
比如"为用户 Alice 做一次匹配"会产生一个 Trace，
记录从意图解析到最终推荐的全流程。

```
Trace: match_Alice_20260612
├── Span: supervisor (调度决策)
├── Generation: intent_agent (LLM 解析意图)
├── Generation: retrieval_agent (向量检索)
├── Generation: analysis_agent (LLM 深度分析)
├── Generation: letter_agent (LLM 写推荐信)
├── Generation: judge_agent (LLM 评估质量)
└── Score: overall_match_quality = 8.5
```

### Observation（观测点）

Trace 中的每个步骤，分三种类型：

| 类型 | 说明 | 自动/手动 |
|------|------|-----------|
| Generation | 一次 LLM 调用（记录 prompt、completion、token） | 自动 |
| Span | 一个操作（如 Agent 执行、数据库查询） | 自动 |
| Event | 一个离散事件（如"评估完成"） | 手动 |

### Score（评分）

给 Trace 打分数。Judge Agent 的评估结果会自动上报为 Score：

- `overall_match_quality` — 整体匹配质量（1-10）
- `dim_relevance` — 相关性
- `dim_compatibility` — 契合度
- `dim_explanation` — 解释力
- `dim_consistency` — 一致性
- `dim_warmth` — 温度感

## 架构设计

```
┌─────────────────────────────────────────────────┐
│              WebSocket 请求                       │
│  config = { callbacks: [langfuse_handler] }      │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           LangGraph 图执行                        │
│     Callback 通过 LangChain 上下文自动传播          │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Intent   │→│ Retrieval│→│ Analysis │→ ...     │
│  │ Agent    │  │ Agent    │  │ Agent    │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │
│       ▼              ▼              ▼              │
│  ┌─────────────────────────────────────────┐      │
│  │    LangFuse CallbackHandler             │      │
│  │    自动记录所有 LLM 调用事件              │      │
│  └─────────────────┬───────────────────────┘      │
└────────────────────┼──────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│      LangFuse Server (localhost:3000)             │
│      ┌────────────┐  ┌────────────────┐          │
│      │ Dashboard  │  │ PostgreSQL     │          │
│      │ (Web UI)   │  │ (数据存储)      │          │
│      └────────────┘  └────────────────┘          │
└─────────────────────────────────────────────────┘
```

**关键设计：关注点分离**

LangFuse 集成通过 LangChain 的 Callback 机制实现，
完全不需要修改任何 Agent 的业务代码。
这就是"关注点分离"——业务逻辑和可观测性完全解耦。

## 快速开始

### 第一步：启动 LangFuse

确保已安装 Docker Desktop（https://www.docker.com/products/docker-desktop/）。

在项目根目录运行：

```bash
docker compose up -d
```

等待约 30 秒，两个容器启动完成：
- `xinxi-langfuse-db` — PostgreSQL 数据库
- `xinxi-langfuse-web` — LangFuse Web 服务

验证服务已启动：

```bash
docker compose ps
```

### 第二步：创建项目并获取 API Key

1. 打开浏览器访问 http://localhost:3000
2. 点击 "Sign Up" 注册账号（本地部署，数据只存在本机）
3. 登录后，创建一个新项目（例如 "心犀AI"）
4. 进入项目 → Settings → API Keys
5. 点击 "Create new API keys"
6. 复制 Public Key 和 Secret Key

### 第三步：配置 .env

编辑 `backend/.env`，填入 API Key：

```env
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx
```

### 第四步：重启后端

```bash
cd backend
python main.py
```

启动日志中会看到：

```
[LangFuse] 追踪已启动: trace_id=match_U12345_20260612143052
```

### 第五步：触发匹配，查看 Trace

在前端触发一次匹配，然后回到 LangFuse Dashboard：
1. 点击左侧 "Traces"
2. 可以看到刚才的匹配 Trace
3. 点击展开，查看每个 Agent 的执行详情

## Dashboard 使用指南

### Traces 页面

Traces 页面展示所有追踪记录。每个 Trace 包含：

- **Name**: trace 名称（如 `match_U12345`）
- **User**: 用户 ID（可按用户过滤）
- **Latency**: 总耗时
- **Total Cost**: LLM 调用总成本
- **Tags**: 标签（如 `match`, `websocket`, `supervisor`）
- **Scores**: Judge Agent 的评分

点击某个 Trace 可以看到完整的时间线：
- 每个 Agent 的执行时间
- 每次 LLM 调用的 prompt 和 completion
- Token 使用量和成本

### Scores 页面

Scores 页面展示所有评分数据的趋势图：
- 匹配质量随时间的变化
- 各维度评分的分布
- 按用户分组的评分对比

这是优化 Prompt 时最有价值的页面——
你可以直观地看到"改了 Prompt 后分数是上升还是下降"。

### Sessions 页面

Sessions 将同一用户的多次匹配关联在一起。
例如，同一个用户的多次匹配可以在同一个 session 下查看。

## 代码架构

### 文件清单

| 文件 | 角色 |
|------|------|
| `core/utils/observability.py` | LangFuse 集成核心模块 |
| `config/settings.py` → `LangFuseConfig` | 配置管理 |
| `api/routers/matching.py` | 匹配路由中集成 Callback |
| `api/routers/interview.py` | 访谈路由中集成 Callback |
| `core/agents/judge/agent.py` | Judge Agent 中上报评分 |

### 集成流程

```
1. WebSocket 收到请求
   └→ create_langfuse_callback(user_id)     # 创建 CallbackHandler
   └→ config["callbacks"] = [handler]       # 注入到 RunnableConfig
   └→ initial_state["langfuse_trace_id"]    # 存入 State

2. LangGraph 图执行
   └→ Callback 通过上下文自动传播到每个节点
   └→ 每个 LLM 调用自动被追踪

3. Judge Agent 评估
   └→ 从 State 读取 langfuse_trace_id
   └→ langfuse_report_scores(trace_id, evaluation)  # 上报评分

4. 执行完成
   └→ flush_langfuse(handler)               # 确保数据发送完毕
```

### 优雅降级

当 LangFuse 未启用时（`LANGFUSE_ENABLED=false`），
所有可观测性功能自动跳过，不影响核心业务流程。
这是通过 `create_langfuse_callback()` 返回 `None` 实现的：

```python
handler = create_langfuse_callback(user_id="U123")
if handler:       # None 时为 False，跳过
    config["callbacks"] = [handler]
```

## 学习路线

### 第一阶段：基础使用（当前）

- 理解 Trace、Observation、Score 的概念
- 能在 Dashboard 上查看匹配的完整追踪
- 能对比不同匹配的耗时和评分

### 第二阶段：深入分析

- 阅读每次 LLM 调用的 prompt 和 completion
- 分析哪个 Agent 消耗 token 最多
- 找到延迟瓶颈（哪个步骤最慢？）

### 第三阶段：实验对比

- 使用 LangFuse 的 Datasets 功能
- 创建评估数据集，固定一组用户资料
- 对比不同 Prompt 版本的匹配质量

### 第四阶段：生产级运维

- 设置告警规则（如匹配质量低于 6 分时告警）
- 监控成本趋势（每日/每周 token 消耗量）
- 使用 A/B 测试对比不同的 Agent 策略

## 常见问题

### LangFuse 连接失败怎么办？

检查以下几点：
1. Docker 容器是否正在运行：`docker compose ps`
2. `.env` 中的 `LANGFUSE_HOST` 是否正确
3. API Key 是否填写正确（Public Key 以 `pk-lf-` 开头）

如果仍然失败，可观测性模块会自动降级（不影响匹配功能），
日志中会打印警告信息。

### 为什么 Dashboard 上看不到 Trace？

可能的原因：
1. `LANGFUSE_ENABLED` 没有设为 `true`
2. 没有调用 `flush_langfuse()`——数据还在内存队列中
3. API Key 填写错误，数据发送被服务器拒绝

### Token 成本显示为 0？

LangFuse 需要知道模型的定价信息。
对于 DeepSeek 等自定义模型，需要在 LangFuse 的 Settings → Models 中手动添加模型定价。

### 如何对比不同 Prompt 的效果？

1. 每次修改 Prompt 前，用同一组测试用户运行匹配
2. 在 LangFuse 中使用 Tags 标记不同版本（如 `prompt_v1`, `prompt_v2`）
3. 在 Scores 页面按 Tag 过滤，对比平均分数的变化

## 停止与清理

停止 LangFuse 容器（数据保留）：

```bash
docker compose down
```

停止并删除所有数据（慎用）：

```bash
docker compose down -v
```

`-v` 参数会删除 Docker volumes，即 PostgreSQL 中的所有追踪数据。
