"""
心犀AI - 用户发现路由（v2 PostgreSQL 版）
==========================================
提供用户发现列表和公开主页接口。

学习要点：
---------
- GET /api/users: 支持分页 + 性别/城市/年龄筛选，用于首页发现页
- GET /api/users/{user_id}: 用户公开主页（不暴露私密信息）
- 两个接口不需要强制登录（公开资源），未来可加可选鉴权
- 与旧版 users.py 的区别：从 ChromaDB 改为 PostgreSQL 查询
  ChromaDB 专门用于向量匹配搜索，列表浏览用 PostgreSQL 更合适

接口列表:
  GET /api/users              用户发现列表（支持筛选 + 分页）
  GET /api/users/{user_id}    用户公开主页
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from api.schemas import UserPublicResponse, UserListResponse
from core.database.session import get_db
from core.database.models import User

router = APIRouter(prefix="/api/users", tags=["用户"])


def _to_public(user: User) -> dict:
    """将 User ORM 对象转换为公开资料字典（去除私密字段）

    学习要点：
    - 公开资料不包含：password_hash、email、phone、target_* 择偶偏好
    - 择偶偏好是私密的（用户不希望别人知道自己的择偶标准）
    - follower_count 等社交统计 Phase 4 实现，暂时返回 0
    """
    return {
        "user_id": user.user_id,
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "province": user.province,
        "education": user.education,
        "annual_income": user.annual_income,
        "marital_status": user.marital_status,
        "mbti": user.mbti,
        "height_cm": user.height_cm,
        "about_me": user.about_me or "",
        "hobbies": user.hobbies or "",
        "avatar_url": user.avatar_url,
        "photos": user.photos or [],
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "follower_count": 0,
        "following_count": 0,
        "match_count": 0,
    }


@router.get("", response_model=UserListResponse)
async def list_users(
    gender: Optional[str] = Query(default=None, description="筛选性别: male/female"),
    city: Optional[str] = Query(default=None, description="筛选城市（模糊匹配）"),
    age_min: Optional[int] = Query(default=None, ge=18, le=80, description="最小年龄"),
    age_max: Optional[int] = Query(default=None, ge=18, le=80, description="最大年龄"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    用户发现列表（小红书风格双列瀑布流的数据源）。

    学习要点：
    - Query() 参数: FastAPI 从 URL query string 提取参数
      例如: GET /api/users?gender=female&city=上海&page=2
    - 动态筛选条件: 只有用户传了的参数才加入 WHERE 条件（避免全量扫描）
    - 分页: offset = (page - 1) * page_size
    - 两次查询策略: 一次查总数（前端分页 UI 需要），一次查当页数据
      性能优化: COUNT(*) 用子查询，避免全表扫描
    """
    query = select(User).where(User.is_active == True)  # noqa: E712

    # 动态添加筛选条件（只有传了参数才过滤）
    if gender:
        query = query.where(User.gender == gender)
    if city:
        query = query.where(User.city.ilike(f"%{city}%"))
    if age_min:
        query = query.where(User.age >= age_min)
    if age_max:
        query = query.where(User.age <= age_max)

    # 查询总数（用于前端分页组件显示 "共 X 人"）
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # 查询当页数据（按注册时间倒序，最新注册的排前面）
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        users=[UserPublicResponse(**_to_public(u)) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户公开主页。

    学习要点：
    - 公开主页任何人都可以访问（不需要登录）
    - 只返回公开信息，不包含私密字段
    - 路径参数 user_id 是用户的业务 ID（如 "U1A2B3C4"）
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    return UserPublicResponse(**_to_public(user))
