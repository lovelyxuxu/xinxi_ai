"""
心犀AI - API 服务启动入口
==========================
启动 FastAPI 服务，提供 HTTP 接口。

使用方式：
    python run.py                  # 默认 8000 端口
    python run.py --port 8080      # 指定端口
    python run.py --reload         # 开发模式（文件修改后自动重启）

启动后访问：
    http://localhost:8000/docs     # Swagger API 文档（自动生成！）
    http://localhost:8000/redoc    # ReDoc 格式的 API 文档
"""

import sys
import os
import argparse

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 编码修复
if sys.platform == "win32":
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="心犀AI API 服务")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发模式：文件修改后自动重启")
    args = parser.parse_args()

    print()
    print("=" * 55)
    print("  心犀AI API Server")
    print(f"  http://{args.host}:{args.port}")
    print(f"  API Docs: http://{args.host}:{args.port}/docs")
    print("=" * 55)
    print()

    import uvicorn
    uvicorn.run(
        "api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
