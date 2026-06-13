"""
心犀AI - 数据库初始化脚本
==========================
在 PostgreSQL 中创建所有 ORM 模型对应的表。

使用方式：
    cd backend
    python scripts/init_db.py

学习要点：
---------
- Base.metadata.create_all() 会根据 ORM 模型自动创建表
- 如果表已存在，不会重复创建（幂等操作）
- 生产环境应使用 Alembic 做迁移管理，这里简化处理
- psycopg3 驱动在 Windows 上比 asyncpg 更稳定
"""

import asyncio
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# 【学习要点】在导入 engine 之前，先覆盖连接参数，增加 connect_timeout
# 这能防止 Docker PG 启动较慢时连接超时
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://langfuse:langfuse@localhost:5432/langfuse")

from core.database.session import engine
from core.database.models import Base
from sqlalchemy import text


async def init_db():
    """创建所有数据库表"""
    print("=" * 50)
    print("心犀AI - 数据库初始化")
    print("=" * 50)
    print(f"  数据库: {engine.url}")

    # 【学习要点】使用 sorted_tables 确保外键依赖的表按正确顺序创建
    sorted_tables = Base.metadata.sorted_tables

    # 最多重试 3 次，每次间隔 2 秒
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                # 【学习要点】先创建 xinxi schema（如果不存在）
                # PostgreSQL 的 schema 类似命名空间，用于隔离不同应用的表
                # 我们的表放在 xinxi schema 下，避免与 LangFuse 的 public schema 冲突
                await conn.execute(
                    text("CREATE SCHEMA IF NOT EXISTS xinxi")
                )

                # 【学习要点】逐张表创建，确保外键依赖顺序正确
                # checkfirst=True 表示如果表已存在则跳过（幂等操作）
                for table in sorted_tables:
                    await conn.run_sync(
                        table.create, checkfirst=True
                    )

            print(f"  [OK] 所有表已创建（或已存在）")

            # 列出已创建的表
            table_names = [t.name for t in sorted_tables]
            print(f"  表清单: {', '.join(table_names)}")
            break  # 成功，跳出重试循环

        except Exception as e:
            print(f"  [Attempt {attempt}/{max_retries}] 连接失败: {e}")
            if attempt < max_retries:
                print(f"  2 秒后重试...")
                await asyncio.sleep(2)
            else:
                print("  [FAIL] 达到最大重试次数，请检查 PostgreSQL 是否正常运行")
                raise

    await engine.dispose()
    print("  [Done] 数据库连接已关闭")


if __name__ == "__main__":
    # 【学习要点】Windows 的 ProactorEventLoop 和某些异步库有兼容性问题
    # 切换到 SelectorEventLoop 可以提高兼容性
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
