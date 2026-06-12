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
- MemorySaver: 纯内存，重启丢失（适合开发调试）
- SqliteSaver: 写入 SQLite 文件，重启保留（推荐生产使用）
- 切换方式：修改 USE_SQLITE 变量即可
"""

import uuid
import json
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from core.embedding.embedding_service import EmbeddingService
from core.database.chroma_store import ChromaStore
from core.retrieval.hybrid_retriever import HybridRetriever
from core.agent.graph import build_matching_graph
from core.agent.interview.graph import build_interview_graph
from core.models.user_profile import UserProfile
from data.mock_data import get_mock_users

# Phase 4: True = 使用 SqliteSaver（持久化到磁盘）, False = 使用 MemorySaver（纯内存）
USE_SQLITE = True
SQLITE_DB_PATH = Path(__file__).parent.parent / "data" / "checkpoints.db"


class AppServices:
    """
    应用级服务容器
    --------------
    在应用启动时初始化所有核心服务，并提供给各个路由使用。
    使用单例模式，确保全局只有一份实例。
    """

    _instance: Optional["AppServices"] = None

    def __init__(self):
        # 1. 核心服务初始化
        self.embedding_service = EmbeddingService()
        self.chroma_store = ChromaStore(self.embedding_service)
        self.retriever = HybridRetriever(self.chroma_store)
        
        # Phase 4: 初始化检查点持久化器
        # SqliteSaver 需要传入 sqlite3 连接，数据会持久化到磁盘
        # MemorySaver 纯内存，适合快速测试
        if USE_SQLITE:
            SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._sqlite_conn = sqlite3.connect(
                str(SQLITE_DB_PATH),
                check_same_thread=False,
            )
            self.checkpointer = SqliteSaver(self._sqlite_conn)
            self.checkpointer.setup()  # 创建必要的数据库表
            print(f"  [Phase 4] SqliteSaver initialized at {SQLITE_DB_PATH}")
        else:
            self.checkpointer = MemorySaver()
            self._sqlite_conn = None
            print("  [Phase 4] MemorySaver initialized (in-memory, volatile)")
        
        # 编译图时传入 checkpointer
        self.matching_graph = build_matching_graph(
            self.retriever, 
            checkpointer=self.checkpointer
        )

        # Phase 5: 初始化访谈子图
        self.interview_graph = build_interview_graph(
            checkpointer=self.checkpointer
        )

        # 2. 内存存储（后续可替换为数据库）
        # user_meta: 存储用户创建时间等 Chroma 不存储的额外信息
        self.user_meta: dict[str, dict] = {}
        # match_history: 匹配历史记录
        self.match_history: dict[str, list[dict]] = {}

        # 3. 导入模拟数据（如果数据库为空）
        if self.chroma_store.get_user_count() == 0:
            self._load_mock_data()

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
