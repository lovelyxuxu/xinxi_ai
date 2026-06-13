"""
XinXi AI - API Server Entry Point
==================================

Usage:
    python run.py                  # Default port 8000
    python run.py --port 8080      # Custom port
    python run.py --reload         # Dev mode (auto-restart on file changes)

After startup:
    http://localhost:8000/docs     # Swagger API docs
    http://localhost:8000/redoc    # ReDoc docs
"""

import sys
import os
import argparse

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows encoding fix
if sys.platform == "win32":
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="XinXi AI API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Listen address")
    parser.add_argument("--port", type=int, default=8000, help="Listen port")
    parser.add_argument("--reload", action="store_true", help="Dev mode: auto-restart on changes")
    args = parser.parse_args()

    print()
    print("=" * 55)
    print("  XinXi AI API Server")
    print(f"  http://{args.host}:{args.port}")
    print(f"  API Docs: http://{args.host}:{args.port}/docs")
    print("=" * 55)
    print()

    # ================================================================
    # Windows Event Loop Fix for psycopg3
    # ================================================================
    # psycopg3 (PostgreSQL async driver) is NOT compatible with
    # ProactorEventLoop on Windows. We must use SelectorEventLoop.
    #
    # uvicorn.run() internally calls asyncio.run(), which on Windows
    # creates a ProactorEventLoop. To fix this, we:
    # 1. Set the event loop policy to WindowsSelectorEventLoopPolicy
    # 2. Use uvicorn.Config + uvicorn.Server directly for full control
    # 3. Manually create and set a SelectorEventLoop before server.run()
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import uvicorn

    config = uvicorn.Config(
        app="api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

    server = uvicorn.Server(config)

    if sys.platform == "win32":
        # On Windows, create a SelectorEventLoop explicitly
        # and set it as the current loop before starting the server
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.serve())
        finally:
            loop.close()
    else:
        # On macOS/Linux, uvicorn's default loop handling works fine
        server.run()


if __name__ == "__main__":
    main()
