# Phase 2 - 用户中心 + UI 全面升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成用户资料编辑、图片/头像上传、个人中心页面，同时将全局 UI 从白色简陋风格重做为暗色渐变 + 磨砂玻璃 + 移动端优先（小红书风格），替换所有 emoji 图标为 Lucide 图标。

**Architecture:** 后端新增图片上传 API + ChromaDB 异步同步任务；前端一次性重做主题系统（CSS 变量 + Tailwind dark 扩展），新增个人中心和编辑资料页，改造首页为双列瀑布流，新增移动端底部导航栏。

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + framer-motion + Lucide React + Tailwind CSS + Zustand + browser-image-compression

---

## 文件变更总览

### 后端

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/core/database/models.py` | 修改 | 新增 `photos JSONB` 字段，更新 `to_dict()` |
| `backend/api/schemas.py` | 修改 | 新增 `UserUpdateFull`、`PhotosResponse`、更新 `UserResponse` 加 `photos` |
| `backend/api/routers/auth.py` | 修改 | 新增头像/照片上传接口，完善 PUT /me + ChromaDB 同步 |
| `backend/api/routers/users.py` | 修改 | 完善发现列表 + 用户详情接口 |
| `backend/api/app.py` | 修改 | 挂载 StaticFiles，创建 uploads 目录 |
| `backend/core/tasks/chroma_sync.py` | 新增 | ChromaDB 异步后台同步任务 |
| `backend/alembic/versions/2026_06_13_1400-002_add_photos_field.py` | 新增 | 数据库迁移：添加 photos 字段 |
| `backend/uploads/avatars/.gitkeep` | 新增 | 头像存储目录 |
| `backend/uploads/photos/.gitkeep` | 新增 | 照片存储目录 |

### 前端

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend/package.json` | 修改 | 新增 framer-motion, zustand, browser-image-compression |
| `frontend/src/index.css` | 修改 | 重做主题：CSS 变量 + 暗色渐变背景 |
| `frontend/tailwind.config.ts` | 修改 | 扩展主题颜色、动效 |
| `frontend/src/stores/appStore.ts` | 新增 | Zustand 全局状态（消息未读数等） |
| `frontend/src/components/BottomNav.tsx` | 新增 | 移动端底部导航栏 |
| `frontend/src/components/ImageUpload.tsx` | 新增 | 图片上传组件（含压缩） |
| `frontend/src/components/Navbar.tsx` | 修改 | 暗色主题适配，Lucide 图标，完善下拉菜单 |
| `frontend/src/components/UserCard.tsx` | 修改 | 暗色主题 + 双列适配 + 照片展示 |
| `frontend/src/pages/Home.tsx` | 修改 | 双列瀑布流布局 |
| `frontend/src/pages/MyProfile.tsx` | 新增 | 个人中心页面 |
| `frontend/src/pages/EditProfile.tsx` | 新增 | 编辑资料页面 |
| `frontend/src/pages/Login.tsx` | 修改 | 暗色主题适配 |
| `frontend/src/pages/Register.tsx` | 修改 | 暗色主题适配 |
| `frontend/src/api/client.ts` | 修改 | 新增 updateProfile, uploadAvatar, uploadPhotos API 函数 |
| `frontend/src/types/index.ts` | 修改 | 新增 `photos` 字段，完善类型定义 |
| `frontend/src/App.tsx` | 修改 | 新增 /profile 和 /profile/edit 路由，加入 BottomNav |

---

## Task 1：数据库迁移 - 添加 photos 字段

**Files:**
- Create: `backend/alembic/versions/2026_06_13_1400-002_add_photos_field.py`
- Modify: `backend/core/database/models.py`

- [ ] **Step 1: 更新 ORM 模型，添加 photos 字段**

在 `backend/core/database/models.py` 的 `User` 类中，在 `avatar_url` 字段后添加：

```python
# === 元数据 ===（修改现有部分，在 avatar_url 后追加）
avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
photos: Mapped[list] = mapped_column(
    JSONB,
    default=list,
    comment="用户照片 URL 列表，最多 6 张",
)
```

同时更新 `to_dict()` 方法，在返回字典中加入 `photos`：

```python
def to_dict(self) -> dict:
    return {
        "user_id": self.user_id,
        "nickname": self.nickname,
        "gender": self.gender,
        "age": self.age,
        "city": self.city,
        "province": self.province,
        "education": self.education,
        "annual_income": self.annual_income,
        "marital_status": self.marital_status,
        "mbti": self.mbti,
        "height_cm": self.height_cm,
        "about_me": self.about_me,
        "ideal_partner": self.ideal_partner,
        "hobbies": self.hobbies,
        "target_gender": self.target_gender,
        "target_age_min": self.target_age_min,
        "target_age_max": self.target_age_max,
        "target_city": self.target_city,
        "target_height_min": self.target_height_min,
        "target_height_max": self.target_height_max,
        "target_education": self.target_education,
        "avatar_url": self.avatar_url,
        "photos": self.photos or [],
        "created_at": self.created_at.isoformat() if self.created_at else None,
    }
```

- [ ] **Step 2: 生成并检查 Alembic 迁移脚本**

```bash
cd E:\study\python\xinxi_ai\backend
python -m alembic revision --autogenerate -m "add_photos_field"
```

检查生成的文件，确认 `upgrade()` 中有类似：
```python
op.add_column('users', sa.Column('photos', postgresql.JSONB(), nullable=True), schema='xinxi')
```

- [ ] **Step 3: 执行迁移**

```bash
python -m alembic upgrade head
```

预期输出：`Running upgrade ... -> ..., add_photos_field`

- [ ] **Step 4: 验证迁移成功**

```bash
python -c "
import asyncio
from core.database.session import AsyncSessionLocal
from sqlalchemy import text
async def check():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_schema='xinxi' AND table_name='users' AND column_name='photos'\"))
        print('photos 字段:', r.scalar_one_or_none())
asyncio.run(check())
"
```

预期：`photos 字段: photos`

- [ ] **Step 5: 提交**

```bash
cd E:\study\python\xinxi_ai
git add backend/core/database/models.py backend/alembic/versions/
git commit -m "feat: add photos JSONB field to users table"
```

---

## Task 2：后端 - 更新 Schemas

**Files:**
- Modify: `backend/api/schemas.py`

- [ ] **Step 1: 更新 `UserResponse` 添加 `photos` 字段**

在 `UserResponse` 类中，在 `avatar_url` 后添加：

```python
avatar_url: Optional[str] = None
photos: list[str] = []          # 用户照片 URL 列表
```

- [ ] **Step 2: 新增 `PhotoUploadResponse` Schema**

在文件末尾 `MessageResponse` 之前添加：

```python
class PhotoUploadResponse(BaseModel):
    """图片上传响应"""
    url: str = Field(description="图片访问 URL")
    photos: list[str] = Field(description="更新后的照片列表")

class UserPublicResponse(BaseModel):
    """用户公开主页响应（不含择偶偏好等私密信息）"""
    user_id: str
    nickname: str
    gender: str
    age: int
    city: str
    province: str
    education: str
    annual_income: str
    marital_status: str
    mbti: str
    height_cm: Optional[int] = None
    about_me: str
    hobbies: str
    avatar_url: Optional[str] = None
    photos: list[str] = []
    created_at: Optional[str] = None

    # 社交统计（后续 Phase 填充，现在返回 0）
    follower_count: int = 0
    following_count: int = 0
    match_count: int = 0
```

- [ ] **Step 3: 提交**

```bash
git add backend/api/schemas.py
git commit -m "feat: update schemas with photos and public user response"
```

---

## Task 3：后端 - ChromaDB 异步同步任务

**Files:**
- Create: `backend/core/tasks/__init__.py`
- Create: `backend/core/tasks/chroma_sync.py`

- [ ] **Step 1: 创建 tasks 包**

创建 `backend/core/tasks/__init__.py`（空文件）。

- [ ] **Step 2: 创建 `chroma_sync.py`**

```python
"""
心犀AI - ChromaDB 向量同步后台任务
====================================
当用户修改个人资料（about_me / ideal_partner / hobbies）时，
需要同步更新 ChromaDB 中的向量嵌入，以便后续匹配时使用最新数据。

学习要点：
---------
- FastAPI BackgroundTasks：在返回 HTTP 响应后，异步执行后台任务
  用法：def endpoint(background_tasks: BackgroundTasks):
           background_tasks.add_task(sync_user_vector, user_id=user_id)
  特点：不阻塞接口响应，用户立刻拿到结果，向量更新在后台静默完成

- 为什么要同步向量？
  ChromaDB 存储的是用户文本的语义向量。
  如果用户修改了 about_me，但向量还是旧的，
  那么匹配时搜索到的用户画像就是过时的——会影响匹配质量。

- 同步策略：
  1. 先检查用户是否已在 ChromaDB 中（有旧向量）
  2. 如果有，删除旧向量并写入新向量（update 操作）
  3. 如果没有，直接添加（add 操作）
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def build_user_document(user) -> str:
    """
    将用户资料拼接成一段文本，用于生成向量嵌入。

    学习要点：
    - 向量嵌入的质量直接影响语义搜索的效果
    - 拼接方式：把各字段用自然语言连接，而不是机械拼接
    - 包含 about_me（自我介绍）、ideal_partner（择偶偏好文字）、hobbies（爱好）
    - 不包含 age/city 等结构化字段（这些字段用 metadata filter 处理，不用向量搜索）
    """
    parts = []
    if user.about_me:
        parts.append(f"关于我：{user.about_me}")
    if user.ideal_partner:
        parts.append(f"我的理想伴侣：{user.ideal_partner}")
    if user.hobbies:
        parts.append(f"我的兴趣爱好：{user.hobbies}")
    if user.mbti and user.mbti != "未知":
        parts.append(f"我的MBTI是{user.mbti}")
    return " ".join(parts) if parts else f"{user.nickname}，{user.age}岁，来自{user.city}"


def build_user_metadata(user) -> dict:
    """
    构建 ChromaDB 的 metadata，用于 metadata filter 精确筛选。

    学习要点：
    - ChromaDB 的混合检索 = 向量语义搜索 + metadata filter 精确过滤
    - metadata 存储结构化字段（年龄、城市、性别等）
    - 匹配时 Agent 会用 metadata filter 先缩小候选范围，再用向量排序
    """
    return {
        "user_id": user.user_id,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "province": user.province,
        "education": user.education,
        "height_cm": user.height_cm or 0,
        "annual_income": user.annual_income,
        "marital_status": user.marital_status,
    }


async def sync_user_vector(user_id: str, user=None) -> None:
    """
    将用户资料同步到 ChromaDB。

    参数:
        user_id: 用户业务 ID（如 "U1A2B3C4"）
        user: SQLAlchemy User 对象（如果已查好，直接传入避免重复查询）

    学习要点：
    - 这是一个 async 函数，可以被 await 调用，也可以被 BackgroundTasks 调度
    - 使用 try/except 包裹，确保同步失败不影响主流程
    - 日志记录同步结果，便于排查问题
    """
    try:
        # 懒加载导入，避免循环依赖
        from core.database.chroma_store import ChromaStore
        from core.database.session import AsyncSessionLocal
        from core.database.models import User
        from sqlalchemy import select

        # 如果没传 user 对象，从数据库查
        if user is None:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.user_id == user_id))
                user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"[ChromaSync] 用户 {user_id} 不存在，跳过同步")
            return

        # 构建文档和 metadata
        document = build_user_document(user)
        metadata = build_user_metadata(user)

        # 同步到 ChromaDB
        chroma = ChromaStore()
        chroma.upsert_user(
            user_id=user_id,
            document=document,
            metadata=metadata,
        )

        logger.info(f"[ChromaSync] 用户 {user_id} 向量同步完成")

    except Exception as e:
        # 同步失败只记录日志，不影响主请求
        logger.error(f"[ChromaSync] 用户 {user_id} 向量同步失败: {e}")
```

- [ ] **Step 3: 检查 ChromaStore 是否有 `upsert_user` 方法**

```bash
cd E:\study\python\xinxi_ai
python -c "from backend.core.database.chroma_store import ChromaStore; print(dir(ChromaStore()))"
```

如果 `ChromaStore` 没有 `upsert_user` 方法，需要看现有的 `add_user` 或 `update_user` 方法名，并在 `chroma_sync.py` 中使用对应的方法名。

- [ ] **Step 4: 提交**

```bash
git add backend/core/tasks/
git commit -m "feat: add ChromaDB async background sync task"
```

---

## Task 4：后端 - 图片上传接口

**Files:**
- Modify: `backend/api/routers/auth.py`
- Modify: `backend/api/app.py`
- Create: `backend/uploads/avatars/.gitkeep`
- Create: `backend/uploads/photos/.gitkeep`

- [ ] **Step 1: 创建上传目录**

```bash
New-Item -ItemType Directory -Force -Path "backend/uploads/avatars"
New-Item -ItemType Directory -Force -Path "backend/uploads/photos"
New-Item -ItemType File -Force -Path "backend/uploads/avatars/.gitkeep"
New-Item -ItemType File -Force -Path "backend/uploads/photos/.gitkeep"
```

- [ ] **Step 2: 在 `app.py` 挂载静态文件**

在 `backend/api/app.py` 中，找到 lifespan 或应用初始化部分，添加静态文件挂载：

```python
import os
from fastapi.staticfiles import StaticFiles

# 在 create_app() 或 app 初始化后添加：
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(os.path.join(UPLOADS_DIR, "avatars"), exist_ok=True)
os.makedirs(os.path.join(UPLOADS_DIR, "photos"), exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
```

- [ ] **Step 3: 在 `auth.py` 添加头像上传接口**

在 `backend/api/routers/auth.py` 文件末尾（在 Pydantic 模型定义之前）添加：

```python
import os
import uuid
from fastapi import BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


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
    - file.content_type: 检查 MIME 类型，防止上传非图片文件
    - 文件名策略: 用 user_id 作为文件名（固定名），新头像覆盖旧头像
    - BackgroundTasks: 上传完成后异步同步 ChromaDB（不阻塞响应）

    安全注意：
    - 限制文件类型（只允许 jpg/png/webp）
    - 限制文件大小（5MB）
    - 文件名由服务端生成，不使用用户提供的文件名（防路径注入）
    """
    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"只支持 JPEG/PNG/WebP 格式，收到: {file.content_type}")

    # 读取并检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件大小不能超过 5MB，收到: {len(content) / 1024 / 1024:.1f}MB")

    # 确定扩展名
    ext = "jpg" if file.content_type == "image/jpeg" else file.content_type.split("/")[1]

    # 保存文件（用 user_id 作为文件名，覆盖旧头像）
    avatar_dir = os.path.join(UPLOADS_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    filename = f"{user_id}.{ext}"
    filepath = os.path.join(avatar_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # 更新数据库中的 avatar_url
    avatar_url = f"/uploads/avatars/{filename}"
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    user.avatar_url = avatar_url
    await db.flush()

    # 后台异步同步 ChromaDB（头像变化不影响向量，但更新 metadata）
    from core.tasks.chroma_sync import sync_user_vector
    background_tasks.add_task(sync_user_vector, user_id=user_id, user=user)

    return {"url": avatar_url, "message": "头像上传成功"}


# ============================================================
# POST /api/auth/me/photos - 上传照片（最多6张）
# ============================================================

@router.post("/me/photos", response_model=None)
async def upload_photo(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传用户照片（最多 6 张）。

    学习要点：
    - 照片列表存储在 users.photos JSONB 字段中（URL 数组）
    - 每次上传追加到列表末尾
    - 超过 6 张时拒绝上传（前端也做限制，这里是服务端兜底）
    - 文件名用 UUID 保证唯一（不同于头像的固定名策略）
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

    current_photos = user.photos or []
    if len(current_photos) >= 6:
        raise HTTPException(400, "最多上传 6 张照片，请先删除部分照片")

    ext = "jpg" if file.content_type == "image/jpeg" else file.content_type.split("/")[1]
    photos_dir = os.path.join(UPLOADS_DIR, "photos")
    os.makedirs(photos_dir, exist_ok=True)
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(photos_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    photo_url = f"/uploads/photos/{filename}"
    user.photos = current_photos + [photo_url]
    await db.flush()

    return {"url": photo_url, "photos": user.photos}


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
    - JSONB 数组更新：不能直接用 SQL 删除元素，需要在 Python 层重建列表
    - 同时删除服务器上的物理文件（避免存储泄漏）
    - index 超出范围时返回 400，不能返回 404（照片不是独立资源）
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

    # 更新数据库
    photos.pop(index)
    user.photos = photos
    await db.flush()

    return {"photos": user.photos, "message": "照片已删除"}
```

- [ ] **Step 4: 在 `auth.py` 的 PUT /me 接口中添加 ChromaDB 同步**

找到现有的 `update_me` 函数，修改为：

```python
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
    - model_dump(exclude_unset=True): 只包含用户实际传入的字段（部分更新）
    - VECTOR_FIELDS: 需要触发 ChromaDB 同步的字段集合
      只有这些字段被修改时，才需要重新生成向量（避免不必要的同步）
    - BackgroundTasks.add_task(): 在响应返回后异步执行，不阻塞用户等待
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()

    # 如果修改了影响向量的字段，触发 ChromaDB 异步同步
    VECTOR_FIELDS = {"about_me", "ideal_partner", "hobbies", "mbti",
                     "age", "city", "province", "education", "gender"}
    if VECTOR_FIELDS.intersection(update_data.keys()):
        from core.tasks.chroma_sync import sync_user_vector
        background_tasks.add_task(sync_user_vector, user_id=user_id, user=user)

    return UserResponse(**user.to_dict())
```

- [ ] **Step 5: 验证上传接口可用**

启动后端：
```bash
cd E:\study\python\xinxi_ai\backend
python run.py
```

测试头像上传（需要先登录获取 Token）：
```bash
# 用 curl 测试（替换 YOUR_TOKEN 为实际 Token）
curl -X POST http://localhost:8000/api/auth/me/avatar \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.jpg"
```

预期返回：`{"url": "/uploads/avatars/UXXX.jpg", "message": "头像上传成功"}`

- [ ] **Step 6: 提交**

```bash
git add backend/api/routers/auth.py backend/api/app.py backend/uploads/
git commit -m "feat: add avatar and photo upload endpoints with background ChromaDB sync"
```

---

## Task 5：后端 - 用户发现列表接口

**Files:**
- Modify: `backend/api/routers/users.py`

- [ ] **Step 1: 查看现有 users.py 内容**

读取 `backend/api/routers/users.py`，了解现有接口。

- [ ] **Step 2: 完善 GET /api/users 和 GET /api/users/{user_id}**

将 `backend/api/routers/users.py` 完整替换为：

```python
"""
心犀AI - 用户模块路由
======================
提供用户发现列表和用户详情接口。

学习要点：
---------
- GET /api/users: 支持分页 + 性别/城市筛选，用于首页发现页
- GET /api/users/{user_id}: 用户公开主页，不暴露私密信息
- 两个接口都不需要登录（可选鉴权，登录用户未来可看到更多信息）

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


@router.get("", response_model=UserListResponse)
async def list_users(
    gender: Optional[str] = Query(default=None, description="筛选性别: male/female"),
    city: Optional[str] = Query(default=None, description="筛选城市"),
    age_min: Optional[int] = Query(default=None, ge=18, le=80),
    age_max: Optional[int] = Query(default=None, ge=18, le=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    用户发现列表。

    学习要点：
    - Query() 参数: FastAPI 从 URL query string 中提取参数
      例如: /api/users?gender=female&city=上海&page=2
    - 动态筛选条件: 只有用户传了的参数才加入 WHERE 条件
    - 分页计算: offset = (page - 1) * page_size
    - 两次查询: 一次查总数（for 分页 UI），一次查当页数据
    """
    query = select(User).where(User.is_active == True)

    if gender:
        query = query.where(User.gender == gender)
    if city:
        query = query.where(User.city.ilike(f"%{city}%"))
    if age_min:
        query = query.where(User.age >= age_min)
    if age_max:
        query = query.where(User.age <= age_max)

    # 查总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # 查当页数据（按注册时间倒序）
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
    - 公开主页只暴露非私密信息（不包含 target_* 择偶偏好、邮箱、手机等）
    - 任何人（包括未登录用户）都可以访问，这是"公开资料"
    - 如果需要区分登录/未登录用户看到的内容，用 get_optional_user 依赖
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    return UserPublicResponse(**_to_public(user))


def _to_public(user: User) -> dict:
    """将 User ORM 对象转换为公开资料字典（去除私密字段）"""
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
        "about_me": user.about_me,
        "hobbies": user.hobbies,
        "avatar_url": user.avatar_url,
        "photos": user.photos or [],
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "follower_count": 0,
        "following_count": 0,
        "match_count": 0,
    }
```

- [ ] **Step 3: 确认 `UserListResponse` 使用 `UserPublicResponse`**

检查 `backend/api/schemas.py` 中的 `UserListResponse`：

```python
class UserListResponse(BaseModel):
    """用户列表响应（带分页）"""
    users: list[UserPublicResponse]
    total: int
    page: int
    page_size: int
```

如果还是用的 `UserResponse`，更新为 `UserPublicResponse`。

- [ ] **Step 4: 提交**

```bash
git add backend/api/routers/users.py backend/api/schemas.py
git commit -m "feat: implement user discovery list and public profile endpoints"
```

---

## Task 6：前端 - 安装依赖 + 主题系统重做

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tailwind.config.ts`

- [ ] **Step 1: 安装新依赖**

```bash
cd E:\study\python\xinxi_ai\frontend
npm install framer-motion zustand browser-image-compression
```

预期：安装成功，`package.json` 中出现这三个包。

- [ ] **Step 2: 重做 `index.css` 主题系统**

将 `frontend/src/index.css` 替换为以下内容（保留 Tailwind 指令，重做 CSS 变量）：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================================================
   心犀AI v3 — 暗色主题设计系统
   ============================================================
   使用 CSS 变量统一管理颜色，这样：
   1. 改一个变量就能全局生效
   2. shadcn/ui 的组件会自动使用这些变量
   3. 未来如果要加浅色主题，只需要覆盖这些变量

   颜色命名规范：
   --background: 页面背景
   --foreground: 主文字颜色
   --card: 卡片背景
   --primary: 主色调（品牌色）
   --muted: 低调/辅助元素颜色
   --border: 边框颜色
*/

:root {
  /* 背景色 */
  --background: 240 10% 4%;          /* #0a0a0f 深空黑 */
  --foreground: 240 5% 94%;          /* #f0f0f5 主文字 */

  /* 卡片 / 面板 */
  --card: 240 8% 8%;                 /* #131318 卡片背景 */
  --card-foreground: 240 5% 94%;

  /* Popover（下拉菜单、弹出层）*/
  --popover: 240 8% 10%;
  --popover-foreground: 240 5% 94%;

  /* 主色调：玫红 → 紫 渐变系列 */
  --primary: 330 78% 50%;            /* #e91e8c 玫红 */
  --primary-foreground: 0 0% 100%;

  /* 次要色 */
  --secondary: 270 50% 40%;          /* #6633cc 紫色 */
  --secondary-foreground: 0 0% 100%;

  /* 低调/辅助 */
  --muted: 240 5% 18%;               /* #2a2a30 */
  --muted-foreground: 240 5% 55%;    /* #8b8b9e */

  /* 强调（未读角标、高亮） */
  --accent: 330 90% 65%;             /* #ff6b9d 亮粉 */
  --accent-foreground: 0 0% 100%;

  /* 危险/错误 */
  --destructive: 0 72% 51%;
  --destructive-foreground: 0 0% 100%;

  /* 边框和输入框 */
  --border: 240 5% 16%;              /* rgba(255,255,255,0.08) 近似 */
  --input: 240 5% 16%;
  --ring: 330 78% 50%;               /* 焦点环颜色，用主色 */

  /* 圆角 */
  --radius: 0.75rem;

  /* 自定义：渐变主题色（用于按钮、Badge 等） */
  --gradient-primary: linear-gradient(135deg, #e91e8c 0%, #9c27b0 100%);
  --gradient-card-border: linear-gradient(135deg, rgba(233,30,140,0.3), rgba(156,39,176,0.3));
}

/* ============================================================
   全局基础样式
*/
* {
  border-color: hsl(var(--border));
}

body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
  /* 全局渐变背景噪点感 */
  background-image:
    radial-gradient(ellipse 80% 50% at 20% 20%, rgba(233,30,140,0.08) 0%, transparent 50%),
    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(156,39,176,0.06) 0%, transparent 50%);
  background-attachment: fixed;
}

/* ============================================================
   磨砂玻璃卡片效果（全局复用类）
*/
.glass-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius);
}

/* 带渐变边框的磨砂卡片 */
.glass-card-glow {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(233, 30, 140, 0.2);
  border-radius: var(--radius);
  box-shadow: 0 0 20px rgba(233, 30, 140, 0.08);
}

/* ============================================================
   滚动条美化（暗色主题）
*/
::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: hsl(var(--muted));
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground));
}

/* ============================================================
   渐变文字（Logo、标题）
*/
.gradient-text {
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ============================================================
   移动端安全区域（底部导航适配）
*/
.pb-safe {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
```

- [ ] **Step 3: 更新 `tailwind.config.ts` 扩展主题**

将 `frontend/tailwind.config.ts` 的 `theme.extend` 部分替换为：

```typescript
extend: {
  colors: {
    border: "hsl(var(--border))",
    input: "hsl(var(--input))",
    ring: "hsl(var(--ring))",
    background: "hsl(var(--background))",
    foreground: "hsl(var(--foreground))",
    primary: {
      DEFAULT: "hsl(var(--primary))",
      foreground: "hsl(var(--primary-foreground))",
    },
    secondary: {
      DEFAULT: "hsl(var(--secondary))",
      foreground: "hsl(var(--secondary-foreground))",
    },
    destructive: {
      DEFAULT: "hsl(var(--destructive))",
      foreground: "hsl(var(--destructive-foreground))",
    },
    muted: {
      DEFAULT: "hsl(var(--muted))",
      foreground: "hsl(var(--muted-foreground))",
    },
    accent: {
      DEFAULT: "hsl(var(--accent))",
      foreground: "hsl(var(--accent-foreground))",
    },
    card: {
      DEFAULT: "hsl(var(--card))",
      foreground: "hsl(var(--card-foreground))",
    },
    popover: {
      DEFAULT: "hsl(var(--popover))",
      foreground: "hsl(var(--popover-foreground))",
    },
  },
  borderRadius: {
    lg: "var(--radius)",
    md: "calc(var(--radius) - 2px)",
    sm: "calc(var(--radius) - 4px)",
  },
  backgroundImage: {
    "gradient-primary": "linear-gradient(135deg, #e91e8c 0%, #9c27b0 100%)",
    "gradient-card": "linear-gradient(135deg, rgba(233,30,140,0.1), rgba(156,39,176,0.1))",
  },
  animation: {
    "fade-in": "fadeIn 0.2s ease-out",
    "slide-up": "slideUp 0.2s ease-out",
    "heartbeat": "heartbeat 1.5s ease-in-out infinite",
  },
  keyframes: {
    fadeIn: {
      "0%": { opacity: "0" },
      "100%": { opacity: "1" },
    },
    slideUp: {
      "0%": { opacity: "0", transform: "translateY(8px)" },
      "100%": { opacity: "1", transform: "translateY(0)" },
    },
    heartbeat: {
      "0%, 100%": { transform: "scale(1)" },
      "50%": { transform: "scale(1.15)" },
    },
  },
},
```

- [ ] **Step 4: 验证编译通过**

```bash
cd E:\study\python\xinxi_ai\frontend
npm run dev
```

访问 http://localhost:5173，页面背景应变为深色。

- [ ] **Step 5: 提交**

```bash
cd E:\study\python\xinxi_ai
git add frontend/
git commit -m "feat: redesign theme system to dark gradient with glass morphism"
```

---

## Task 7：前端 - 更新 Zustand Store + 类型定义

**Files:**
- Create: `frontend/src/stores/appStore.ts`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 创建 Zustand 全局状态**

创建 `frontend/src/stores/appStore.ts`：

```typescript
/**
 * 心犀AI - 全局应用状态（Zustand）
 * ==================================
 *
 * 学习要点 — Zustand vs React Context:
 * - Context 适合低频更新的全局状态（如认证状态、主题）
 * - Zustand 适合高频更新或需要在多处独立订阅的状态
 *   例如：未读消息数（导航栏和聊天室都需要实时更新）
 *
 * Zustand 特点：
 * - 无需 Provider 包裹，直接 import useAppStore 即可用
 * - 只有订阅了某个字段的组件才会在该字段变化时重渲染
 * - 比 Context 性能更好（Context 变化时所有消费者都重渲染）
 */
import { create } from 'zustand'

interface AppState {
  // 未读消息数（用于导航栏角标）
  unreadCount: number
  setUnreadCount: (count: number) => void
  incrementUnread: () => void
  clearUnread: () => void

  // 匹配状态（用于 MatchCenter 组件间共享）
  isMatching: boolean
  setIsMatching: (v: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  unreadCount: 0,
  setUnreadCount: (count) => set({ unreadCount: count }),
  incrementUnread: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
  clearUnread: () => set({ unreadCount: 0 }),

  isMatching: false,
  setIsMatching: (v) => set({ isMatching: v }),
}))
```

- [ ] **Step 2: 更新 `types/index.ts` 添加 `photos` 字段**

在 `frontend/src/types/index.ts` 中找到用户相关类型，添加 `photos` 字段：

```typescript
export interface UserProfile {
  user_id: string
  nickname: string
  gender: string
  age: number
  city: string
  province: string
  education: string
  annual_income: string
  marital_status: string
  mbti: string
  height_cm?: number
  about_me: string
  ideal_partner: string
  hobbies: string
  target_gender: string
  target_age_min: number
  target_age_max: number
  target_city: string
  target_height_min?: number
  target_height_max?: number
  target_education?: string
  avatar_url?: string
  photos: string[]          // 新增：照片列表
  created_at?: string
  // 登录/注册时返回
  access_token?: string
  refresh_token?: string
}

export interface UserPublic {
  user_id: string
  nickname: string
  gender: string
  age: number
  city: string
  province: string
  education: string
  annual_income: string
  marital_status: string
  mbti: string
  height_cm?: number
  about_me: string
  hobbies: string
  avatar_url?: string
  photos: string[]
  created_at?: string
  follower_count: number
  following_count: number
  match_count: number
}

export interface UserListResponse {
  users: UserPublic[]
  total: number
  page: number
  page_size: number
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/stores/ frontend/src/types/
git commit -m "feat: add Zustand store and update user types with photos"
```

---

## Task 8：前端 - 底部导航栏组件

**Files:**
- Create: `frontend/src/components/BottomNav.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 `BottomNav.tsx`**

```typescript
/**
 * 心犀AI - 移动端底部导航栏
 * ============================
 *
 * 学习要点 — 移动端专属导航:
 * - 在 md (768px) 以上隐藏（hidden md:hidden 不对，用 md:hidden）
 * - 固定在屏幕底部（fixed bottom-0），不随页面滚动
 * - 中间按钮（AI访谈）凸起，突出核心功能入口
 * - 使用 env(safe-area-inset-bottom) 适配 iPhone 的 Home 指示条
 *
 * 注意: 底部导航只在登录后显示完整功能；未登录时只显示发现和登录
 */
import { NavLink, useLocation } from 'react-router-dom'
import { Compass, Heart, Sparkles, MessageCircle, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { useAppStore } from '@/stores/appStore'

export default function BottomNav() {
  const { isAuthenticated, user } = useAuth()
  const location = useLocation()
  const unreadCount = useAppStore((s) => s.unreadCount)

  // 登录页和注册页不显示底部导航
  const hideOn = ['/login', '/register']
  if (hideOn.includes(location.pathname)) return null

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-card/80 backdrop-blur-xl border-t border-border pb-safe">
      <div className="flex items-center justify-around h-16 px-2">

        {/* 发现 */}
        <NavLink to="/" end className="flex-1">
          {({ isActive }) => (
            <NavItem icon={<Compass size={22} />} label="发现" isActive={isActive} />
          )}
        </NavLink>

        {/* 匹配（需登录） */}
        <NavLink to="/match" className="flex-1">
          {({ isActive }) => (
            <NavItem
              icon={<Heart size={22} />}
              label="匹配"
              isActive={isActive}
              requireAuth={!isAuthenticated}
            />
          )}
        </NavLink>

        {/* AI 访谈 — 凸起中心按钮 */}
        <NavLink to="/interview" className="flex-1 flex justify-center -mt-5">
          <div className={cn(
            "flex flex-col items-center justify-center",
            "w-14 h-14 rounded-full",
            "bg-gradient-primary shadow-lg shadow-primary/40",
            "transition-transform active:scale-95"
          )}>
            <Sparkles size={24} className="text-white" />
          </div>
        </NavLink>

        {/* 消息（需登录） */}
        <NavLink to="/chat" className="flex-1">
          {({ isActive }) => (
            <NavItem
              icon={
                <div className="relative">
                  <MessageCircle size={22} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-accent text-white text-[10px] font-bold flex items-center justify-center">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </div>
              }
              label="消息"
              isActive={isActive}
              requireAuth={!isAuthenticated}
            />
          )}
        </NavLink>

        {/* 我的（需登录） */}
        <NavLink to={isAuthenticated ? '/profile' : '/login'} className="flex-1">
          {({ isActive }) => (
            <NavItem icon={<User size={22} />} label="我的" isActive={isActive} />
          )}
        </NavLink>

      </div>
    </nav>
  )
}

function NavItem({
  icon,
  label,
  isActive,
  requireAuth = false,
}: {
  icon: React.ReactNode
  label: string
  isActive: boolean
  requireAuth?: boolean
}) {
  return (
    <div className={cn(
      "flex flex-col items-center gap-0.5 py-1 transition-colors",
      isActive ? "text-primary" : "text-muted-foreground",
      requireAuth && "opacity-50"
    )}>
      {icon}
      <span className="text-[10px] font-medium">{label}</span>
    </div>
  )
}
```

- [ ] **Step 2: 在 `App.tsx` 中引入 `BottomNav`，并添加底部 padding 避免内容被遮挡**

在 `App.tsx` 中：

```typescript
import BottomNav from './components/BottomNav'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      {/* md:pb-0 在桌面端不需要底部 padding；移动端给底部导航留空间 */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full pb-20 md:pb-6">
        <Routes>
          {/* 现有路由保持不变，后续添加新路由 */}
          <Route path="/" element={<Home />} />
          <Route path="/user/:userId" element={<UserDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/history" element={
            <ProtectedRoute><MatchHistory /></ProtectedRoute>
          } />
          {/* Phase 2 新增路由 */}
          <Route path="/profile" element={
            <ProtectedRoute><MyProfile /></ProtectedRoute>
          } />
          <Route path="/profile/edit" element={
            <ProtectedRoute><EditProfile /></ProtectedRoute>
          } />
        </Routes>
      </main>
      <BottomNav />
      <footer className="hidden md:block text-center py-4 text-xs text-muted-foreground">
        心犀AI · 基于 Agent + Hybrid RAG 的智能婚恋匹配系统
      </footer>
    </div>
  )
}
```

（`MyProfile` 和 `EditProfile` 的 import 会在 Task 10/11 创建文件后添加）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/BottomNav.tsx frontend/src/App.tsx
git commit -m "feat: add mobile bottom navigation bar"
```

---

## Task 9：前端 - 首页改造（双列瀑布流）

**Files:**
- Modify: `frontend/src/pages/Home.tsx`
- Modify: `frontend/src/components/UserCard.tsx`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 更新 `api/client.ts` 添加用户列表 API**

在 `frontend/src/api/client.ts` 中添加：

```typescript
// ============================================================
// 用户相关 API
// ============================================================

export interface UserListParams {
  gender?: string
  city?: string
  age_min?: number
  age_max?: number
  page?: number
  page_size?: number
}

export const usersApi = {
  /** 获取用户发现列表 */
  list: (params: UserListParams = {}) =>
    apiClient.get<UserListResponse>('/api/users', { params }),

  /** 获取用户公开主页 */
  getPublic: (userId: string) =>
    apiClient.get<UserPublic>(`/api/users/${userId}`),
}
```

- [ ] **Step 2: 改造 `UserCard.tsx` 为暗色磨砂风格**

将 `frontend/src/components/UserCard.tsx` 改造为支持双列布局的暗色卡片：

```typescript
/**
 * 心犀AI - 用户卡片组件（v3 暗色磨砂风格）
 * ============================================
 *
 * 学习要点 — 磨砂玻璃效果:
 * backdrop-filter: blur() 让卡片背景模糊，产生磨砂感
 * 需要父元素有背景（否则没有可模糊的内容），所以 body 的渐变背景很重要
 *
 * 学习要点 — framer-motion:
 * motion.div 是 framer-motion 的动画容器
 * whileHover: 鼠标悬停时触发的动画状态
 * transition: 动画过渡参数
 */
import { motion } from 'framer-motion'
import { MapPin, GraduationCap, Heart } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { UserPublic } from '@/types'
import { cn } from '@/lib/utils'

interface UserCardProps {
  user: UserPublic
  className?: string
}

export default function UserCard({ user, className }: UserCardProps) {
  const navigate = useNavigate()
  const coverImage = user.photos?.[0] || user.avatar_url

  return (
    <motion.div
      className={cn(
        "glass-card cursor-pointer overflow-hidden group",
        className
      )}
      whileHover={{ scale: 1.02, y: -2 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      onClick={() => navigate(`/user/${user.user_id}`)}
    >
      {/* 封面图 */}
      <div className="relative aspect-[3/4] bg-muted overflow-hidden">
        {coverImage ? (
          <img
            src={coverImage}
            alt={user.nickname}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-card">
            <span className="text-5xl font-bold text-primary/30">
              {user.nickname.charAt(0)}
            </span>
          </div>
        )}

        {/* 渐变遮罩（底部文字可读性） */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />

        {/* 底部信息覆层 */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <div className="flex items-end justify-between">
            <div>
              <p className="font-semibold text-white text-sm leading-tight">
                {user.nickname}，{user.age}
              </p>
              <div className="flex items-center gap-1 mt-0.5">
                <MapPin size={10} className="text-white/70" />
                <span className="text-white/70 text-[11px]">{user.city}</span>
              </div>
            </div>
            <Heart size={16} className="text-white/60 group-hover:text-primary transition-colors" />
          </div>
        </div>
      </div>

      {/* 底部标签 */}
      <div className="p-2 flex gap-1.5 flex-wrap">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[11px]">
          <GraduationCap size={10} />
          {user.education}
        </span>
        {user.mbti && user.mbti !== '未知' && (
          <span className="px-2 py-0.5 rounded-full bg-secondary/10 text-secondary text-[11px]">
            {user.mbti}
          </span>
        )}
      </div>
    </motion.div>
  )
}
```

- [ ] **Step 3: 改造 `Home.tsx` 为双列瀑布流**

将 `frontend/src/pages/Home.tsx` 替换为：

```typescript
/**
 * 心犀AI - 发现页（v3 小红书风格双列瀑布流）
 * ==============================================
 *
 * 学习要点 — CSS Grid 双列布局:
 * grid-cols-2: 两列，gap-3: 列间距
 * 这比 masonry 布局简单（真正的 masonry 需要 JS），
 * 但对于等比例卡片（aspect-[3/4]）效果完全相同
 *
 * 学习要点 — 无限滚动基础:
 * 当前用"加载更多"按钮替代无限滚动，
 * 原因：无限滚动需要 IntersectionObserver，Phase 5 可以升级
 */
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { SlidersHorizontal, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import UserCard from '@/components/UserCard'
import { usersApi } from '@/api/client'
import type { UserPublic } from '@/types'

export default function Home() {
  const [users, setUsers] = useState<UserPublic[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [genderFilter, setGenderFilter] = useState<string>('')
  const [citySearch, setCitySearch] = useState('')

  const fetchUsers = async (p = 1, reset = false) => {
    setLoading(true)
    try {
      const res = await usersApi.list({
        page: p,
        page_size: 20,
        gender: genderFilter || undefined,
        city: citySearch || undefined,
      })
      const data = res.data
      setTotal(data.total)
      setUsers(prev => reset ? data.users : [...prev, ...data.users])
      setPage(p)
    } catch (e) {
      console.error('加载用户列表失败', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers(1, true)
  }, [genderFilter])

  const handleSearch = () => fetchUsers(1, true)

  return (
    <div className="space-y-4">
      {/* 搜索和筛选栏 */}
      <div className="flex gap-2 sticky top-16 z-10 py-2 bg-background/80 backdrop-blur-md -mx-4 px-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索城市..."
            value={citySearch}
            onChange={e => setCitySearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            className="pl-9 bg-card border-border h-9 text-sm"
          />
        </div>
        <div className="flex gap-1">
          {(['', 'female', 'male'] as const).map(g => (
            <Button
              key={g}
              size="sm"
              variant={genderFilter === g ? 'default' : 'outline'}
              onClick={() => setGenderFilter(g)}
              className="h-9 px-3 text-xs"
            >
              {g === '' ? '全部' : g === 'female' ? '女生' : '男生'}
            </Button>
          ))}
        </div>
      </div>

      {/* 用户计数 */}
      {!loading && (
        <p className="text-xs text-muted-foreground">
          共 {total} 位用户
        </p>
      )}

      {/* 双列瀑布流 */}
      {loading && users.length === 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="glass-card animate-pulse aspect-[3/4] rounded-xl" />
          ))}
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.05 } },
          }}
        >
          {users.map(user => (
            <motion.div
              key={user.user_id}
              variants={{
                hidden: { opacity: 0, y: 16 },
                visible: { opacity: 1, y: 0 },
              }}
            >
              <UserCard user={user} />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* 加载更多 */}
      {users.length < total && (
        <div className="flex justify-center pt-4">
          <Button
            variant="outline"
            onClick={() => fetchUsers(page + 1)}
            disabled={loading}
            className="border-border"
          >
            {loading ? '加载中...' : '加载更多'}
          </Button>
        </div>
      )}

      {!loading && users.length === 0 && (
        <div className="text-center py-20 text-muted-foreground">
          <SlidersHorizontal size={40} className="mx-auto mb-3 opacity-30" />
          <p>暂时没有找到符合条件的用户</p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: 更新 Navbar，替换 emoji 为 Lucide 图标，适配暗色主题**

将 `frontend/src/components/Navbar.tsx` 中的 emoji 导航链接部分改为 Lucide 图标：

```typescript
import { Compass, Heart, History, Sparkles } from 'lucide-react'

const BASE_LINKS = [
  { to: '/', label: '发现', icon: <Compass size={16} />, end: true },
] as const

const AUTH_LINKS = [
  { to: '/history', label: '历史', icon: <History size={16} /> },
  { to: '/match', label: '匹配', icon: <Heart size={16} /> },
] as const
```

同时更新 Navbar 的容器样式为暗色：

```typescript
<nav className="sticky top-0 z-50 bg-card/80 backdrop-blur-xl border-b border-border">
```

Logo 文字使用渐变类：

```typescript
<span className="text-xl font-bold gradient-text">心犀AI</span>
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/
git commit -m "feat: redesign Home page with masonry grid and update Navbar to dark theme"
```

---

## Task 10：前端 - 图片上传组件

**Files:**
- Create: `frontend/src/components/ImageUpload.tsx`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 在 `client.ts` 添加上传 API 函数**

在 `frontend/src/api/client.ts` 中添加：

```typescript
export const authApi = {
  // ... 现有的 login、register 等函数

  /** 上传头像 */
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<{ url: string; message: string }>('/api/auth/me/avatar', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /** 上传照片 */
  uploadPhoto: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<{ url: string; photos: string[] }>('/api/auth/me/photos', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /** 删除照片 */
  deletePhoto: (index: number) =>
    apiClient.delete<{ photos: string[] }>(`/api/auth/me/photos/${index}`),

  /** 更新个人资料 */
  updateProfile: (data: Partial<UserProfile>) =>
    apiClient.put<UserProfile>('/api/auth/me', data),
}
```

- [ ] **Step 2: 创建 `ImageUpload.tsx` 组件**

```typescript
/**
 * 心犀AI - 图片上传组件
 * =======================
 *
 * 功能：
 * - 点击上传区域或拖拽上传图片
 * - 上传前用 browser-image-compression 压缩到 ≤800px、≤500KB
 * - 支持预览、删除
 * - 限制最多 maxCount 张
 *
 * 学习要点 — browser-image-compression:
 *   import imageCompression from 'browser-image-compression'
 *   const compressed = await imageCompression(file, { maxSizeMB: 0.5, maxWidthOrHeight: 800 })
 *   这在浏览器端完成压缩，不需要后端参与，节省服务器带宽
 *
 * 学习要点 — FileReader:
 *   用于在上传前读取本地图片并预览，无需服务器往返
 */
import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import imageCompression from 'browser-image-compression'
import { Upload, X, Plus, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { authApi } from '@/api/client'

interface ImageUploadProps {
  /** 当前图片 URL 列表 */
  value: string[]
  /** 图片列表变化回调 */
  onChange: (urls: string[]) => void
  /** 最大图片数量 */
  maxCount?: number
  /** 是否是头像上传模式（单图，圆形） */
  isAvatar?: boolean
  className?: string
}

const COMPRESS_OPTIONS = {
  maxSizeMB: 0.5,         // 最大 500KB
  maxWidthOrHeight: 800,  // 最大边长 800px
  useWebWorker: true,     // 使用 Web Worker 避免阻塞 UI
}

export default function ImageUpload({
  value,
  onChange,
  maxCount = 6,
  isAvatar = false,
  className,
}: ImageUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    if (value.length >= maxCount) return

    const file = files[0]
    setUploading(true)

    try {
      // 1. 压缩图片（浏览器端处理，不占服务器资源）
      const compressed = await imageCompression(file, COMPRESS_OPTIONS)

      // 2. 上传到服务器
      if (isAvatar) {
        const res = await authApi.uploadAvatar(compressed as File)
        onChange([res.data.url])
      } else {
        const res = await authApi.uploadPhoto(compressed as File)
        onChange(res.data.photos)
      }
    } catch (e) {
      console.error('图片上传失败', e)
      alert('图片上传失败，请重试')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async (index: number) => {
    if (isAvatar) {
      onChange([])
      return
    }
    setUploadingIndex(index)
    try {
      const res = await authApi.deletePhoto(index)
      onChange(res.data.photos)
    } catch (e) {
      console.error('删除失败', e)
    } finally {
      setUploadingIndex(null)
    }
  }

  if (isAvatar) {
    const avatarUrl = value[0]
    return (
      <div className={cn("relative w-24 h-24", className)}>
        <div
          className="w-full h-full rounded-full overflow-hidden bg-muted border-2 border-primary/30 cursor-pointer hover:border-primary/60 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="头像" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground">
              {uploading ? <Loader2 size={24} className="animate-spin" /> : <Upload size={24} />}
            </div>
          )}
        </div>
        {avatarUrl && (
          <button
            onClick={() => handleDelete(0)}
            className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-destructive text-white flex items-center justify-center text-xs"
          >
            <X size={12} />
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={e => handleFileSelect(e.target.files)}
        />
      </div>
    )
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div className="grid grid-cols-3 gap-2">
        <AnimatePresence>
          {value.map((url, i) => (
            <motion.div
              key={url}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="relative aspect-square rounded-lg overflow-hidden group"
            >
              <img src={url} alt={`照片${i + 1}`} className="w-full h-full object-cover" />
              <button
                onClick={() => handleDelete(i)}
                disabled={uploadingIndex === i}
                className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                {uploadingIndex === i ? <Loader2 size={10} className="animate-spin" /> : <X size={10} />}
              </button>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* 上传按钮 */}
        {value.length < maxCount && (
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="aspect-square rounded-lg border-2 border-dashed border-border hover:border-primary/50 flex flex-col items-center justify-center gap-1 transition-colors text-muted-foreground hover:text-primary"
          >
            {uploading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <>
                <Plus size={20} />
                <span className="text-[11px]">{value.length}/{maxCount}</span>
              </>
            )}
          </button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={e => handleFileSelect(e.target.files)}
      />
    </div>
  )
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ImageUpload.tsx frontend/src/api/client.ts
git commit -m "feat: add ImageUpload component with browser-side compression"
```

---

## Task 11：前端 - 个人中心页面

**Files:**
- Create: `frontend/src/pages/MyProfile.tsx`

- [ ] **Step 1: 创建 `MyProfile.tsx`**

```typescript
/**
 * 心犀AI - 个人中心页面
 * =======================
 *
 * 展示：
 * - 头像 + 基本信息
 * - 数据统计：匹配次数、关注数、粉丝数
 * - 照片墙
 * - 快捷操作：寻找缘分、AI访谈、编辑资料
 *
 * 学习要点 — useAuth Hook:
 * - user 对象从 AuthContext 获取，整个应用都可以直接读取
 * - 修改 user 信息后，需要调用 AuthContext 的 refreshUser 更新全局状态
 */
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Pencil, Heart, Sparkles, MapPin, GraduationCap, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

export default function MyProfile() {
  const { user } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  const stats = [
    { label: '匹配次数', value: 0, icon: Heart },
    { label: '关注', value: 0, icon: Users },
    { label: '粉丝', value: 0, icon: Users },
  ]

  return (
    <div className="max-w-lg mx-auto space-y-4">
      {/* 个人信息卡 */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card-glow p-6"
      >
        <div className="flex items-start gap-4">
          {/* 头像 */}
          <Avatar className="w-20 h-20 ring-2 ring-primary/30">
            <AvatarImage src={user.avatar_url} />
            <AvatarFallback className="bg-gradient-primary text-white text-2xl font-bold">
              {user.nickname.charAt(0)}
            </AvatarFallback>
          </Avatar>

          {/* 基本信息 */}
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold">{user.nickname}</h1>
            <p className="text-sm text-muted-foreground mt-0.5">{user.user_id}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin size={12} /> {user.city}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <GraduationCap size={12} /> {user.education}
              </span>
              {user.mbti && user.mbti !== '未知' && (
                <span className="px-2 py-0.5 rounded-full bg-secondary/20 text-secondary text-xs">
                  {user.mbti}
                </span>
              )}
            </div>
          </div>

          {/* 编辑按钮 */}
          <Button
            size="icon"
            variant="ghost"
            onClick={() => navigate('/profile/edit')}
            className="text-muted-foreground hover:text-primary"
          >
            <Pencil size={18} />
          </Button>
        </div>

        {/* 关于我 */}
        {user.about_me && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed line-clamp-3">
            {user.about_me}
          </p>
        )}
      </motion.div>

      {/* 数据统计 */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="glass-card p-4"
      >
        <div className="grid grid-cols-3 divide-x divide-border">
          {stats.map(({ label, value }) => (
            <div key={label} className="flex flex-col items-center py-1">
              <span className="text-2xl font-bold gradient-text">{value}</span>
              <span className="text-xs text-muted-foreground mt-0.5">{label}</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* 照片墙 */}
      {(user.photos?.length ?? 0) > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-4 space-y-3"
        >
          <h2 className="text-sm font-semibold text-muted-foreground">我的照片</h2>
          <div className="grid grid-cols-3 gap-2">
            {user.photos!.map((url, i) => (
              <div key={i} className="aspect-square rounded-lg overflow-hidden">
                <img src={url} alt={`照片${i + 1}`} className="w-full h-full object-cover" />
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* 快捷操作 */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-2 gap-3"
      >
        <Button
          onClick={() => navigate('/match')}
          className="h-14 bg-gradient-primary text-white font-medium flex flex-col gap-0.5 rounded-xl"
        >
          <Heart size={20} />
          <span className="text-xs">寻找缘分</span>
        </Button>
        <Button
          onClick={() => navigate('/interview')}
          variant="outline"
          className="h-14 border-primary/30 text-primary hover:bg-primary/10 flex flex-col gap-0.5 rounded-xl"
        >
          <Sparkles size={20} />
          <span className="text-xs">AI 访谈</span>
        </Button>
      </motion.div>
    </div>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/MyProfile.tsx
git commit -m "feat: add MyProfile personal center page"
```

---

## Task 12：前端 - 编辑资料页面

**Files:**
- Create: `frontend/src/pages/EditProfile.tsx`

- [ ] **Step 1: 创建 `EditProfile.tsx`**

```typescript
/**
 * 心犀AI - 编辑资料页面
 * =======================
 *
 * 分三个区块（Tabs）：
 * 1. 基本信息：头像、昵称、年龄、城市、身高、学历等
 * 2. 择偶偏好：期望对方的性别、年龄、城市、身高、学历
 * 3. 自我介绍：关于我、理想的Ta、兴趣爱好
 *
 * 学习要点 — 部分更新:
 * 只发送用户修改过的字段（form.formState.dirtyFields）
 * 减少网络传输，避免覆盖未修改的字段
 *
 * 学习要点 — 乐观更新:
 * 保存成功后立刻更新 AuthContext 中的 user 状态（不需要重新登录）
 * 这样导航栏的昵称/头像也会立刻更新
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Save, ArrowLeft, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import ImageUpload from '@/components/ImageUpload'
import { useAuth } from '@/contexts/AuthContext'
import { authApi } from '@/api/client'
import type { UserProfile } from '@/types'

const EDUCATION_OPTIONS = ['高中及以下', '大专', '本科', '硕士', '博士']
const MBTI_OPTIONS = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP',
                      'ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP','未知']
const INCOME_OPTIONS = ['未填写', '5万以下', '5-10万', '10-20万', '20-50万', '50万以上']

export default function EditProfile() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [avatarUrls, setAvatarUrls] = useState<string[]>(
    user?.avatar_url ? [user.avatar_url] : []
  )
  const [photos, setPhotos] = useState<string[]>(user?.photos || [])

  const { register, handleSubmit, setValue, watch, formState: { isDirty, dirtyFields } } = useForm<Partial<UserProfile>>({
    defaultValues: {
      nickname: user?.nickname,
      age: user?.age,
      city: user?.city,
      province: user?.province,
      height_cm: user?.height_cm,
      education: user?.education,
      annual_income: user?.annual_income,
      marital_status: user?.marital_status,
      mbti: user?.mbti,
      about_me: user?.about_me,
      ideal_partner: user?.ideal_partner,
      hobbies: user?.hobbies,
      target_gender: user?.target_gender,
      target_age_min: user?.target_age_min,
      target_age_max: user?.target_age_max,
      target_city: user?.target_city,
      target_height_min: user?.target_height_min,
      target_height_max: user?.target_height_max,
      target_education: user?.target_education,
    },
  })

  const onSubmit = async (data: Partial<UserProfile>) => {
    setSaving(true)
    setError(null)
    try {
      // 只发送 dirty 字段（用户实际修改的）
      const changedFields = Object.fromEntries(
        Object.entries(data).filter(([k]) => dirtyFields[k as keyof typeof dirtyFields])
      )
      if (Object.keys(changedFields).length > 0) {
        const res = await authApi.updateProfile(changedFields)
        updateUser(res.data)  // 更新全局 AuthContext
      }
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto space-y-4">
      {/* 页头 */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
        </Button>
        <h1 className="text-lg font-semibold">编辑资料</h1>
        {saved && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className="ml-auto flex items-center gap-1 text-sm text-green-400"
          >
            <CheckCircle size={14} /> 已保存
          </motion.div>
        )}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <Tabs defaultValue="basic" className="space-y-4">
          <TabsList className="grid grid-cols-3 w-full bg-card">
            <TabsTrigger value="basic">基本信息</TabsTrigger>
            <TabsTrigger value="preference">择偶偏好</TabsTrigger>
            <TabsTrigger value="intro">自我介绍</TabsTrigger>
          </TabsList>

          {/* === 基本信息 === */}
          <TabsContent value="basic" className="space-y-4">
            <div className="glass-card p-4 space-y-4">
              {/* 头像上传 */}
              <div className="flex flex-col items-center gap-2">
                <ImageUpload
                  value={avatarUrls}
                  onChange={setAvatarUrls}
                  maxCount={1}
                  isAvatar
                />
                <span className="text-xs text-muted-foreground">点击更换头像</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">昵称</Label>
                  <Input className="bg-muted/30 border-border" {...register('nickname')} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">年龄</Label>
                  <Input type="number" className="bg-muted/30 border-border" {...register('age', { valueAsNumber: true })} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">城市</Label>
                  <Input className="bg-muted/30 border-border" {...register('city')} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">省份</Label>
                  <Input className="bg-muted/30 border-border" {...register('province')} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">身高(cm)</Label>
                  <Input type="number" className="bg-muted/30 border-border" {...register('height_cm', { valueAsNumber: true })} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">学历</Label>
                  <Select onValueChange={v => setValue('education', v, { shouldDirty: true })} defaultValue={user?.education}>
                    <SelectTrigger className="bg-muted/30 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {EDUCATION_OPTIONS.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">年收入</Label>
                  <Select onValueChange={v => setValue('annual_income', v, { shouldDirty: true })} defaultValue={user?.annual_income}>
                    <SelectTrigger className="bg-muted/30 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {INCOME_OPTIONS.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">MBTI</Label>
                  <Select onValueChange={v => setValue('mbti', v, { shouldDirty: true })} defaultValue={user?.mbti}>
                    <SelectTrigger className="bg-muted/30 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MBTI_OPTIONS.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* 照片上传 */}
            <div className="glass-card p-4 space-y-3">
              <Label className="text-sm font-medium">我的照片（最多6张）</Label>
              <ImageUpload value={photos} onChange={setPhotos} maxCount={6} />
            </div>
          </TabsContent>

          {/* === 择偶偏好 === */}
          <TabsContent value="preference" className="space-y-4">
            <div className="glass-card p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">期望性别</Label>
                  <Select onValueChange={v => setValue('target_gender', v, { shouldDirty: true })} defaultValue={user?.target_gender}>
                    <SelectTrigger className="bg-muted/30 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="female">女性</SelectItem>
                      <SelectItem value="male">男性</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">期望城市</Label>
                  <Input className="bg-muted/30 border-border" placeholder="不限" {...register('target_city')} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">年龄下限</Label>
                  <Input type="number" className="bg-muted/30 border-border" {...register('target_age_min', { valueAsNumber: true })} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">年龄上限</Label>
                  <Input type="number" className="bg-muted/30 border-border" {...register('target_age_max', { valueAsNumber: true })} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">身高下限(cm)</Label>
                  <Input type="number" className="bg-muted/30 border-border" {...register('target_height_min', { valueAsNumber: true })} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">最低学历</Label>
                  <Select onValueChange={v => setValue('target_education', v, { shouldDirty: true })} defaultValue={user?.target_education}>
                    <SelectTrigger className="bg-muted/30 border-border">
                      <SelectValue placeholder="不限" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">不限</SelectItem>
                      {EDUCATION_OPTIONS.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* === 自我介绍 === */}
          <TabsContent value="intro" className="space-y-4">
            <div className="glass-card p-4 space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs">关于我</Label>
                <Textarea
                  className="bg-muted/30 border-border min-h-[100px] resize-none"
                  placeholder="介绍一下自己..."
                  {...register('about_me')}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">理想的Ta</Label>
                <Textarea
                  className="bg-muted/30 border-border min-h-[100px] resize-none"
                  placeholder="描述你心目中的另一半..."
                  {...register('ideal_partner')}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">兴趣爱好</Label>
                <Input
                  className="bg-muted/30 border-border"
                  placeholder="例如：旅行、摄影、咖啡（逗号分隔）"
                  {...register('hobbies')}
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <Button
          type="submit"
          disabled={saving || (!isDirty && avatarUrls[0] === user?.avatar_url)}
          className="w-full mt-4 bg-gradient-primary text-white h-12 rounded-xl font-medium"
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              保存中...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Save size={18} /> 保存资料
            </span>
          )}
        </Button>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: 在 `AuthContext.tsx` 添加 `updateUser` 方法**

在 `frontend/src/contexts/AuthContext.tsx` 中，给 context 添加 `updateUser` 方法，让编辑资料保存后可以实时更新全局 user 状态：

```typescript
// 在 AuthContextType 接口中添加:
updateUser: (data: Partial<UserProfile>) => void

// 在 AuthProvider 的实现中添加:
const updateUser = useCallback((data: Partial<UserProfile>) => {
  setUser(prev => prev ? { ...prev, ...data } : null)
}, [])

// 在 value 中加入:
value={{ user, login, register, logout, isAuthenticated, isLoading, updateUser }}
```

- [ ] **Step 3: 完善 App.tsx 中的 MyProfile 和 EditProfile 路由 import**

在 `frontend/src/App.tsx` 顶部添加：

```typescript
import MyProfile from './pages/MyProfile'
import EditProfile from './pages/EditProfile'
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/EditProfile.tsx frontend/src/contexts/AuthContext.tsx frontend/src/App.tsx
git commit -m "feat: add EditProfile page with image upload and partial update"
```

---

## Task 13：联调验证 + 清理

- [ ] **Step 1: 启动后端**

```bash
cd E:\study\python\xinxi_ai\backend
python run.py
```

确认启动日志无报错，`/uploads` 静态文件已挂载。

- [ ] **Step 2: 启动前端**

```bash
cd E:\study\python\xinxi_ai\frontend
npm run dev
```

- [ ] **Step 3: 验证清单**

逐项测试：

| 测试项 | 预期结果 |
|---|---|
| 访问 http://localhost:5173 | 深色背景，双列瀑布流发现页 |
| 手机窗口宽度（< 768px） | 底部导航栏出现 |
| 点击任意用户卡片 | 悬浮时 scale(1.02) 动效 |
| 登录后访问 /profile | 个人中心页正常显示 |
| 点击"编辑资料" | 跳转编辑页，三个 Tab 正常切换 |
| 上传头像 | 图片压缩后上传，头像栏更新 |
| 上传照片 | 最多 6 张，超出时按钮消失 |
| 修改昵称并保存 | Navbar 中的昵称实时更新 |
| 保存后刷新页面 | 修改持久化（数据库已保存） |

- [ ] **Step 4: 最终提交**

```bash
cd E:\study\python\xinxi_ai
git add .
git commit -m "feat: complete Phase 2 - user center, image upload, and full UI redesign"
```

---

## 自检清单

### Spec 覆盖检查

| 需求 | 对应 Task |
|---|---|
| PUT /api/auth/me 编辑接口 | Task 4（已存在，添加 ChromaDB 同步） |
| 头像上传 POST /api/auth/me/avatar | Task 4 |
| 照片上传 POST /api/auth/me/photos | Task 4 |
| 照片删除 DELETE /api/auth/me/photos/{index} | Task 4 |
| GET /api/users 发现列表 | Task 5 |
| GET /api/users/{user_id} 公开主页 | Task 5 |
| ChromaDB 后台异步同步 | Task 3 + Task 4 |
| 暗色渐变主题系统 | Task 6 |
| 图标替换为 Lucide | Task 9（Navbar）+ 各新增组件 |
| 移动端底部导航栏 | Task 8 |
| 首页双列瀑布流 | Task 9 |
| 个人中心页面 | Task 11 |
| 编辑资料页面 | Task 12 |
| 图片上传组件（含压缩） | Task 10 |
| framer-motion 动效 | Task 6 + Task 9 + Task 11/12 |
| Zustand 全局状态 | Task 7 |

所有 Spec 需求均有对应 Task，无遗漏。
