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

from api.routers import users, matching, interview


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
    # CORS 说明（已移除 CORSMiddleware）
    # ============================================================
    # 学习要点：
    # Starlette 的 CORSMiddleware 会拦截没有合法 Origin 头的 WebSocket upgrade 请求，
    # 直接返回 403——这正是 Phase 3 WebSocket Bug 的根本原因。
    #
    # 解决方案（Option C）：
    # 开发环境下，前端通过 Vite proxy 访问后端（/api → http://127.0.0.1:8000），
    # Vite proxy 已经处理了跨域问题，不需要后端再加 CORS 头。
    # WebSocket 连接也走 Vite proxy，同样不需要后端 CORS。
    #
    # 生产环境部署时（前后端独立域名），再在此处添加 CORSMiddleware 即可：
    # from fastapi.middleware.cors import CORSMiddleware
    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["https://your-frontend-domain.com"],
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )

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
