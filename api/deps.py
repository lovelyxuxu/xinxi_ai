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
"""

import uuid
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.embedding.embedding_service import EmbeddingService
from src.database.chroma_store import ChromaStore
from src.retrieval.hybrid_retriever import HybridRetriever
from src.agent.graph import build_matching_graph
from src.models.user_profile import UserProfile
from data.mock_data import get_mock_users


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
        self.matching_graph = build_matching_graph(self.retriever)

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
