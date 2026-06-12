"""
心犀AI - FastAPI 应用
======================
这是 HTTP 服务层的核心入口，负责：
1. 创建 FastAPI 应用实例
2. 注册路由（routers）
3. 配置 CORS（跨域资源共享，React 前端需要）
4. 提供健康检查接口
5. 应用启动时异步初始化 AsyncSqliteSaver

学习要点：
---------
- FastAPI 会自动生成 Swagger API 文档，访问 /docs 即可查看
- 路由通过 include_router 注册，每个模块独立管理自己的接口
- 工厂模式 create_app() 的好处：测试时可以创建独立的 app 实例
- startup 事件用于异步初始化（如 AsyncSqliteSaver 的数据库连接）
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.routers import users, matching, interview


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

    这里我们用它来异步初始化 AsyncSqliteSaver，
    因为 AsyncSqliteSaver 的数据库连接创建是异步操作。
    """
    # === Startup ===
    from api.deps import get_services
    svc = get_services()
    await svc.setup_checkpointer()
    print("  [Startup] All services initialized")

    yield  # 应用运行中...

    # === Shutdown ===
    # 可以在这里做清理工作（如关闭数据库连接）
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
        version="0.3.0",
        lifespan=lifespan,
    )

    # ============================================================
    # CORS 说明（已移除 CORSMiddleware）
    # ============================================================
    # 开发环境下，前端通过 Vite proxy 访问后端，不需要 CORS。
    # WebSocket 连接也走 Vite proxy，同样不需要后端 CORS。
    # 生产环境部署时再添加 CORSMiddleware。

    # ============================================================
    # 注册路由
    # ============================================================
    app.include_router(users.router)
    app.include_router(matching.router)
    app.include_router(interview.router)

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
