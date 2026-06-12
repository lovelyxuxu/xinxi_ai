# 心犀AI - 完整上下文交接文档

> 生成时间：2026-06-11
> 用途：供其他 AI 模型无缝接手继续开发

---

## 一、项目概述

**心犀AI** 是一个基于 LangChain + LangGraph 的智能婚恋匹配系统，是一个**学习项目**，目标是掌握 LangChain/LangGraph 的核心概念。

**核心技术栈：**
- **LLM**: DeepSeek V4 Flash（通过 OpenAI 兼容协议调用）
- **Embedding**: 硅基流动 bge-m3（中文优化，1024维，免费）
- **向量数据库**: ChromaDB 1.x（本地持久化）
- **Agent 工作流**: LangGraph StateGraph
- **后端**: FastAPI + Uvicorn
- **前端**: React 19 + Vite 6 + Tailwind CSS 4 + React Router 7
- **数据模型**: Pydantic v2

**项目位置**: `E:\study\python\xinxi_ai`
**Python 虚拟环境**: `E:\study\python\xinxi_ai\.venv`
**Node 环境**: 用户有 nvm-windows，版本包括 v20.15.1, v22.22.3, v24.14.0, v24.16.0

---

## 二、项目目录结构

```
xinxi_ai/
├── .gitignore
├── 心犀AI.md                          # 原始项目说明文档
├── HANDOVER_CONTEXT.md                # 本文件（上下文交接文档）
├── backend/
│   ├── .env                           # 环境变量（API Keys，不提交git）
│   ├── .env.example                   # 环境变量模板
│   ├── requirements.txt               # Python 依赖
│   ├── main.py                        # CLI 入口（命令行运行匹配）
│   ├── run.py                         # API 服务入口（FastAPI）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                     # FastAPI 应用工厂
│   │   ├── deps.py                    # 依赖注入（AppServices 单例）
│   │   ├── schemas.py                 # API 请求/响应 Pydantic 模型
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── users.py               # 用户 CRUD 路由
│   │       └── matching.py            # 匹配路由（HTTP + WebSocket）
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                # 配置管理（从 .env 读取）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── state.py               # LangGraph AgentState 定义
│   │   │   ├── nodes.py               # 5 个 Agent 节点函数
│   │   │   └── graph.py               # LangGraph StateGraph 构建
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   └── chroma_store.py        # ChromaDB 存储层
│   │   ├── embedding/
│   │   │   ├── __init__.py
│   │   │   └── embedding_service.py   # Embedding 服务封装
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user_profile.py        # 用户画像 Pydantic 模型
│   │   │   └── llm_outputs.py         # LLM 结构化输出 Pydantic 模型
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   └── hybrid_retriever.py    # 混合检索（硬过滤+向量搜索）
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── prompts.py             # 旧版 prompt（已被 ChatPromptTemplate 替代）
│   ├── data/
│   │   ├── __init__.py
│   │   └── mock_data.py               # 12 位模拟用户（6男6女）
│   ├── tests/
│   │   ├── test_api.py
│   │   └── test_pipeline.py
│   └── chroma_db/                     # ChromaDB 持久化目录（git忽略）
├── frontend/
│   ├── .gitignore
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── api/
│       │   └── client.js              # axios API 客户端
│       ├── components/
│       │   ├── Navbar.jsx
│       │   └── UserCard.jsx
│       └── pages/
│           ├── Home.jsx               # 用户浏览页
│           ├── UserDetail.jsx         # 用户详情 + WebSocket 匹配
│           ├── CreateUser.jsx         # 注册页
│           └── MatchHistory.jsx       # 匹配历史页
└── .venv/                             # Python 虚拟环境（git忽略）
```

---

## 三、环境配置（.env）

```env
# DeepSeek LLM
DEEPSEEK_API_KEY=sk-a2fce808f3c5418bac41fb1651dc2866
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0.7

# 硅基流动 Embedding
SILICONFLOW_API_KEY=sk-vptadpzccyqcljewxkrknxnwftabzpdzvpjdnzheqgrefbqh
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# Chroma
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=xinxi_users

# 匹配参数
MAX_RETRIEVAL_CANDIDATES=10
MAX_TOP_MATCHES=3
MATCH_THRESHOLD_SCORE=0.6
MAX_AGENT_LOOPS=3
```

---

## 四、核心架构

### 4.1 LangGraph 工作流拓扑

```
parse_intent → hybrid_search → post_analysis → [条件判断]
                                                    │
                ┌─── 满足阈值 ──→ generate_match → END
                │
                └─── 不满足 ──→ reflection → [检查循环次数]
                                                    │
                                  ┌── 未超限 ──→ hybrid_search（重试）
                                  └── 已超限 ──→ generate_match → END
```

### 4.2 AgentState 定义（TypedDict）

```python
class AgentState(TypedDict, total=False):
    user_profile: UserProfile
    hard_filters: dict
    rewritten_query: str
    candidates: list[dict]
    analysis_results: list[dict]
    best_score: float
    loop_count: int
    should_retry: bool
    retry_strategy: str        # relax_age / relax_city / rewrite_query
    new_query: Optional[str]
    top_matches: list[dict]
    match_letters: list[str]
    messages: list[str]
```

### 4.3 五个核心节点

1. **parse_intent** - LLM 意图解析，输出 `IntentParseResult`（hard_filters + rewritten_query）
2. **hybrid_search** - 混合检索（ChromaDB metadata 硬过滤 + 向量相似度搜索）
3. **post_analysis** - LLM 深度分析评分，输出 `AnalysisResultList`
4. **reflection** - LLM 反思失败原因+调整策略，输出 `ReflectionResult`
5. **generate_match** - LLM 撰写缘分推荐信（自由文本，非结构化输出）

### 4.4 关键技术模式

- **结构化输出**: `llm.with_structured_output(PydanticModel)` 替代手动 JSON 解析
- **ChatPromptTemplate**: 模板和数据分离管理 Prompt
- **混合检索 (Hybrid RAG)**: metadata 硬过滤 + 向量语义搜索
- **ChromaDB EmbeddingFunction 适配器**: 将 LangChain Embeddings 接口适配到 ChromaDB 1.x

### 4.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/users | 创建用户 |
| GET | /api/users | 用户列表（分页+筛选）|
| GET | /api/users/{user_id} | 用户详情 |
| PUT | /api/users/{user_id} | 更新用户 |
| DELETE | /api/users/{user_id} | 删除用户 |
| POST | /api/match | 触发匹配（同步HTTP）|
| WS | /api/match/ws/{user_id} | 触发匹配（WebSocket实时推送）|
| GET | /api/match/history/{user_id} | 匹配历史 |
| GET | /api/match/{match_id} | 单次匹配结果 |
| GET | /api/health | 健康检查 |

### 4.6 启动方式

```bash
# 后端（在 backend/ 目录下）
cd backend
../.venv/Scripts/python.exe run.py --port 8000 --reload

# 前端（在 frontend/ 目录下）
cd frontend
npx vite --port 5173
```

前端通过 Vite proxy 将 `/api` 请求代理到 `http://127.0.0.1:8000`。

---

## 五、任务进度

### Phase 1: 项目结构重构 ✅ 已完成
- 前后端分离：`backend/` 和 `frontend/` 独立目录
- 所有 import 路径从 `from src.` 更新为 `from core.`
- 后端从新位置验证运行正常

### Phase 2: LangChain 结构化输出 + ChatPromptTemplate ✅ 已完成
- 新增 `core/models/llm_outputs.py`（Pydantic 结构化输出模型）
- 重写 `core/agent/nodes.py`，所有 LLM 调用改用 `with_structured_output()` + `ChatPromptTemplate`
- 移除旧的 `_safe_json_parse()` 方法
- API 测试验证通过（阿杰92分, 大伟45分）

### Phase 3: Streaming + WebSocket 实时推送 ✅ 已完成

**实现内容：**
- WebSocket 端点 `@router.websocket("/ws/{user_id}")` 在 `/api/match/ws/{user_id}`
- 使用 `graph.astream_events(initial_state, version="v2")` 流式执行
- 实时推送事件：`start`, `node_start`, `node_end`, `complete`, `error`
- 前端 UserDetail.jsx 重写为 WebSocket 版本（进度条+实时日志）
- Vite proxy 代理规则 `/api/match/ws` → `http://127.0.0.1:8000`
- **已修复 Bug**：WebSocket 403（移除 CORSMiddleware，由 Vite proxy 处理跨域）
- **已修复 Bug**：DeepSeek V4 Flash thinking mode 不支持 `with_structured_output()`
  - 解决方案：`_invoke_structured()` + `_parse_json_response()` 手动解析 JSON + Pydantic 校验
  - nodes.py 升级到 v3：所有结构化输出节点改用手动 JSON 解析

**验证状态：**
- 直连 WebSocket 测试通过 ✅
- Vite 代理 WebSocket 测试通过 ✅
- 完整匹配流程端到端通过 ✅

### Phase 4: LangGraph Checkpointing 检查点持久化 ✅ 已完成

**实现内容：**
- `deps.py` 升级为 `SqliteSaver`（持久化到 `backend/data/checkpoints.db`）
- 保留 `MemorySaver` 选项（通过 `USE_SQLITE` 变量切换）
- 调用 `checkpointer.setup()` 初始化数据库表
- 每次匹配使用唯一 `thread_id`（格式：`match_{user_id}_{timestamp}`），避免重复运行冲突
- 访谈子图使用固定 `thread_id`（`interview_{user_id}`），支持跨会话继续
- 新增检查点状态查询端点 `GET /api/match/state/{user_id}`
- 新增 `langgraph-checkpoint-sqlite` 依赖

**验证状态：**
- SQLite 数据库创建成功 ✅
- Checkpoint 写入验证（6 个检查点对应 5 个节点 + 最终状态）✅
- 从 checkpoint 恢复完整状态（含 Agent 日志）✅

### Phase 5: 多 Agent 子图（用户访谈 Agent）✅ 已完成

**实现内容：**
- `core/agent/interview/` 子目录：state.py, graph.py, nodes.py
- InterviewState TypedDict（messages, draft_profile, missing_fields, is_complete, user_id）
- 访谈工作流：`parse_answer` → `generate_question` → END
- WebSocket 路由 `/api/interview/ws/{user_id}`
- 使用 `run_in_executor` 运行同步 `invoke`（兼容 SqliteSaver）
- Checkpointing 支持多轮对话状态持久化
- 访谈完成后自动更新 ChromaDB 用户画像
- InterviewExtraction Pydantic 模型（updated_fields, is_complete, analysis）

**验证状态：**
- 多轮对话测试通过（AI 提问 → 用户回答 → 画像提取 → 更新数据库）✅
- 检查点跨会话恢复测试通过 ✅

### Phase 6: Human-in-the-loop 用户反馈学习 ✅ 已完成

**实现内容：**
- `nodes.py` 新增 `human_feedback` 节点，使用 LangGraph `interrupt()` 暂停执行
- `graph.py` 升级为双模式：`HITL_ENABLED` 环境变量控制
  - HITL 模式：post_analysis → human_feedback → [approve/reject/adjust] → generate_match/reflection
  - Auto 模式（默认）：保持原始流程不变
- 新增 `_should_continue_after_feedback` 路由函数
- 反馈类型：approve（满意）、reject（不满意，触发反思重试）、adjust（具体调整意见）
- 通过 `Command(resume=feedback)` 恢复执行

**验证状态：**
- Graph 编译为 HITL 模式 ✅
- interrupt() 暂停执行验证（Next nodes: ('human_feedback',)）✅
- Command(resume=feedback) 恢复执行验证 ✅
- 非 HITL 模式仍然正常工作 ✅

### Phase 7: 匹配质量评估（LLM-as-Judge）✅ 已完成

**实现内容：**
- `core/evaluation/judge.py` 评估模块
- MatchEvaluation + MatchDimensionScore Pydantic 模型
- 5 个评估维度：相关性、契合度、解释力、一致性、温度感
- Judge Prompt 设计（低温度 0.2 确保评估稳定性）
- 评估端点 `POST /api/match/evaluate/{match_id}`
- 输出结构化评估报告（整体评分 + 各维度评分 + 优缺点 + 改进建议）

**验证状态：**
- 端到端评估测试通过（触发匹配 → 获取结果 → Judge 评估）✅
- 评估报告质量高（9/10 整体评分，5 维度详细点评）✅

---

## 六、当前代码最新状态

### 6.1 backend/api/app.py（CORS 已移除，由 Vite proxy 处理跨域）

```python
# CORSMiddleware 已移除
# 开发环境下，前端通过 Vite proxy 访问后端，不需要 CORS
# 生产环境部署时再加回
```

### 6.2 backend/api/deps.py（SqliteSaver 持久化）

```python
USE_SQLITE = True  # True = SqliteSaver, False = MemorySaver
# SqliteSaver 持久化到 backend/data/checkpoints.db
# 需要调用 checkpointer.setup() 初始化表
```

### 6.3 backend/core/agent/nodes.py（v3: 手动 JSON 解析）

```python
# 不再使用 with_structured_output()（DeepSeek thinking mode 不支持）
# 改用: Prompt 要求 JSON 输出 → _parse_json_response() 提取 → Pydantic 校验
# 新增 human_feedback 节点（Phase 6 HITL）
```

### 6.4 backend/core/agent/graph.py（v2: 含 HITL 双模式）

```python
# HITL_ENABLED 环境变量控制工作流模式
# HITL: post_analysis → human_feedback → [条件] → generate_match/reflection
# Auto: post_analysis → [条件] → generate_match/reflection
```

### 6.5 frontend/vite.config.js

```javascript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api/match/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### 6.6 新增文件

- `backend/core/evaluation/judge.py` - Phase 7 LLM-as-Judge 评估
- `backend/data/checkpoints.db` - Phase 4 SqliteSaver 持久化数据

---

## 七、已知问题和历史 Bug

1. **Vite 8 不兼容 Node 20.15.1**: Vite 8 需要 Node 20.19+。已降级到 Vite 6.x 解决。
2. **ChromaDB EmbeddingFunction 适配器**: ChromaDB 1.x 要求 `embedding_function` 继承 `EmbeddingFunction` 基类并实现 `__call__` + `name()` 方法。已通过 `_ChromaEmbeddingAdapter` 类解决。
3. **page_size 验证**: 用户列表接口 `le=50` 导致历史页空下拉，已改为 `le=200`。
4. **Windows nul 文件**: Windows 保留文件名 `nul` 导致 git add 失败，已删除。
5. **WebSocket 403 Bug**: 当前未解决，详见 Phase 3 状态。

---

## 八、模拟数据

12位预置用户（6男6女），ID 格式：
- 女：F001(小晴/杭州/INFP), F002(雨桐/上海/ENTJ), F003(阿月/成都/ESFP), F004(思远/北京/INTJ), F005(小薇/深圳/ISFP), F006(晓晓/杭州/ESTP)
- 男：M001(阿杰/杭州/INTP), M002(浩然/上海/ENTP), M003(小宇/成都/ENFP), M004(文博/北京/INFJ), M005(子轩/深圳/INFP), M006(大伟/杭州/ESTJ)

---

## 九、依赖版本（requirements.txt）

```
langchain>=1.3.0
langchain-openai>=1.3.0
langchain-community>=0.4.0
langgraph>=1.2.0
chromadb>=1.5.0
fastapi>=0.115.0
uvicorn>=0.30.0
httpx>=0.27.0
pydantic>=2.0
python-dotenv>=1.0
rich>=13.0
```

---

## 十、所有 Phase 已完成 — 后续扩展建议

所有 7 个 Phase（Phase 1-7）均已实现并通过验证。以下为后续扩展建议：

1. **生产化改进**
   - 将 `SqliteSaver` 升级为 `AsyncSqliteSaver`（支持 async 方法，避免阻塞事件循环）
   - 添加认证和权限控制
   - 添加 API 限流和错误监控

2. **前端完善**
   - 访谈子图的前端 UI（WebSocket 对话界面）
   - HITL 反馈面板（在匹配流程中暂停，等待用户审核候选人）
   - Phase 7 评估报告的可视化展示

3. **评估体系深化**
   - 构建标准评估数据集（手动标注的"最佳匹配"）
   - 批量评估和 A/B 测试不同 Prompt 策略
   - 追踪评估分数随时间的变化趋势

4. **高级特性**
   - 用户反馈的长期学习（将反馈数据用于优化 embedding 或 prompt）
   - 多 Agent 协作（匹配 Agent + 访谈 Agent + 评估 Agent 协同工作）
   - 匹配结果的个性化解释生成

5. **代码文件均包含详细中文注释和学习要点**，方便理解设计意图。
