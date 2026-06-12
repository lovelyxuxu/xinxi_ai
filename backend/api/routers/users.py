"""
心犀AI - 用户路由
==================
处理用户资料管理和用户浏览相关的 HTTP 接口。

接口列表：
  POST   /api/users          创建用户（注册）
  GET    /api/users          浏览用户列表（支持分页和筛选）
  GET    /api/users/{id}     查看单个用户详情
  PUT    /api/users/{id}     更新用户资料
  DELETE /api/users/{id}     删除用户
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends

from api.schemas import (
    UserCreate, UserUpdate, UserResponse,
    UserListResponse, MessageResponse,
)
from api.deps import get_services, AppServices, generate_user_id
from core.models.user_profile import UserProfile

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _user_to_response(user: UserProfile, created_at: str = None) -> UserResponse:
    """将领域模型 UserProfile 转换为 API 响应模型"""
    return UserResponse(
        user_id=user.user_id,
        nickname=user.nickname,
        gender=user.gender,
        age=user.age,
        city=user.city,
        province=user.province,
        education=user.education,
        annual_income=user.annual_income,
        marital_status=user.marital_status,
        target_gender=user.target_gender,
        target_age_min=user.target_age_min,
        target_age_max=user.target_age_max,
        target_city=user.target_city,
        about_me=user.about_me,
        ideal_partner=user.ideal_partner,
        hobbies=user.hobbies,
        mbti=user.mbti,
        created_at=created_at,
    )


# ============================================================
# POST /api/users - 创建用户
# ============================================================
@router.post("", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate, svc: AppServices = Depends(get_services)):
    """
    注册新用户。
    系统自动生成 user_id，将用户资料存入 Chroma 向量数据库。
    """
    user_id = generate_user_id()

    # 构建 UserProfile 领域模型
    user = UserProfile(
        user_id=user_id,
        nickname=body.nickname,
        gender=body.gender,
        age=body.age,
        city=body.city,
        province=body.province,
        education=body.education,
        annual_income=body.annual_income,
        marital_status=body.marital_status,
        target_gender=body.target_gender,
        target_age_min=body.target_age_min,
        target_age_max=body.target_age_max,
        target_city=body.target_city,
        about_me=body.about_me,
        ideal_partner=body.ideal_partner,
        hobbies=body.hobbies,
        mbti=body.mbti,
    )

    # 写入 Chroma（自动触发 Embedding）
    svc.chroma_store.upsert_user(user)

    # 记录创建时间
    now = datetime.now().isoformat()
    svc.user_meta[user_id] = {"created_at": now}

    return _user_to_response(user, created_at=now)


# ============================================================
# GET /api/users - 浏览用户列表
# ============================================================
@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=200, description="每页数量"),
    gender: str | None = Query(None, description="按性别筛选"),
    city: str | None = Query(None, description="按城市筛选"),
    svc: AppServices = Depends(get_services),
):
    """
    浏览所有用户，支持分页和简单筛选。

    学习要点：
    - ChromaDB 的 get() 方法可以不带向量查询，只按 metadata 过滤
    - 分页在应用层实现（ChromaDB 不原生支持分页）
    """
    # 构建 where 过滤条件
    where_filter = {}
    conditions = []
    if gender:
        conditions.append({"gender": gender})
    if city:
        conditions.append({"city": city})

    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}
    else:
        where_filter = None

    # 从 Chroma 查询（不带向量搜索，只按 metadata 过滤）
    get_params = {"include": ["metadatas", "documents"]}
    if where_filter:
        get_params["where"] = where_filter

    results = svc.chroma_store.collection.get(**get_params)

    # 整理结果并分页
    all_users = []
    if results and results["ids"]:
        for i, uid in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            created_at = svc.user_meta.get(uid, {}).get("created_at")

            user_resp = UserResponse(
                user_id=uid,
                nickname=meta.get("nickname", ""),
                gender=meta.get("gender", ""),
                age=meta.get("age", 0),
                city=meta.get("city", ""),
                province=meta.get("province", ""),
                education=meta.get("education", ""),
                annual_income=meta.get("annual_income", "未填写"),
                marital_status=meta.get("marital_status", "未婚"),
                target_gender=meta.get("target_gender", ""),
                target_age_min=meta.get("target_age_min", 18),
                target_age_max=meta.get("target_age_max", 45),
                target_city=meta.get("target_city", "不限"),
                about_me=meta.get("about_me", ""),
                ideal_partner=meta.get("ideal_partner", ""),
                hobbies=meta.get("hobbies", ""),
                mbti=meta.get("mbti", "未知"),
                created_at=created_at,
            )
            all_users.append(user_resp)

    total = len(all_users)
    start = (page - 1) * page_size
    end = start + page_size
    page_users = all_users[start:end]

    return UserListResponse(
        users=page_users,
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# GET /api/users/{user_id} - 查看用户详情
# ============================================================
@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, svc: AppServices = Depends(get_services)):
    """查看指定用户的详细资料"""
    data = svc.chroma_store.get_user(user_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    meta = data["metadata"]
    created_at = svc.user_meta.get(user_id, {}).get("created_at")

    return UserResponse(
        user_id=user_id,
        nickname=meta.get("nickname", ""),
        gender=meta.get("gender", ""),
        age=meta.get("age", 0),
        city=meta.get("city", ""),
        province=meta.get("province", ""),
        education=meta.get("education", ""),
        annual_income=meta.get("annual_income", "未填写"),
        marital_status=meta.get("marital_status", "未婚"),
        target_gender=meta.get("target_gender", ""),
        target_age_min=meta.get("target_age_min", 18),
        target_age_max=meta.get("target_age_max", 45),
        target_city=meta.get("target_city", "不限"),
        about_me=meta.get("about_me", ""),
        ideal_partner=meta.get("ideal_partner", ""),
        hobbies=meta.get("hobbies", ""),
        mbti=meta.get("mbti", "未知"),
        created_at=created_at,
    )


# ============================================================
# PUT /api/users/{user_id} - 更新用户资料
# ============================================================
@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UserUpdate,
    svc: AppServices = Depends(get_services),
):
    """
    更新用户资料（部分更新）。
    只需传需要修改的字段，未传的字段保持不变。

    学习要点：
    - 先从 Chroma 读取现有数据
    - 合并更新字段
    - 重新写入 Chroma（触发重新 Embedding）
    """
    # 读取现有数据
    existing = svc.chroma_store.get_user(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    meta = existing["metadata"]

    # 提取用户提交的更新字段（只取非 None 的值）
    update_data = body.model_dump(exclude_none=True)

    # 合并：现有值 + 更新值
    merged = {**meta, **update_data}

    # 重建 UserProfile 并写入 Chroma
    user = UserProfile(
        user_id=user_id,
        nickname=merged.get("nickname", ""),
        gender=merged.get("gender", ""),
        age=merged.get("age", 0),
        city=merged.get("city", ""),
        province=merged.get("province", ""),
        education=merged.get("education", ""),
        annual_income=merged.get("annual_income", "未填写"),
        marital_status=merged.get("marital_status", "未婚"),
        target_gender=merged.get("target_gender", ""),
        target_age_min=merged.get("target_age_min", 18),
        target_age_max=merged.get("target_age_max", 45),
        target_city=merged.get("target_city", "不限"),
        about_me=merged.get("about_me", ""),
        ideal_partner=merged.get("ideal_partner", ""),
        hobbies=merged.get("hobbies", ""),
        mbti=merged.get("mbti", "未知"),
    )
    svc.chroma_store.upsert_user(user)

    created_at = svc.user_meta.get(user_id, {}).get("created_at")
    return _user_to_response(user, created_at=created_at)


# ============================================================
# DELETE /api/users/{user_id} - 删除用户
# ============================================================
@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(user_id: str, svc: AppServices = Depends(get_services)):
    """删除指定用户"""
    existing = svc.chroma_store.get_user(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    # 从 Chroma 中删除
    svc.chroma_store.collection.delete(ids=[user_id])
    svc.user_meta.pop(user_id, None)
    svc.match_history.pop(user_id, None)

    return MessageResponse(message=f"用户 {user_id} 已删除")
