"""
心犀AI - 认证路由
==================
处理用户注册、登录、Token 刷新、个人资料查看/编辑。

学习要点：
---------
- 所有写入操作（注册/登录）都使用 async 函数 + AsyncSession
- get_current_user 依赖注入自动验证 JWT，无需手动检查
- Pydantic Schema 用于请求验证（自动检查字段类型和约束）

接口列表：
  POST /api/auth/register   注册新用户
  POST /api/auth/login      登录（返回 access + refresh Token）
  POST /api/auth/refresh    用 refresh Token 换新的 access Token
  GET  /api/auth/me         获取当前登录用户的资料
  PUT  /api/auth/me         编辑当前登录用户的资料
"""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from api.schemas import UserCreate, UserResponse, MessageResponse, PhotoUploadResponse
from core.database.session import get_db
from core.database.models import User

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 上传文件配置
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _generate_user_id() -> str:
    """生成唯一用户ID：U + 8位随机大写字母/数字"""
    return "U" + uuid.uuid4().hex[:8].upper()


# ============================================================
# POST /api/auth/register - 注册
# ============================================================

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    注册新用户。

    学习要点：
    - 密码用 bcrypt 加密后存储，绝不保存明文
    - user_id 由服务端自动生成（U + 8位随机），用户不能指定
    - 注册成功后同时返回 Token，用户无需再次登录

    流程：
    1. 检查邮箱/手机是否已注册（防重复）
    2. 创建 User 记录（密码加密）
    3. 生成 JWT Token
    4. 返回用户信息 + Token
    """
    # 1. 检查邮箱唯一性（如果提供了邮箱）
    if body.email:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(400, "该邮箱已被注册")

    # 2. 检查手机唯一性（如果提供了手机）
    if body.phone:
        existing = await db.execute(select(User).where(User.phone == body.phone))
        if existing.scalar_one_or_none():
            raise HTTPException(400, "该手机号已被注册")

    # 3. 创建用户
    user_id = _generate_user_id()
    user = User(
        user_id=user_id,
        nickname=body.nickname,
        gender=body.gender,
        age=body.age,
        city=body.city,
        province=body.province,
        education=body.education,
        annual_income=body.annual_income,
        marital_status=body.marital_status,
        mbti=body.mbti,
        about_me=body.about_me,
        ideal_partner=body.ideal_partner,
        hobbies=body.hobbies,
        target_gender=body.target_gender,
        target_age_min=body.target_age_min,
        target_age_max=body.target_age_max,
        target_city=body.target_city,
        password_hash=hash_password(body.password),
        email=body.email,
        phone=body.phone,
    )
    db.add(user)
    await db.flush()  # flush 让数据库分配 ID，但不提交事务

    # 4. 生成 Token
    access_token = create_access_token(user_id, user.nickname)
    refresh_token = create_refresh_token(user_id)

    # 5. 返回用户信息（通过 response headers 传递 Token）
    return UserResponse(
        **user.to_dict(),
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ============================================================
# POST /api/auth/login - 登录
# ============================================================

@router.post("/login", response_model=UserResponse)
async def login(
    body: "LoginRequest",
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录。

    学习要点：
    - 支持邮箱或 user_id 登录（灵活适配不同场景）
    - verify_password 对比 bcrypt 哈希值，不暴露密码是否存在
    - 登录成功后更新 last_login_at 时间戳

    安全注意：
    - 错误消息统一为"账号或密码错误"，不区分"用户不存在"和"密码错误"
    - 这样攻击者无法通过错误消息枚举有效账号
    """
    # 1. 查找用户（支持邮箱或 user_id 登录）
    query = select(User).where(
        (User.email == body.account) | (User.user_id == body.account)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # 2. 验证密码（统一错误消息，防止账号枚举）
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误")

    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")

    # 3. 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)

    # 4. 生成 Token
    access_token = create_access_token(user.user_id, user.nickname)
    refresh_token = create_refresh_token(user.user_id)

    return UserResponse(
        **user.to_dict(),
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ============================================================
# POST /api/auth/refresh - 刷新 Token
# ============================================================

@router.post("/refresh")
async def refresh_token(
    body: "RefreshRequest",
    db: AsyncSession = Depends(get_db),
):
    """
    用 refresh Token 换取新的 access Token。

    学习要点：
    - access Token 短期有效（2小时），refresh Token 长期有效（7天）
    - 当 access Token 过期时，前端用 refresh Token 静默获取新 Token
    - 用户感知不到 Token 刷新，体验更流畅
    """
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(401, "请提供 refresh Token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token 无效")

    # 验证用户仍然活跃
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")

    # 生成新 Token
    new_access = create_access_token(user.user_id, user.nickname)
    new_refresh = create_refresh_token(user.user_id)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


# ============================================================
# GET /api/auth/me - 获取当前用户信息
# ============================================================

@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前登录用户的完整资料。

    学习要点：
    - Depends(get_current_user) 自动验证 JWT 并注入 user_id
    - 如果 Token 无效/过期，直接返回 401，不需要手动检查
    - 这就是 FastAPI 依赖注入的威力：认证逻辑和业务逻辑完全解耦
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    return UserResponse(**user.to_dict())


# ============================================================
# PUT /api/auth/me - 编辑个人资料
# ============================================================

@router.put("/me", response_model=UserResponse)
async def update_me(
    body: "UpdateProfileRequest",
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    编辑当前登录用户的个人资料。

    学习要点：
    - 部分更新（Partial Update）：只传需要修改的字段
    - body.model_dump(exclude_unset=True) 只包含用户实际传入的字段
    - 这样前端不需要发送完整表单，只发变化的字段即可

    Agent 集成：
    - 如果修改了影响向量的字段（about_me / ideal_partner 等），
      通过 BackgroundTasks 在后台异步同步 ChromaDB
    - 不阻塞 API 响应——用户立刻拿到结果，向量在后台更新
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    # 部分更新：只修改传入的字段
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.flush()

    # 如果修改了影响向量搜索的字段，触发 ChromaDB 后台同步
    # VECTOR_FIELDS 在 chroma_sync.py 中定义，包含影响向量质量的字段集合
    from core.tasks.chroma_sync import VECTOR_FIELDS, sync_user_vector
    if VECTOR_FIELDS.intersection(update_data.keys()):
        background_tasks.add_task(sync_user_vector, user_id=user_id, user=user)

    return UserResponse(**user.to_dict())


# ============================================================
# POST /api/auth/me/avatar - 上传头像
# ============================================================

@router.post("/me/avatar")
async def upload_avatar(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传或更新用户头像。

    学习要点：
    - UploadFile: FastAPI 的文件上传类型，自动处理 multipart/form-data
    - file.content_type: 验证 MIME 类型，防止上传非图片文件
    - 文件名策略: 用 user_id 固定文件名，新头像覆盖旧头像（不积累冗余文件）
    - BackgroundTasks: 上传完成后异步更新 ChromaDB metadata

    安全注意：
    - 限制文件类型（只允许 jpg/png/webp），防止上传可执行文件
    - 限制文件大小（5MB），防止存储耗尽
    - 文件名由服务端生成，不使用用户提供的文件名（防路径注入攻击）
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"只支持 JPEG/PNG/WebP 格式，收到: {file.content_type}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件大小不能超过 5MB，收到: {len(content) / 1024 / 1024:.1f}MB")

    # 确定扩展名
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")

    # 保存文件（固定文件名：user_id.ext，覆盖旧头像）
    avatar_dir = os.path.join(UPLOADS_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    filename = f"{user_id}.{ext}"
    filepath = os.path.join(avatar_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # 更新数据库
    avatar_url = f"/uploads/avatars/{filename}"
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    user.avatar_url = avatar_url
    await db.flush()

    # 头像变化需要同步 ChromaDB（不影响向量质量，但保持数据一致性）
    from core.tasks.chroma_sync import sync_user_vector
    background_tasks.add_task(sync_user_vector, user_id=user_id, user=user)

    return {"url": avatar_url, "message": "头像上传成功"}


# ============================================================
# POST /api/auth/me/photos - 上传照片（最多 6 张）
# ============================================================

@router.post("/me/photos")
async def upload_photo(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传用户照片（最多 6 张）。

    学习要点：
    - 照片列表存储在 users.photos JSONB 字段（PostgreSQL 的 JSON 列类型）
    - JSONB 支持索引，比 TEXT 存 JSON 字符串性能更好
    - 每次上传追加到列表末尾；超过 6 张时拒绝（前端也做限制，这里是服务端兜底）
    - 文件名用 UUID 前缀保证唯一（区别于头像的固定文件名策略）
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "只支持 JPEG/PNG/WebP 格式")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件大小不能超过 5MB")

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    current_photos = list(user.photos or [])
    if len(current_photos) >= 6:
        raise HTTPException(400, "最多上传 6 张照片，请先删除部分照片再上传")

    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")

    photos_dir = os.path.join(UPLOADS_DIR, "photos")
    os.makedirs(photos_dir, exist_ok=True)
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(photos_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    photo_url = f"/uploads/photos/{filename}"
    user.photos = current_photos + [photo_url]
    await db.flush()

    return PhotoUploadResponse(url=photo_url, photos=user.photos)


# ============================================================
# DELETE /api/auth/me/photos/{index} - 删除照片
# ============================================================

@router.delete("/me/photos/{index}")
async def delete_photo(
    index: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除指定位置的照片（按索引 0~5）。

    学习要点：
    - JSONB 数组更新：不能直接 SQL 删除元素，需要在 Python 层重建列表再写回
    - 同时删除服务器上的物理文件，避免孤立文件占用存储
    - index 超出范围时返回 400（不是 404，因为照片不是独立的可寻址资源）
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    photos = list(user.photos or [])
    if index < 0 or index >= len(photos):
        raise HTTPException(400, f"索引 {index} 超出范围（当前有 {len(photos)} 张照片）")

    # 删除物理文件
    photo_url = photos[index]
    filename = os.path.basename(photo_url)
    filepath = os.path.join(UPLOADS_DIR, "photos", filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    # 更新数据库（重建列表）
    photos.pop(index)
    user.photos = photos
    await db.flush()

    return PhotoUploadResponse(url="", photos=user.photos)


# ============================================================
# Pydantic 请求模型（认证专用）
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """登录请求"""
    account: str = Field(description="邮箱或用户ID")
    password: str = Field(description="密码")


class RefreshRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(description="Refresh Token")


class UpdateProfileRequest(BaseModel):
    """编辑个人资料请求（所有字段可选）"""
    nickname: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=18, le=80)
    city: Optional[str] = None
    province: Optional[str] = None
    education: Optional[str] = None
    annual_income: Optional[str] = None
    marital_status: Optional[str] = None
    mbti: Optional[str] = None
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    about_me: Optional[str] = Field(default=None, min_length=10)
    ideal_partner: Optional[str] = Field(default=None, min_length=10)
    hobbies: Optional[str] = None
    target_gender: Optional[str] = None
    target_age_min: Optional[int] = Field(default=None, ge=18, le=80)
    target_age_max: Optional[int] = Field(default=None, ge=18, le=80)
    target_city: Optional[str] = None
    target_height_min: Optional[int] = None
    target_height_max: Optional[int] = None
    target_education: Optional[str] = None
    avatar_url: Optional[str] = None
