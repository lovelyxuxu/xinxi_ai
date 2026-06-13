"""
心犀AI - FastAPI 应用
======================
HTTP 服务层的核心入口，负责：
1. 创建 FastAPI 应用实例
2. 注册路由（routers）
3. 配置 CORS（跨域资源共享）
4. 提供健康检查接口
5. 应用启动时初始化 AsyncSqliteSaver + 验证 PostgreSQL 连接

学习要点：
---------
- 工厂模式 create_app() 的好处：测试时可以创建独立的 app 实例
- lifespan 上下文管理器替代了旧版的 @app.on_event("startup")
- CORS 配置允许前端 (localhost:5173) 发送带 Authorization 头的请求
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import users, matching, interview, auth
from api.routers.fate import router as fate_router
from api.routers.notifications import router as notifications_router

# 上传文件目录（相对于 backend/ 目录）
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器。

    学习要点：
    ---------
    FastAPI 的 lifespan 是一个异步上下文管理器：
    - yield 之前的代码在应用启动时执行（相当于 startup 事件）
    - yield 之后的代码在应用关闭时执行（相当于 shutdown 事件）
    - 比 @app.on_event("startup") 更现代，是推荐的写法

    启动时做两件事：
    1. 初始化 AsyncSqliteSaver（LangGraph 检查点持久化）
    2. 验证 PostgreSQL 连接（如果配置了 DATABASE_URL）
    """
    # === Startup ===
    from api.deps import get_services
    svc = get_services()
    await svc.setup_checkpointer()
    print("  [Startup] LangGraph checkpointer initialized")

    # 验证 PostgreSQL 连接（v2 新增）
    try:
        from core.database.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        print("  [Startup] PostgreSQL connection verified")
    except Exception as e:
        print(f"  [Startup] PostgreSQL connection failed: {e}")
        print("  [Startup] Auth features may not work. Check DATABASE_URL in .env")

    yield  # 应用运行中...

    # === Shutdown ===
    # 关闭数据库连接池
    try:
        from core.database.session import engine
        await engine.dispose()
        print("  [Shutdown] Database connections closed")
    except Exception:
        pass
    print("  [Shutdown] Application shutting down")


def create_app() -> FastAPI:
    """
    FastAPI 应用工厂函数。
    使用工厂模式：每次调用创建一个新的 app 实例，方便测试隔离。
    """
    app = FastAPI(
        title="心犀AI - 智能婚恋匹配系统 API",
        description=(
            "基于 Agent + Hybrid RAG 的新一代婚恋匹配系统。\n\n"
            "技术栈：LangChain + LangGraph + DeepSeek V4 Flash + ChromaDB + FastAPI"
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    # ============================================================
    # CORS 配置（跨域资源共享）
    # ============================================================
    # 【学习要点】
    # 开发环境下，前端 (localhost:5173) 和后端 (localhost:8000) 端口不同，
    # 浏览器会执行"同源策略"限制。CORS 告诉浏览器"允许前端访问后端"。
    #
    # - allow_origins: 允许的前端地址列表
    # - allow_credentials=True: 允许前端发送 Cookie / Authorization 头
    #   （JWT 认证必须开启这个！否则浏览器不会带上 Token）
    # - allow_methods=["*"]: 允许所有 HTTP 方法（GET/POST/PUT/DELETE/OPTIONS）
    # - allow_headers=["*"]: 允许所有请求头
    #
    # Vite proxy 在开发环境下也能工作，但显式配置 CORS 更可靠，
    # 尤其是 WebSocket 连接和某些浏览器的行为。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # LangFuse Web UI
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================================================
    # 注册路由
    # ============================================================
    app.include_router(auth.router)         # v2: 认证路由（注册/登录/JWT）
    app.include_router(users.router)
    app.include_router(matching.router)
    app.include_router(interview.router)
    app.include_router(fate_router)         # v3: 心动清单 + 缘分分析
    app.include_router(notifications_router)  # v3: 通知系统

    # ============================================================
    # 静态文件托管（用户上传的图片）
    # ============================================================
    # 【学习要点】
    # StaticFiles 让 FastAPI 直接托管静态文件，无需 Nginx。
    # 访问路径：http://localhost:8000/uploads/avatars/{filename}
    # 对于生产环境，应该改用 Nginx 或 CDN 托管静态文件（性能更好）。
    # 这里用于开发和学习目的。
    os.makedirs(os.path.join(UPLOADS_DIR, "avatars"), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, "photos"), exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

    # ============================================================
    # 健康检查接口
    # ============================================================
    @app.get("/api/health", tags=["系统"])
    def health_check():
        """健康检查：确认服务正常运行，依赖服务就绪"""
        from api.deps import get_services
        svc = get_services()
        user_count = svc.chroma_store.get_user_count()
        return {
            "status": "ok",
            "service": "xinxi-ai",
            "user_count": user_count,
        }

    return app
