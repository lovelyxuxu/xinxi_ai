"""
心犀AI - 异步数据库会话工厂
============================
使用 SQLAlchemy 2.0 异步引擎连接 PostgreSQL。

学习要点：
---------
- AsyncSession 是 SQLAlchemy 的异步会话，所有 DB 操作都用 await
- psycopg 是 PostgreSQL 官方驱动（psycopg3），Windows 兼容性比 asyncpg 好得多
- sessionmaker 创建会话工厂，每次请求生成独立的 session（事务隔离）
- asynccontextmanager 让 FastAPI 的 Depends() 可以用 async for 管理会话生命周期

关键设计：
  FastAPI 的每个请求 → get_db() → 生成一个 AsyncSession → 请求结束后自动关闭
  这确保了：
  1. 请求之间的数据隔离（每个请求有自己的事务）
  2. 连接池复用（不需要每次创建新连接）
  3. 异常自动回滚（出错时不会留下半成品数据）
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator
import os

# 【学习要点】
# DATABASE_URL 格式：postgresql+psycopg://user:password@host:port/dbname
# - postgresql+psycopg 告诉 SQLAlchemy 使用 psycopg3 驱动
# - psycopg3 比 asyncpg 在 Windows 上更稳定，同时性能也很优秀
# - 默认连接 LangFuse Docker 中的 PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://langfuse:langfuse@localhost:5433/langfuse",
)

# 创建异步引擎
# 【学习要点】
# - echo=False: 不打印 SQL 日志（生产环境）; 开发时可设为 True 调试
# - pool_size=5: 连接池大小（最多保持 5 个空闲连接）
# - max_overflow=10: 连接池满时最多额外创建 10 个临时连接
# - connect_args: psycopg 的连接参数
#   - connect_timeout: 防止 Docker PG 启动慢时超时
#   - options: 设置 search_path，让 SQL 查询默认在 xinxi schema 下查找表
#     这样写 SELECT * FROM users 就等价于 SELECT * FROM xinxi.users
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=5,
    max_overflow=10,
    connect_args={
        "connect_timeout": 10,
        "options": "-c search_path=xinxi,public",
    },
)

# 创建异步会话工厂
# 【学习要点】
# - expire_on_commit=False: 提交后不过期对象属性
#   （默认 True 会导致 commit 后访问属性时自动查询数据库，在异步模式下会报错）
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：为每个请求提供一个数据库会话。

    使用方式：
        @router.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            ...

    学习要点：
    - async generator（async for）模式：yield 之前的代码在请求开始时执行，
      yield 之后的代码在请求结束时执行（类似 try/finally）
    - 如果请求中发生异常，session 会自动回滚
    - 请求结束后 session 自动关闭，连接归还给连接池
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
