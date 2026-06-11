"""
心犀AI - FastAPI 应用
======================
这是 HTTP 服务层的核心入口，负责：
1. 创建 FastAPI 应用实例
2. 注册路由（routers）
3. 配置 CORS（跨域资源共享，React 前端需要）
4. 提供健康检查接口

学习要点：
---------
- FastAPI 会自动生成 Swagger API 文档，访问 /docs 即可查看
- CORS 配置允许前端开发服务器（通常是 localhost:3000）跨域调用后端
- 路由通过 include_router 注册，每个模块独立管理自己的接口
- 工厂模式 create_app() 的好处：测试时可以创建独立的 app 实例
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import users, matching


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
        version="0.2.0",
    )

    # ============================================================
    # CORS 配置
    # ============================================================
    # 允许前端开发服务器跨域访问。
    # React 开发时默认端口是 3000 或 5173（Vite）。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",   # React dev server (CRA)
            "http://localhost:5173",   # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================================================
    # 注册路由
    # ============================================================
    app.include_router(users.router)
    app.include_router(matching.router)

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
