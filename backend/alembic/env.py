"""
XinXi AI - Alembic Async Migration Environment

This is the entry point for Alembic migrations.
It loads ORM models from core.database.models and compares
them against the database to generate/apply migration scripts.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ORM Base class (contains all table metadata)
from core.database.models import Base

# Load .env file
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Alembic Config object
config = context.config

# Override database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://langfuse:langfuse@localhost:5433/langfuse",
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script only, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="xinxi",
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """只处理 xinxi schema 的对象，忽略其他 schema（如 public、langfuse）。

    学习要点：
    - include_object 是 Alembic autogenerate 的过滤钩子
    - 当数据库中有多个 schema 时，需要告诉 Alembic "只看我们的 schema"
    - 不加这个过滤器，会把 LangFuse 的 public schema 表也当成 diff 对象处理
    """
    # 只处理属于 xinxi schema 的表
    if type_ == "table":
        schema = getattr(object, "schema", None)
        return schema == "xinxi"
    return True


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations on an existing connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="xinxi",
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "connect_timeout": 10,
            "options": "-c search_path=xinxi,public",
        },
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB and apply).

    Windows fix: psycopg3 requires SelectorEventLoop, not ProactorEventLoop.
    """
    import selectors
    selector = selectors.SelectSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_async_migrations())
    loop.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
