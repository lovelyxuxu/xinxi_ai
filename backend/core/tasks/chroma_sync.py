"""
心犀AI - ChromaDB 向量同步后台任务
====================================
当用户修改个人资料（about_me / ideal_partner / hobbies 等）时，
需要同步更新 ChromaDB 中的向量嵌入，以便后续匹配时使用最新数据。

学习要点：
---------
- FastAPI BackgroundTasks：在返回 HTTP 响应后，异步执行后台任务
  用法：def endpoint(background_tasks: BackgroundTasks):
           background_tasks.add_task(sync_user_vector, user_id=user_id)
  特点：不阻塞接口响应，用户立刻拿到结果，向量更新在后台静默完成

- 为什么需要同步向量？
  ChromaDB 存储的是用户文本的语义向量（1024 维浮点数组）。
  如果用户修改了 about_me，但 ChromaDB 中还是旧向量，
  那么匹配时语义搜索会基于过时数据——影响匹配质量。

- 同步时机（只在这些字段被修改时触发）：
  about_me / ideal_partner / hobbies / mbti —— 影响向量内容
  age / city / province / education / gender —— 影响 metadata filter

- 失败处理：
  同步失败只记录日志，不影响主流程
  用户已收到成功的 API 响应，向量会在下次调用时重试
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 这些字段被修改时需要触发 ChromaDB 同步
VECTOR_FIELDS = {
    "about_me", "ideal_partner", "hobbies", "mbti",
    "age", "city", "province", "education", "gender",
    "annual_income", "marital_status",
}


async def sync_user_vector(user_id: str, user=None) -> None:
    """
    将用户资料同步到 ChromaDB。

    参数:
        user_id: 用户业务 ID（如 "U1A2B3C4"）
        user: SQLAlchemy User 对象（如果已查好，直接传入避免重复查询）

    流程:
        1. 如果没传 user 对象，从 PostgreSQL 查询
        2. 将 User ORM 对象转换为 UserProfile 领域模型
        3. 调用 ChromaStore.upsert_user() 更新向量和 metadata

    学习要点：
    - 这是一个 async 函数，被 BackgroundTasks 调度时以协程方式运行
    - 懒加载导入（在函数内部 import）避免模块循环依赖
    - try/except 确保同步失败不影响主流程
    """
    try:
        # 懒加载导入，避免循环依赖
        from api.deps import get_services
        from core.models.user_profile import UserProfile

        if user is None:
            # 如果没有传入 user 对象，从数据库查
            from core.database.session import AsyncSessionLocal
            from core.database.models import User
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"[ChromaSync] 用户 {user_id} 不存在，跳过同步")
            return

        # 将 SQLAlchemy User 模型转换为 UserProfile 领域模型
        # UserProfile 是 ChromaStore 期望的数据格式
        user_profile = UserProfile(
            user_id=user.user_id,
            nickname=user.nickname,
            gender=user.gender,
            age=user.age,
            city=user.city,
            province=user.province,
            education=user.education,
            annual_income=user.annual_income or "未填写",
            marital_status=user.marital_status or "未婚",
            target_gender=user.target_gender,
            target_age_min=user.target_age_min,
            target_age_max=user.target_age_max,
            target_city=user.target_city or "不限",
            about_me=user.about_me or "",
            ideal_partner=user.ideal_partner or "",
            hobbies=user.hobbies or "",
            mbti=user.mbti or "未知",
        )

        # 获取 ChromaStore 实例并同步
        svc = get_services()
        svc.chroma_store.upsert_user(user_profile)

        logger.info(f"[ChromaSync] 用户 {user_id} 向量同步完成")

    except Exception as e:
        # 同步失败只记录日志，不抛出异常（不影响主请求）
        logger.error(f"[ChromaSync] 用户 {user_id} 向量同步失败: {e}", exc_info=True)
