# 心犀AI - 启动与运维手册

## 项目结构速览

```
xinxi_ai/
├── docker-compose.yml          ← LangFuse 容器编排
├── backend/
│   ├── run.py                  ← API 服务启动入口
│   ├── main.py                 ← CLI 单次匹配（调试用）
│   ├── .env                    ← 环境变量配置
│   └── requirements.txt        ← Python 依赖
└── frontend/
    └── (React + TypeScript)
```

## 日常启动流程

### 第一步：启动 LangFuse（如果还没启动）

在项目根目录 `xinxi_ai/` 下运行：

```bash
docker compose up -d
```

等待约 30 秒，验证容器状态：

```bash
docker compose ps
```

看到 `xinxi-langfuse-web` 和 `xinxi-langfuse-db` 都是 `Up` 状态就对了。

LangFuse Dashboard 地址：http://localhost:3000

### 第二步：启动后端 API 服务

进入 `backend/` 目录：

```bash
cd E:\study\python\xinxi_ai\backend
python run.py
```

看到以下输出表示启动成功：

```
=======================================================
  心犀AI API Server
  http://127.0.0.1:8000
  API Docs: http://127.0.0.1:8000/docs
=======================================================

  [Phase 2] Using Supervisor multi-agent graph
  [Supervisor] Graph compiled with Rule-based router
  [Phase 4] AsyncSqliteSaver initialized at ...
  [Startup] All services initialized
```

开发模式（文件修改后自动重启）：

```bash
python run.py --reload
```

验证服务：访问 http://localhost:8000/api/health，应该看到：

```json
{"status":"ok","service":"xinxi-ai","user_count":13}
```

### 第三步：启动前端（如需要）

进入 `frontend/` 目录：

```bash
cd E:\study\python\xinxi_ai\frontend
npm run dev
```

前端默认运行在 http://localhost:5173

## 常用命令速查

| 操作 | 命令 |
|------|------|
| 启动 LangFuse | `docker compose up -d` |
| 停止 LangFuse | `docker compose down` |
| 启动后端 | `cd backend && python run.py` |
| 启动后端（开发模式） | `cd backend && python run.py --reload` |
| 启动后端（自定义端口） | `cd backend && python run.py --port 8080` |
| 启动前端 | `cd frontend && npm run dev` |
| CLI 单次匹配测试 | `cd backend && python main.py --user F001` |
| 安装 Python 依赖 | `cd backend && pip install -r requirements.txt` |
| 安装前端依赖 | `cd frontend && npm install` |
| 查看 LangFuse 日志 | `docker compose logs -f langfuse-web` |

## 关键配置文件

### backend/.env

核心配置项一览：

```env
# LLM（DeepSeek V4 Flash）
DEEPSEEK_API_KEY=sk-xxx
LLM_MODEL=deepseek-v4-flash

# Embedding（硅基流动 bge-m3）
SILICONFLOW_API_KEY=sk-xxx

# Supervisor 架构开关
USE_SUPERVISOR=true
SUPERVISOR_ROUTER=rule

# LangFuse 可观测性
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
```

- `USE_SUPERVISOR=false` 可切换回旧版单 Agent 图（对比学习用）
- `SUPERVISOR_ROUTER=llm` 可切换为 LLM 版路由（更灵活但不稳定）
- `LANGFUSE_ENABLED=false` 关闭追踪（LangFuse 不可用时自动降级）

## 验证 LangFuse 追踪

1. 确保 `.env` 中 `LANGFUSE_ENABLED=true` 且 API Key 已填写
2. 启动后端和前端
3. 在前端触发一次匹配
4. 打开 http://localhost:3000，进入 Traces 页面
5. 应该能看到一条新的 trace，点击展开查看每个 Agent 的执行详情

如果看不到 trace：
- 检查 Docker 容器是否在运行
- 检查 `.env` 中的 API Key 是否正确
- 查看后端终端是否有 `[LangFuse]` 开头的日志

## 常见问题

### 端口被占用

如果 8000 端口被占用，换一个端口：

```bash
python run.py --port 8081
```

### 依赖缺失

```bash
cd backend
pip install -r requirements.txt
```

### Docker 启动失败

确保 Docker Desktop 正在运行。Windows 上可以从开始菜单启动 Docker Desktop。

### 数据库重置

删除 `backend/data/checkpoints.db` 可以重置检查点数据。
删除 `backend/chroma_db/` 可以重置向量数据库（下次启动会重新导入模拟数据）。

## 完整重启步骤（从零开始）

```bash
# 1. 启动 LangFuse
cd E:\study\python\xinxi_ai
docker compose up -d

# 2. 启动后端
cd backend
python run.py --reload

# 3. 新开一个终端，启动前端
cd E:\study\python\xinxi_ai\frontend
npm run dev
```

打开浏览器：
- 前端页面：http://localhost:5173
- API 文档：http://localhost:8000/docs
- LangFuse Dashboard：http://localhost:3000
