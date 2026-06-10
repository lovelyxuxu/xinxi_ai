"""
心犀AI - Chroma 向量数据库存储层
==================================
封装 Chroma 数据库的增删改查操作。

学习要点：
---------
- Chroma 是一个轻量级的向量数据库，用 pip install chromadb 即可安装
- 数据以 "Collection"（集合）为单位组织，类似关系数据库中的"表"
- 每条记录包含：文档文本（document）、元数据（metadata）、向量（embedding）
- Chroma 支持 metadata 过滤 + 向量相似度的混合查询

数据流：
  用户文本 → 硅基流动 bge-m3 API → 1024维向量 → 存入 Chroma
  用户元数据 → 直接存入 Chroma 的 metadata 字段
"""

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from typing import Optional

from config.settings import chroma_config
from src.embedding.embedding_service import EmbeddingService
from src.models.user_profile import UserProfile


class _ChromaEmbeddingAdapter(EmbeddingFunction):
    """
    适配器：将 LangChain 的 Embeddings 接口转换为 ChromaDB 期望的接口。

    学习要点：
    - ChromaDB 1.x 要求 embedding_function 继承 EmbeddingFunction 基类
    - 必须实现 __call__ 和 name() 方法
    - 这是设计模式中经典的 Adapter 模式
    """

    def __init__(self, embedding_service: EmbeddingService):
        self._service = embedding_service

    def __call__(self, input: Documents) -> Embeddings:
        """ChromaDB 会调用这个方法来获取文本的向量表示"""
        return self._service.embed_texts(list(input))

    def name(self) -> str:
        """返回 Embedding 函数的名称，ChromaDB 用于校验一致性"""
        return "siliconflow_bge_m3"


class ChromaStore:
    """
    Chroma 向量数据库操作封装
    --------------------------
    提供用户数据的存入、更新、查询等操作。
    使用硅基流动的 bge-m3 模型做 Embedding，而非 ChromaDB 默认模型。
    """

    def __init__(self, embedding_service: EmbeddingService):
        """
        初始化 Chroma 客户端和集合。

        参数:
            embedding_service: Embedding 服务实例
                              Chroma 会通过它自动将文档转为向量
        """
        self.embedding_service = embedding_service

        # 创建适配器，让 ChromaDB 能调用我们的 Embedding 服务
        self._embedding_fn = _ChromaEmbeddingAdapter(embedding_service)

        # 创建 Chroma 持久化客户端
        # persistent_client 会把数据存到磁盘，重启后数据不丢失
        self.client = chromadb.PersistentClient(
            path=chroma_config.persist_dir,
        )

        # 获取或创建 Collection
        # 关键：传入 embedding_function，让 Chroma 使用 bge-m3 而不是默认模型
        self.collection = self.client.get_or_create_collection(
            name=chroma_config.collection_name,
            metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
            embedding_function=self._embedding_fn,
        )

    def upsert_user(self, user: UserProfile) -> None:
        """
        存入或更新一个用户的数据（UPSERT = UPdate or inSERT）。

        核心逻辑：
        1. 将用户的文本描述拼接成一段完整文本（profile_text）
        2. 提取用户的结构化元数据（metadata）
        3. Chroma 自动调用 bge-m3 将 profile_text 转为 1024 维向量
        4. 如果 user_id 已存在则更新，不存在则新增

        参数:
            user: 用户画像对象
        """
        profile_text = user.get_profile_text()
        metadata = user.get_metadata()

        # about_me 和 ideal_partner 也单独存一份在 metadata 里
        # 方便后续 LLM 后分析时直接取用
        metadata["about_me"] = user.about_me
        metadata["ideal_partner"] = user.ideal_partner

        self.collection.upsert(
            ids=[user.user_id],
            documents=[profile_text],
            metadatas=[metadata],
        )

    def upsert_users(self, users: list[UserProfile]) -> None:
        """批量存入/更新多个用户"""
        for user in users:
            self.upsert_user(user)

    def search(
        self,
        query_text: str,
        n_results: int = 10,
        where_filter: Optional[dict] = None,
    ) -> dict:
        """
        混合检索：元数据过滤 + 向量相似度搜索。

        这是整个系统的核心查询方法！

        执行流程：
        1. Chroma 先用 where_filter 过滤掉不符合硬性条件的用户
        2. 在剩余用户中，用 bge-m3 将 query_text 转为向量，做相似度计算
        3. 返回最相似的 n_results 个结果

        参数:
            query_text: 查询文本（会被 bge-m3 自动转为向量）
            n_results: 返回结果数量
            where_filter: Chroma 格式的元数据过滤条件

        返回:
            Chroma 的查询结果字典，包含 ids, documents, metadatas, distances
        """
        query_params = {
            "query_texts": [query_text],
            "n_results": n_results,
        }

        # 如果有硬性过滤条件，加入查询参数
        if where_filter:
            query_params["where"] = where_filter

        results = self.collection.query(**query_params)
        return results

    def get_user_count(self) -> int:
        """获取当前 Collection 中的用户数量"""
        return self.collection.count()

    def get_user(self, user_id: str) -> Optional[dict]:
        """根据 user_id 获取单个用户的完整数据"""
        result = self.collection.get(ids=[user_id])
        if result and result["ids"]:
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result["documents"] else None,
                "metadata": result["metadatas"][0] if result["metadatas"] else None,
            }
        return None

    def clear_collection(self) -> None:
        """清空当前集合（谨慎使用，仅用于开发调试）"""
        self.client.delete_collection(chroma_config.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=chroma_config.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self._embedding_fn,
        )
