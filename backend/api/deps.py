"""
心犀AI - API 依赖注入
======================
FastAPI 的依赖注入系统让共享服务（如数据库连接、Embedding 服务）
只在应用启动时初始化一次，然后注入到每个路由处理函数中。

学习要点：
---------
- FastAPI 用 Depends() 实现依赖注入，类似 Spring 的 @Autowired
- 好处：路由函数不需要关心服务怎么创建，直接用就行
- 全局单例：Embedding、ChromaStore 这些重量级服务只初始化一次

Phase 4 检查点持久化：
---------------------
- MemorySaver: 纯内存，支持同步和异步（默认）
- AsyncSqliteSaver: 异步 SQLite，支持 astream_events/ainvoke
- SqliteSaver: 同步 SQLite，不支持异步方法（会导致 WebSocket 报错）

关键教训：
  LangGraph 的 astream_events() 和 ainvoke() 是异步方法，
  要求 checkpointer 也支持异步（aget/aput 等方法）。
  SqliteSaver 只支持同步方法，用在异步上下文中会报：
  "The SqliteSaver does not support async methods"
  解决方案：使用 AsyncSqliteSaver（基于 aiosqlite）。

Phase 2 多 Agent 架构：
---------------------
- USE_SUPERVISOR=True 时使用 Supervisor 多 Agent 图
- USE_SUPERVISOR=False 时使用旧版单 Agent 图（便于对比学习）
"""

import uuid
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver

from core.embedding.embedding_service import EmbeddingService
from core.database.chroma_store import ChromaStore
from core.retrieval.hybrid_retriever import HybridRetriever

# 导入新旧两种图构建器
from core.agent.graph import build_matching_graph as build_legacy_graph
from core.agents.supervisor.graph import build_supervisor_graph
from core.agent.interview.graph import build_interview_graph
from core.models.user_profile import UserProfile
from config.settings import supervisor_config
from data.mock_data import get_mock_users

# Phase 4: True = 使用 AsyncSqliteSaver（持久化到磁盘）, False = 使用 MemorySaver（纯内存）
USE_SQLITE = True
SQLITE_DB_PATH = Path(__file__).parent.parent / "data" / "checkpoints.db"


class AppServices:
    """
    应用级服务容器
    --------------
    在应用启动时初始化所有核心服务，并提供给各个路由使用。
    使用单例模式，确保全局只有一份实例。

    注意：checkpointer 需要通过 setup_checkpointer() 异步初始化，
    因为 AsyncSqliteSaver 需要异步创建数据库连接。
    """

    _instance: Optional["AppServices"] = None

    def __init__(self):
        # 1. 核心服务初始化
        self.embedding_service = EmbeddingService()
        self.chroma_store = ChromaStore(self.embedding_service)
        self.retriever = HybridRetriever(self.chroma_store)

        # Phase 4: 先用 MemorySaver 占位，后续由 setup_checkpointer() 替换
        self.checkpointer = MemorySaver()

        # Phase 2: 根据配置选择图架构
        self.matching_graph = self._build_graph(checkpointer=self.checkpointer)

        # Phase 5: 初始化访谈子图
        self.interview_graph = build_interview_graph(
            checkpointer=self.checkpointer
        )

        # 2. 内存存储（后续可替换为数据库）
        self.user_meta: dict[str, dict] = {}
        self.match_history: dict[str, list[dict]] = {}

        # 3. 导入模拟数据（如果数据库为空）
        if self.chroma_store.get_user_count() == 0:
            self._load_mock_data()

    def _build_graph(self, checkpointer=None):
        """
        根据配置构建匹配图。

        学习要点：
        - 工厂方法模式：封装图构建的决策逻辑
        - 向后兼容：旧的图代码保留不动，通过开关切换
        """
        if supervisor_config.use_supervisor:
            print("  [Phase 2] Using Supervisor multi-agent graph")
            return build_supervisor_graph(self.retriever, checkpointer=checkpointer)
        else:
            print("  [Phase 2] Using legacy single-agent graph")
            return build_legacy_graph(self.retriever, checkpointer=checkpointer)

    async def setup_checkpointer(self):
        """
        异步初始化 checkpointer（必须在 FastAPI startup 事件中调用）。

        学习要点：
        AsyncSqliteSaver 基于 aiosqlite，连接创建是异步操作，
        所以不能在 __init__()（同步方法）中初始化。
        FastAPI 的 lifespan/startup 事件支持异步，正好用来做这件事。
        """
        if USE_SQLITE:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._aiosqlite_conn = await aiosqlite.connect(str(SQLITE_DB_PATH))
            self.checkpointer = AsyncSqliteSaver(self._aiosqlite_conn)
            await self.checkpointer.setup()

            # 用新的 checkpointer 重新编译图
            self.matching_graph = self._build_graph(checkpointer=self.checkpointer)
            self.interview_graph = build_interview_graph(
                checkpointer=self.checkpointer
            )
            print(f"  [Phase 4] AsyncSqliteSaver initialized at {SQLITE_DB_PATH}")
        else:
            print("  [Phase 4] MemorySaver initialized (in-memory, volatile)")

    def _load_mock_data(self):
        """加载模拟数据到 Chroma 数据库"""
        mock_users = get_mock_users()
        self.chroma_store.upsert_users(mock_users)
        now = datetime.now().isoformat()
        for u in mock_users:
            self.user_meta[u.user_id] = {"created_at": now}

    @classmethod
    def get_instance(cls) -> "AppServices":
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_services() -> AppServices:
    """FastAPI 依赖注入函数：返回全局服务实例"""
    return AppServices.get_instance()


def generate_user_id() -> str:
    """生成唯一的用户ID（格式：U + 8位随机字符）"""
    return "U" + uuid.uuid4().hex[:8].upper()


def generate_match_id() -> str:
    """生成唯一的匹配记录ID"""
    return "M" + uuid.uuid4().hex[:8].upper()
