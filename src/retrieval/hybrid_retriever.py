"""
心犀AI - 混合检索模块
======================
实现"硬性过滤 + 语义检索"的混合搜索策略。

学习要点：
---------
混合检索 (Hybrid Retrieval) 是 RAG 系统的核心技术之一：
  1. 硬性过滤（Pre-filtering）：用元数据条件做精确筛选，如性别、年龄范围、城市
     → 类似 SQL 的 WHERE 子句，100% 精确，不满足条件的候选人直接排除
  2. 语义检索（Semantic Search）：在过滤后的候选集中，用向量相似度排序
     → 捕捉"三观契合、兴趣相似"等软性语义

这种组合确保了：
  - 硬性条件绝对准确（不会出现性别、年龄不对的推荐）
  - 软性匹配有深度（能理解"性格温和""喜欢安静"等模糊描述）
"""

from typing import Optional
from src.database.chroma_store import ChromaStore
from src.models.user_profile import UserProfile


class HybridRetriever:
    """
    混合检索器
    ----------
    封装了从"构建过滤条件"到"执行检索"的完整流程。
    """

    def __init__(self, chroma_store: ChromaStore):
        """
        参数:
            chroma_store: Chroma 数据库存储实例
        """
        self.store = chroma_store

    def build_where_filter(self, user: UserProfile, relaxed: bool = False) -> Optional[dict]:
        """
        根据用户的择偶要求，构建 Chroma 的 where 过滤条件。

        这是"硬性过滤"的核心逻辑！

        参数:
            user: 当前用户的画像
            relaxed: 是否放宽条件（Agent 反思循环中使用）
                     True 时会放松年龄范围和城市限制

        返回:
            Chroma 格式的 where 过滤字典，或 None（如果没有过滤条件）
        """
        filters = []

        # 条件1: 对方性别（始终严格执行，这是最基本的一票否决）
        # Chroma 的 where 语法：{"字段名": "值"} 表示精确匹配
        filters.append({"gender": user.target_gender})

        # 条件2: 年龄范围
        if relaxed:
            # 放宽模式：年龄范围各扩展 3 岁
            age_min = max(18, user.target_age_min - 3)
            age_max = user.target_age_max + 3
        else:
            age_min = user.target_age_min
            age_max = user.target_age_max

        filters.append({"age": {"$gte": age_min}})
        filters.append({"age": {"$lte": age_max}})

        # 条件3: 城市/地域
        if not relaxed and user.target_city and user.target_city != "不限":
            # 严格模式：同城过滤
            filters.append({"city": user.target_city})
        elif relaxed:
            # 放宽模式：同省过滤（或完全不限）
            if user.target_city and user.target_city != "不限":
                filters.append({"province": user.province})
            # 如果用户本身就不限城市，则不加地域过滤

        # 排除自己（不能推荐自己给自己）
        filters.append({"user_id": {"$ne": user.user_id}})

        # 组合所有条件：使用 $and 逻辑
        # 注意：Chroma 的 $and 语法需要特殊处理
        # 当只有一个条件时，直接返回该条件即可
        if len(filters) == 1:
            return filters[0]

        # Chroma where 子句需要合并为嵌套 $and
        return {"$and": filters}

    def retrieve(
        self,
        user: UserProfile,
        query_text: str,
        n_results: int = 10,
        relaxed: bool = False,
    ) -> list[dict]:
        """
        执行混合检索。

        流程:
        1. 根据用户的择偶要求构建硬性过滤条件
        2. 用过滤条件 + 查询文本在 Chroma 中检索
        3. 返回结构化的候选人列表

        参数:
            user: 当前用户画像
            query_text: 查询文本（可以是用户原始描述，也可以被 LLM 重写后）
            n_results: 返回的候选人数量
            relaxed: 是否放宽硬性条件

        返回:
            候选人列表，每个元素包含 user_id, metadata, document, distance
        """
        # 构建过滤条件
        where_filter = self.build_where_filter(user, relaxed=relaxed)

        # 执行检索
        results = self.store.search(
            query_text=query_text,
            n_results=n_results,
            where_filter=where_filter,
        )

        # 将 Chroma 的返回结果整理为候选人列表
        candidates = []
        if results and results["ids"] and results["ids"][0]:
            for i, candidate_id in enumerate(results["ids"][0]):
                candidate = {
                    "user_id": candidate_id,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                }
                candidates.append(candidate)

        return candidates
