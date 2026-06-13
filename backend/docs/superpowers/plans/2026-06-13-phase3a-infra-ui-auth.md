# Phase 3a — 基础设施 · UI 重构 · 权限与注册 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成数据库迁移（新增4字段+3张表）、20位种子用户、INS风UI重构、简化注册流程、权限控制门，为 Phase 3b（心动TA们+缘分分析）打好基础。

**Architecture:** 后端通过 Alembic 迁移扩展 PostgreSQL schema，更新 SQLAlchemy 模型和 FastAPI schemas，新增属相/星座计算工具；前端全面替换 CSS 变量为 INS 深靛蓝色系，更新注册页，在路由层植入 `profile_complete` 检查。

**Tech Stack:** Python/FastAPI/SQLAlchemy 2.0/Alembic/psycopg3 · React/TypeScript/Tailwind v4/framer-motion/Lucide React

---

## 文件清单

### 后端（新建）
- `backend/core/utils/zodiac.py` — 星座/属相计算工具
- `backend/scripts/seed_users.py` — 20位用户种子脚本
- `backend/alembic/versions/2026_06_13_1500-002_phase3_schema.py` — 迁移文件

### 后端（修改）
- `backend/core/database/models.py` — 添加新字段和3张表的 ORM 模型
- `backend/api/schemas.py` — 更新 UserCreate（简化注册），UserResponse（新字段）
- `backend/api/routers/auth.py` — 更新 register 端点，添加 profile_complete 自动计算

### 前端（修改）
- `frontend/src/index.css` — 全面替换为 INS 风色系
- `frontend/src/components/UserCard.tsx` — 添加心动按钮（占位，Phase 3b 接通逻辑）
- `frontend/src/components/Navbar.tsx` — 适配新色系，添加通知入口占位
- `frontend/src/components/ProfileCompleteBanner.tsx` — 新建，引导横幅
- `frontend/src/pages/Register.tsx` — 改为4字段简化注册
- `frontend/src/pages/Home.tsx` — 添加横幅，调整3列布局
- `frontend/src/contexts/AuthContext.tsx` — 同步 profile_complete 字段
- `frontend/src/types/index.ts` — 添加 profile_complete/zodiac/birth_date 字段

---

## Task 1：属相/星座计算工具

**Files:**
- Create: `backend/core/utils/zodiac.py`

- [ ] **Step 1: 写 zodiac.py**

```python
"""
属相（Chinese Zodiac）和星座（Western Zodiac）计算工具。
根据生日自动计算，无需外部 API。
"""
from datetime import date


CHINESE_ZODIAC = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

WESTERN_ZODIAC = [
    (1, 20, "摩羯座"),
    (2, 19, "水瓶座"),
    (3, 21, "双鱼座"),
    (4, 20, "白羊座"),
    (5, 21, "金牛座"),
    (6, 21, "双子座"),
    (7, 23, "巨蟹座"),
    (8, 23, "狮子座"),
    (9, 23, "处女座"),
    (10, 23, "天秤座"),
    (11, 22, "天蝎座"),
    (12, 22, "射手座"),
    (12, 31, "摩羯座"),
]


def get_chinese_zodiac(birth_date: date) -> str:
    """计算属相（以1900年为庚子鼠年基准）"""
    base_year = 1900  # 庚子鼠年
    offset = (birth_date.year - base_year) % 12
    return CHINESE_ZODIAC[offset]


def get_zodiac_sign(birth_date: date) -> str:
    """计算西方星座"""
    month = birth_date.month
    day = birth_date.day
    for end_month, end_day, sign in WESTERN_ZODIAC:
        if month < end_month or (month == end_month and day <= end_day):
            return sign
    return "摩羯座"


def update_zodiac_fields(user, birth_date: date) -> None:
    """在更新 birth_date 时同步写入 zodiac_sign 和 chinese_zodiac"""
    user.birth_date = birth_date
    user.zodiac_sign = get_zodiac_sign(birth_date)
    user.chinese_zodiac = get_chinese_zodiac(birth_date)
    # 同步更新 age
    from datetime import date as date_
    today = date_.today()
    user.age = (
        today.year - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
```

- [ ] **Step 2: 快速验证（Python 交互或单独运行）**

```bash
cd backend
python -c "
from datetime import date
from core.utils.zodiac import get_chinese_zodiac, get_zodiac_sign
print(get_chinese_zodiac(date(1995, 3, 15)))   # 猪
print(get_zodiac_sign(date(1995, 3, 15)))       # 双鱼座
"
```

预期：无报错，输出"猪"和"双鱼座"

- [ ] **Step 3: Commit**

```bash
git add backend/core/utils/zodiac.py
git commit -m "feat: add zodiac/chinese zodiac calculation utility"
```

---

## Task 2：更新 SQLAlchemy 模型

**Files:**
- Modify: `backend/core/database/models.py`

- [ ] **Step 1: 在 User 类中添加新字段**

在 `backend/core/database/models.py` 中，`User` 类的"元数据"字段块之前，添加：

```python
# 在 === 基本信息 === 块中，age 改为可空
age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

# 在 === 认证字段 === 之后添加
# === 星座/属相/生日 ===
birth_date: Mapped[Optional[date]] = mapped_column(
    Date, nullable=True, comment="生日，用于自动计算星座和属相",
)
zodiac_sign: Mapped[Optional[str]] = mapped_column(
    String(10), nullable=True, comment="西方星座",
)
chinese_zodiac: Mapped[Optional[str]] = mapped_column(
    String(10), nullable=True, comment="属相",
)

# === 资料完善状态 ===
profile_complete: Mapped[bool] = mapped_column(
    Boolean, default=False,
    comment="是否完成资料填写，True 才能出现在发现列表并发起匹配",
)
```

在 User 的 `to_dict()` 方法中添加这些字段：

```python
"birth_date": self.birth_date.isoformat() if self.birth_date else None,
"zodiac_sign": self.zodiac_sign,
"chinese_zodiac": self.chinese_zodiac,
"profile_complete": self.profile_complete,
```

在文件顶部导入中添加 `date`：

```python
from datetime import datetime, date
```

- [ ] **Step 2: 添加 FateCandidate 模型**

在 `Blacklist` 类之后追加：

```python
# ============================================================
# fate_candidates - 心动 TA 们清单
# ============================================================

class FateCandidate(Base):
    """
    心动 TA 们清单 - 用户手动收藏的缘分候选者。

    学习要点：
    - UniqueConstraint 防止同一对用户重复加入
    - CheckConstraint 防止自己把自己加入清单
    - 与 fate_analyses 共同构成「缘分分析」功能的数据基础
    """
    __tablename__ = "fate_candidates"
    __table_args__ = (
        UniqueConstraint("user_id", "candidate_id", name="uq_fate_candidate"),
        CheckConstraint("user_id != candidate_id", name="ck_fate_no_self"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    candidate: Mapped["User"] = relationship(foreign_keys=[candidate_id])
```

- [ ] **Step 3: 添加 FateAnalysis 模型**

```python
# ============================================================
# fate_analyses - 缘分分析记录
# ============================================================

class FateAnalysis(Base):
    """
    缘分分析记录 - 存储 AI 生成的缘分分析报告。

    学习要点：
    - analysis_type 区分两层分析：第一层 group_overview，第二层三条路径
    - result 用 JSONB 存完整报告（Markdown 文本 + 结构化评分）
    - match_params_snapshot 保存分析时的偏好参数，便于复盘
    - status 支持异步分析状态追踪（Agent 流式输出期间为 pending）

    Agent 集成：
    - FateAnalysisAgent 完成后更新 result 和 status
    - 前端通过 SSE 流式接收分析过程
    """
    __tablename__ = "fate_analyses"
    __table_args__ = (
        Index("idx_fate_analyses_initiator", "initiator_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    initiator_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    analysis_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="group_overview | deep_compatibility | comm_advice | comparison",
    )
    candidate_ids: Mapped[list] = mapped_column(JSONB, default=list)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    match_params_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    parent_analysis_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    initiator: Mapped["User"] = relationship(foreign_keys=[initiator_id])
```

- [ ] **Step 4: 添加 Notification 模型**

```python
# ============================================================
# notifications - 通知表
# ============================================================

class Notification(Base):
    """
    通知表 - 系统和互动事件通知。

    通知类型：
    - fate_added:    有人把你加入心动清单
    - mutual_fate:   双向心动（你也把对方加了）
    - analysis_done: 缘分分析完成
    - new_message:   新私信
    """
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_recipient", "recipient_id", "is_read", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    notif_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    recipient_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=True,
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    recipient: Mapped["User"] = relationship(foreign_keys=[recipient_id])
    actor: Mapped[Optional["User"]] = relationship(foreign_keys=[actor_id])
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/database/models.py
git commit -m "feat: add FateCandidate, FateAnalysis, Notification models; extend User with zodiac/profile_complete"
```

---

## Task 3：Alembic 迁移

**Files:**
- Create: `backend/alembic/versions/2026_06_13_1500-002_phase3_schema.py`

- [ ] **Step 1: 生成迁移脚本**

```bash
cd backend
alembic revision --autogenerate -m "phase3_schema"
```

- [ ] **Step 2: 检查生成的迁移文件**

生成的文件位于 `backend/alembic/versions/`，文件名含 `phase3_schema`。打开验证：

1. `upgrade()` 应包含：
   - `ALTER TABLE xinxi.users ADD COLUMN profile_complete BOOLEAN`
   - `ALTER TABLE xinxi.users ADD COLUMN birth_date DATE`
   - `ALTER TABLE xinxi.users ADD COLUMN zodiac_sign VARCHAR(10)`
   - `ALTER TABLE xinxi.users ADD COLUMN chinese_zodiac VARCHAR(10)`
   - `ALTER TABLE xinxi.users ALTER COLUMN age DROP NOT NULL`（age 改可空）
   - `CREATE TABLE xinxi.fate_candidates (...)`
   - `CREATE TABLE xinxi.fate_analyses (...)`
   - `CREATE TABLE xinxi.notifications (...)`

2. 若出现 Langfuse 相关的 DROP 语句，立即删除（`include_object` 过滤器应已拦截）

3. 确认 `profile_complete` 添加时带 `server_default='false'`（已有行不报错）

- [ ] **Step 3: 执行迁移**

```bash
cd backend
alembic upgrade head
```

预期输出末尾：`Running upgrade ... -> ..., phase3_schema`，无报错。

- [ ] **Step 4: 验证**

```bash
python scripts/check_tables.py
```

确认新表存在。若 `check_tables.py` 不支持，可用：

```bash
python -c "
from core.database.session import engine
from sqlalchemy import inspect, text
with engine.connect() as conn:
    result = conn.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_schema='xinxi'\"))
    print([r[0] for r in result])
"
```

预期包含：`users, match_records, match_candidates, follow_relationships, conversations, messages, blacklist, fate_candidates, fate_analyses, notifications`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: alembic migration phase3 - add fate tables and user zodiac fields"
```

---

## Task 4：更新 API Schemas

**Files:**
- Modify: `backend/api/schemas.py`

- [ ] **Step 1: 更新 UserCreate（简化注册）**

找到 `UserCreate` 类，替换为：

```python
class UserCreate(BaseModel):
    """注册请求体 - 仅需4个字段，其他资料可稍后编辑"""
    nickname: str = Field(..., min_length=2, max_length=20)
    gender: str = Field(..., pattern="^(男|女)$")
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    password: str = Field(..., min_length=8, max_length=50)
```

- [ ] **Step 2: 更新 UserResponse（添加新字段）**

在 `UserResponse` 中添加：

```python
birth_date: Optional[str] = None
zodiac_sign: Optional[str] = None
chinese_zodiac: Optional[str] = None
profile_complete: bool = False
```

- [ ] **Step 3: 更新 UserUpdateRequest（支持 birth_date）**

找到 `UserUpdateRequest`（或 `UserUpdate`），添加：

```python
birth_date: Optional[str] = None  # 格式: YYYY-MM-DD
```

- [ ] **Step 4: 添加 FateCandidate、FateAnalysis、Notification schemas**

在文件末尾追加：

```python
# ── 心动清单 ──────────────────────────────────────────────
class FateCandidateResponse(BaseModel):
    candidate_id: str
    note: Optional[str] = None
    added_at: str
    candidate: "UserPublicResponse"

class FateCandidateListResponse(BaseModel):
    items: list[FateCandidateResponse]
    total: int

# ── 缘分分析 ──────────────────────────────────────────────
class FateAnalysisCreate(BaseModel):
    analysis_type: str = Field(
        ...,
        pattern="^(group_overview|deep_compatibility|comm_advice|comparison)$",
    )
    candidate_ids: list[str] = Field(..., min_length=1, max_length=20)
    match_params_override: Optional[dict] = None
    parent_analysis_id: Optional[str] = None

class FateAnalysisResponse(BaseModel):
    analysis_id: str
    analysis_type: str
    candidate_ids: list[str]
    result: Optional[dict] = None
    status: str
    created_at: str

# ── 通知 ──────────────────────────────────────────────────
class NotificationResponse(BaseModel):
    notif_id: str
    type: str
    actor_id: Optional[str] = None
    payload: dict = {}
    is_read: bool
    created_at: str

class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
```

- [ ] **Step 5: Commit**

```bash
git add backend/api/schemas.py
git commit -m "feat: update schemas for simplified registration and phase3 new entities"
```

---

## Task 5：更新注册端点

**Files:**
- Modify: `backend/api/routers/auth.py`

- [ ] **Step 1: 更新 register 端点**

找到 `POST /register` 端点，将创建用户的部分改为：

```python
@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # 检查手机号唯一性
    existing = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="手机号已注册")

    import secrets, string
    uid_chars = string.ascii_uppercase + string.digits
    user_id = "U" + "".join(secrets.choice(uid_chars) for _ in range(8))

    user = User(
        user_id=user_id,
        nickname=data.nickname,
        gender=data.gender,
        phone=data.phone,
        password_hash=pwd_context.hash(data.password),
        target_gender="女" if data.gender == "男" else "男",
        profile_complete=False,
        # 其他字段保持默认值
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": user.user_id})
    return TokenResponse(access_token=access_token, token_type="bearer")
```

- [ ] **Step 2: 更新 update_me 端点，加入 birth_date 处理**

在 `PUT /me` 端点中，处理 `birth_date` 时调用 zodiac 工具：

```python
if data.birth_date is not None:
    from datetime import date as date_
    from core.utils.zodiac import update_zodiac_fields
    try:
        bd = date_.fromisoformat(data.birth_date)
        update_zodiac_fields(current_user, bd)
    except ValueError:
        raise HTTPException(status_code=400, detail="birth_date 格式应为 YYYY-MM-DD")
```

- [ ] **Step 3: 更新 profile_complete 自动计算**

在 `PUT /me` 端点 commit 之前，添加自动判断：

```python
# 自动判断资料是否已完善
required_fields = ["nickname", "gender", "age", "city", "about_me", "ideal_partner"]
current_user.profile_complete = all(
    getattr(current_user, f) not in (None, "", 0) for f in required_fields
)
```

- [ ] **Step 4: Commit**

```bash
git add backend/api/routers/auth.py
git commit -m "feat: simplify registration to 4 fields, auto-calc zodiac and profile_complete"
```

---

## Task 6：种子数据脚本（20位用户）

**Files:**
- Create: `backend/scripts/seed_users.py`

- [ ] **Step 1: 创建种子脚本**

```python
"""
种子数据脚本 - 创建20位完整资料的测试用户。
运行: python scripts/seed_users.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from passlib.context import CryptContext
from sqlalchemy import select
from core.database.session import AsyncSessionLocal
from core.database.models import User
from core.utils.zodiac import get_zodiac_sign, get_chinese_zodiac

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "Test@123456"

USERS_DATA = [
    # (nickname, gender, phone, age, birth_date, city, province, education,
    #  annual_income, mbti, height_cm, about_me, ideal_partner, hobbies,
    #  target_gender, target_age_min, target_age_max)
    ("林晓雨", "女", "13800000001", 26, date(1998, 3, 15), "上海", "上海",
     "本科", "15-25万", "INFJ", 163,
     "喜欢读书和爬山，在互联网公司做产品经理。性格温柔但有自己的坚持。",
     "希望他有上进心，爱生活，最好能一起旅行。",
     "阅读 爬山 摄影 美食探店",
     "男", 26, 35),

    ("陈浩然", "男", "13800000002", 29, date(1995, 7, 22), "上海", "上海",
     "硕士", "25-40万", "ENTJ", 178,
     "金融行业，喜欢健身和投资。周末会去骑行，追求高效的生活方式。",
     "独立自主，有自己的事业和想法，不依赖男方。",
     "健身 骑行 投资 看纪录片",
     "女", 24, 32),

    ("张美琳", "女", "13800000003", 24, date(2000, 11, 5), "北京", "北京",
     "本科", "8-15万", "ENFP", 158,
     "刚参加工作的设计师，充满活力，喜欢画画和看展。生活里充满色彩。",
     "温柔体贴，有安全感，包容我的小情绪。",
     "绘画 看展 街拍 咖啡 音乐",
     "男", 24, 32),

    ("王子豪", "男", "13800000004", 31, date(1993, 1, 18), "北京", "北京",
     "本科", "15-25万", "ISTJ", 175,
     "程序员，喜欢打篮球和玩游戏。性格稳重，对感情认真专一。",
     "善良真诚，不在乎外表，在乎内心。",
     "篮球 编程 游戏 做饭",
     "女", 23, 30),

    ("刘思远", "女", "13800000005", 27, date(1997, 5, 30), "广州", "广东",
     "本科", "15-25万", "ISFJ", 160,
     "小学教师，喜欢种植和烘焙。生活平静温暖，享受当下。",
     "顾家，有责任心，最好爱孩子。",
     "烘焙 种植 瑜伽 读书",
     "男", 27, 36),

    ("赵明宇", "男", "13800000006", 33, date(1991, 9, 12), "广州", "广东",
     "硕士", "40万以上", "INTJ", 182,
     "创业公司CEO，工作忙但重视感情。喜欢马拉松和冥想。",
     "有自己想法，不随波逐流，能接受我经常出差。",
     "马拉松 冥想 商业读物 旅行",
     "女", 25, 35),

    ("孙雨桐", "女", "13800000007", 25, date(1999, 2, 14), "成都", "四川",
     "本科", "8-15万", "ESFP", 162,
     "市场运营，四川人超爱吃辣！喜欢逛街和追剧。活泼开朗。",
     "幽默风趣，不沉闷，最好也爱吃。",
     "美食 逛街 追剧 打卡新店",
     "男", 25, 33),

    ("李建国", "男", "13800000008", 28, date(1996, 4, 8), "成都", "四川",
     "大专", "8-15万", "ESFJ", 173,
     "厨师，做得一手好川菜。性格豪爽，朋友多。",
     "真实不做作，能接受我不规律的工作时间。",
     "做饭 打牌 钓鱼 看球",
     "女", 22, 30),

    ("吴静怡", "女", "13800000009", 30, date(1994, 8, 19), "杭州", "浙江",
     "硕士", "15-25万", "INTP", 165,
     "数据分析师，理性逻辑强，但内心温柔。喜欢一个人旅行。",
     "尊重个人空间，有共同话题，不无聊。",
     "一人旅行 冥想 科幻小说 养猫",
     "男", 28, 38),

    ("周大伟", "男", "13800000010", 35, date(1989, 12, 25), "杭州", "浙江",
     "本科", "25-40万", "ENTP", 180,
     "律师，能说会道，喜欢辩论和下棋。希望找到灵魂伴侣。",
     "聪明有趣，有自己的见解，不依附于人。",
     "辩论 下棋 红酒 历史",
     "女", 26, 36),

    ("郑小燕", "女", "13800000011", 22, date(2002, 6, 20), "上海", "上海",
     "本科", "8万以下", "ENFJ", 156,
     "大学应届生，主修心理学，喜欢倾听和帮助他人。",
     "成熟稳重，给我引导和安全感。",
     "心理学 公益 瑜伽 写日记",
     "男", 24, 32),

    ("黄志强", "男", "13800000012", 27, date(1997, 10, 3), "北京", "北京",
     "硕士", "15-25万", "INFP", 176,
     "公务员，稳定有保障。平时喜欢写作和看电影。",
     "善解人意，不爱争吵，一起安安静静过日子。",
     "写作 电影 慢跑 烹饪",
     "女", 23, 30),

    ("徐梦洁", "女", "13800000013", 29, date(1995, 3, 28), "广州", "广东",
     "本科", "15-25万", "ESTP", 168,
     "销售总监，雷厉风行，有激情。喜欢极限运动和派对。",
     "有担当，不软弱，敢于拼搏的男生。",
     "极限运动 派对 买买买 网球",
     "男", 28, 38),

    ("马天宇", "男", "13800000014", 32, date(1992, 7, 15), "成都", "四川",
     "本科", "15-25万", "ISFP", 174,
     "自由摄影师，走遍中国。安静内敛，镜头后面是另一个世界。",
     "欣赏艺术，包容我的漂泊，有自己的生活。",
     "摄影 旅行 咖啡 人文纪录片",
     "女", 24, 34),

    ("高丽娜", "女", "13800000015", 26, date(1998, 1, 7), "杭州", "浙江",
     "硕士", "15-25万", "ESTJ", 161,
     "医生，工作认真负责。下班爱看综艺减压，人很接地气。",
     "理解医生工作的辛苦，有耐心，爱家庭。",
     "综艺 美食 健身 睡觉",
     "男", 27, 36),

    ("蒋俊凯", "男", "13800000016", 24, date(2000, 9, 9), "上海", "上海",
     "本科", "8-15万", "ENFP", 179,
     "短视频博主，有几十万粉。热爱生活，每天都很充实。",
     "支持我的工作，活泼有趣，不无聊。",
     "短视频 街舞 旅行 剧本杀",
     "女", 22, 28),

    ("韩冰清", "女", "13800000017", 31, date(1993, 5, 16), "北京", "北京",
     "硕士", "25-40万", "INTJ", 167,
     "大学讲师，研究方向AI。理性冷静，有点高冷，熟了很暖。",
     "智识对等，能聊学术也能聊生活，尊重边界。",
     "AI研究 古典音乐 阅读 茶道",
     "男", 30, 40),

    ("曹宇轩", "男", "13800000018", 26, date(1998, 2, 22), "广州", "广东",
     "本科", "8-15万", "ESFP", 177,
     "健身教练，体型好看，阳光开朗。喜欢带人运动。",
     "阳光健康，积极向上，最好也喜欢运动。",
     "健身 篮球 冲浪 烤肉",
     "女", 22, 30),

    ("宋欣然", "女", "13800000019", 28, date(1996, 11, 11), "成都", "四川",
     "本科", "15-25万", "INFP", 159,
     "插画师，工作在家，自由度高。喜欢猫和一切毛茸茸的东西。",
     "温柔体贴，能接受猫，不排斥宅。",
     "画画 养猫 刷剧 逛花市",
     "男", 26, 35),

    ("冯天浩", "男", "13800000020", 36, date(1988, 4, 4), "杭州", "浙江",
     "本科", "25-40万", "ISTP", 181,
     "建筑设计师，有自己的工作室。沉默寡言，但设计作品很有温度。",
     "独立自主，不黏人，欣赏美的事物。",
     "建筑设计 木工 登山 清酒",
     "女", 26, 36),
]


async def seed():
    async with AsyncSessionLocal() as session:
        created = 0
        for row in USERS_DATA:
            (nickname, gender, phone, age, birth_date, city, province,
             education, annual_income, mbti, height_cm, about_me,
             ideal_partner, hobbies, target_gender,
             target_age_min, target_age_max) = row

            # 检查是否已存在
            existing = await session.execute(
                select(User).where(User.phone == phone)
            )
            if existing.scalar_one_or_none():
                print(f"  跳过已存在: {nickname} ({phone})")
                continue

            import secrets, string
            uid_chars = string.ascii_uppercase + string.digits
            user_id = "U" + "".join(secrets.choice(uid_chars) for _ in range(8))

            user = User(
                user_id=user_id,
                nickname=nickname,
                gender=gender,
                phone=phone,
                password_hash=pwd_context.hash(DEFAULT_PASSWORD),
                age=age,
                birth_date=birth_date,
                zodiac_sign=get_zodiac_sign(birth_date),
                chinese_zodiac=get_chinese_zodiac(birth_date),
                city=city,
                province=province,
                education=education,
                annual_income=annual_income,
                marital_status="未婚",
                mbti=mbti,
                height_cm=height_cm,
                about_me=about_me,
                ideal_partner=ideal_partner,
                hobbies=hobbies,
                target_gender=target_gender,
                target_age_min=target_age_min,
                target_age_max=target_age_max,
                target_city="不限",
                profile_complete=True,
                photos=[],
            )
            session.add(user)
            created += 1
            print(f"  创建用户: {nickname} ({user_id}) | {get_zodiac_sign(birth_date)} | {get_chinese_zodiac(birth_date)}")

        await session.commit()
        print(f"\n✅ 完成！新增 {created} 位用户，统一密码: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: 运行种子脚本**

```bash
cd backend
python scripts/seed_users.py
```

预期输出：创建 20 位用户（若已有同手机号则跳过），末尾显示 `✅ 完成！新增 X 位用户`

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed_users.py
git commit -m "feat: add 20 test users seed script with zodiac/profile_complete"
```

---

## Task 7：UI 全面重构（index.css）

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: 替换 CSS 变量和全局样式**

完整替换 `frontend/src/index.css` 内容：

```css
@import "tailwindcss";

@theme inline {
  /* ── 主色系（深靛蓝 INS 风）─────────────────────── */
  --color-bg-base:      #0f0c29;
  --color-bg-elevated:  #1a1040;
  --color-bg-deep:      #1e0a3c;
  --color-bg-card:      rgba(255, 255, 255, 0.07);

  /* ── 渐变（直接在 CSS var 里定义，组件内用 bg 属性引用）*/
  --gradient-primary:   linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-heart:     linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  --gradient-ai:        linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  --gradient-gold:      linear-gradient(135deg, #f6d365 0%, #fda085 100%);

  /* ── 文字色 ───────────────────────────────────────── */
  --color-text-primary:   #f0f0f8;
  --color-text-secondary: #a0a0c0;
  --color-text-muted:     #6060a0;

  /* ── 边框/分割 ──────────────────────────────────── */
  --color-border:    rgba(255, 255, 255, 0.12);
  --color-border-strong: rgba(255, 255, 255, 0.20);

  /* ── 语义色 ─────────────────────────────────────── */
  --color-success: #4ade80;
  --color-warning: #fbbf24;
  --color-danger:  #f87171;

  /* ── 字体 ───────────────────────────────────────── */
  --font-sans: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;

  /* ── 圆角 ───────────────────────────────────────── */
  --radius-sm:  8px;
  --radius-md:  12px;
  --radius-lg:  20px;
  --radius-xl:  28px;
}

/* ── 全局重置 ───────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html {
  font-size: 15px;
  -webkit-text-size-adjust: 100%;
}

body {
  margin: 0;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0c29 0%, #1a1040 50%, #1e0a3c 100%);
  background-attachment: fixed;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  line-height: 1.6;
}

/* 顶部径向发光，增加深度感 */
body::before {
  content: "";
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 10%, rgba(102, 126, 234, 0.18) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 80%, rgba(240, 147, 251, 0.12) 0%, transparent 55%);
  pointer-events: none;
  z-index: 0;
}

#root { position: relative; z-index: 1; }

/* ── 玻璃卡片 ───────────────────────────────────────────── */
.glass-card {
  background: var(--color-bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.glass-card-hover {
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.glass-card-hover:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 60px rgba(102, 126, 234, 0.25);
  border-color: rgba(102, 126, 234, 0.4);
}

/* ── 渐变按钮 ───────────────────────────────────────────── */
.btn-primary {
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 24px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s, box-shadow 0.2s;
}

.btn-primary:hover {
  opacity: 0.92;
  box-shadow: 0 8px 24px rgba(118, 75, 162, 0.45);
}

.btn-primary:active { transform: scale(0.97); }

.btn-heart {
  background: var(--gradient-heart);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-heart:hover {
  transform: scale(1.15);
  box-shadow: 0 0 16px rgba(240, 147, 251, 0.6);
}

.btn-ghost {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: 9px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.btn-ghost:hover {
  background: rgba(255,255,255,0.08);
  border-color: rgba(255,255,255,0.3);
}

/* ── 输入框 ─────────────────────────────────────────────── */
.input-dark {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  padding: 10px 14px;
  font-size: 15px;
  width: 100%;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-dark::placeholder { color: var(--color-text-muted); }

.input-dark:focus {
  border-color: rgba(102, 126, 234, 0.6);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

/* ── 渐变文字 ───────────────────────────────────────────── */
.text-gradient-primary {
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.text-gradient-heart {
  background: var(--gradient-heart);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── 缘分指数动画 ────────────────────────────────────────── */
@keyframes pulse-heart {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(30px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes border-glow {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 星星粒子（首页 Hero 用） */
@keyframes float-star {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.6; }
  50%       { transform: translateY(-8px) rotate(180deg); opacity: 1; }
}

.animate-fade-in-up { animation: fade-in-up 0.5s ease both; }
.animate-slide-up   { animation: slide-up  0.4s ease both; }
.animate-pulse-heart { animation: pulse-heart 1s ease infinite; }

/* ── 心动脉冲标记 ────────────────────────────────────────── */
.heart-active {
  position: relative;
}
.heart-active::after {
  content: "";
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: var(--gradient-heart);
  opacity: 0.3;
  animation: pulse-heart 1.5s ease infinite;
}

/* ── 滚动条美化 ─────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(102, 126, 234, 0.4);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(102, 126, 234, 0.7); }

/* ── 移动端优化 ─────────────────────────────────────────── */
@media (max-width: 768px) {
  html { font-size: 16px; }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/index.css
git commit -m "style: replace dark theme with INS indigo/purple gradient system"
```

---

## Task 8：更新 UserCard 和 Navbar 组件

**Files:**
- Modify: `frontend/src/components/UserCard.tsx`
- Modify: `frontend/src/components/Navbar.tsx`

- [ ] **Step 1: 更新 UserCard - 添加心动按钮和新样式**

在 `UserCard.tsx` 中，找到卡片 JSX，更新为以下结构（保留现有 props，只改样式和添加按钮）：

```tsx
import { Heart, MapPin, GraduationCap, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

// 在卡片右下角添加心动按钮（Phase 3b 接通实际逻辑，此处先做 UI）
const HeartButton = ({ isActive, onClick }: { isActive: boolean; onClick: () => void }) => (
  <motion.button
    className={`btn-heart ${isActive ? "heart-active" : ""}`}
    style={isActive ? {} : { background: "rgba(255,255,255,0.15)", border: "1px solid rgba(255,255,255,0.25)" }}
    whileTap={{ scale: 0.85 }}
    onClick={(e) => { e.stopPropagation(); onClick(); }}
    aria-label="加入心动TA们"
  >
    <Heart size={16} fill={isActive ? "white" : "none"} color="white" />
  </motion.button>
);
```

在卡片封面图区域确保有渐变遮罩：

```tsx
{/* 底部渐变遮罩 */}
<div className="absolute bottom-0 left-0 right-0 h-2/5 bg-gradient-to-t from-black/70 to-transparent" />
```

卡片整体使用 `glass-card glass-card-hover` 类。

- [ ] **Step 2: 更新 Navbar**

在 `Navbar.tsx` 中：
1. 背景改为 `rgba(15,12,41,0.85)` + `backdrop-filter: blur(20px)`
2. Logo 文字使用 `text-gradient-primary` 类
3. 添加通知铃铛图标占位（`Bell` from lucide-react），角标数量从 `appStore` 读

```tsx
import { Bell } from "lucide-react";

// 通知图标（Phase 3b 接通实际数量）
<button className="relative btn-ghost p-2">
  <Bell size={20} />
  {/* <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">3</span> */}
</button>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/UserCard.tsx frontend/src/components/Navbar.tsx
git commit -m "style: update UserCard with heart button placeholder and Navbar to new theme"
```

---

## Task 9：简化注册页 + 资料引导横幅

**Files:**
- Modify: `frontend/src/pages/Register.tsx`
- Create: `frontend/src/components/ProfileCompleteBanner.tsx`
- Modify: `frontend/src/pages/Home.tsx`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 更新 types/index.ts**

在 `AuthUser` 接口添加新字段：

```typescript
export interface AuthUser {
  user_id: string;
  nickname: string;
  gender: string;
  age?: number;
  city?: string;
  profile_complete: boolean;
  birth_date?: string;
  zodiac_sign?: string;
  chinese_zodiac?: string;
  avatar_url?: string;
  photos: string[];
  // ... 其他已有字段
}
```

- [ ] **Step 2: 更新 Register.tsx（4字段）**

```tsx
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { register as apiRegister } from "../api/client";

interface RegisterForm {
  nickname: string;
  gender: "男" | "女";
  phone: string;
  password: string;
}

export default function Register() {
  const { register: formRegister, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>();
  const { login } = useAuth();
  const navigate = useNavigate();

  const onSubmit = async (data: RegisterForm) => {
    try {
      const result = await apiRegister(data);
      login(result.access_token);
      navigate("/");
    } catch (err: any) {
      // 显示错误 toast
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass-card w-full max-w-sm p-8 animate-fade-in-up">
        <h1 className="text-2xl font-bold text-center mb-2">加入心犀</h1>
        <p className="text-center text-sm mb-8" style={{ color: "var(--color-text-secondary)" }}>
          注册后可完善资料，解锁寻找缘分
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">昵称</label>
            <input className="input-dark" placeholder="2-20个字符" {...formRegister("nickname", { required: true, minLength: 2, maxLength: 20 })} />
          </div>

          <div>
            <label className="block text-sm mb-2">性别</label>
            <div className="flex gap-3">
              {(["男", "女"] as const).map((g) => (
                <label key={g} className="flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all"
                  style={{ borderColor: "var(--color-border)" }}>
                  <input type="radio" value={g} {...formRegister("gender", { required: true })} className="sr-only" />
                  <span>{g === "男" ? "👨" : "👩"} {g}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm mb-1">手机号</label>
            <input className="input-dark" placeholder="11位手机号" type="tel"
              {...formRegister("phone", { required: true, pattern: /^1[3-9]\d{9}$/ })} />
          </div>

          <div>
            <label className="block text-sm mb-1">密码</label>
            <input className="input-dark" placeholder="8位以上" type="password"
              {...formRegister("password", { required: true, minLength: 8 })} />
          </div>

          <button type="submit" className="btn-primary w-full mt-2" disabled={isSubmitting}>
            {isSubmitting ? "注册中..." : "立即注册"}
          </button>
        </form>

        <p className="text-center text-sm mt-6" style={{ color: "var(--color-text-secondary)" }}>
          已有账号？<a href="/login" className="text-gradient-primary">立即登录</a>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 创建 ProfileCompleteBanner.tsx**

```tsx
import { Sparkles, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function ProfileCompleteBanner() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  if (!user || user.profile_complete || dismissed) return null;

  return (
    <div className="animate-fade-in-up mx-4 mt-3 rounded-2xl p-4 flex items-center gap-3"
      style={{ background: "linear-gradient(135deg, rgba(102,126,234,0.2), rgba(240,147,251,0.15))", border: "1px solid rgba(102,126,234,0.3)" }}>
      <Sparkles size={20} style={{ color: "#f093fb", flexShrink: 0 }} />
      <div className="flex-1">
        <p className="text-sm font-medium">完善资料，解锁寻找缘分 ✨</p>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
          填写年龄、城市和自我介绍后即可被发现
        </p>
      </div>
      <button className="btn-primary text-xs px-4 py-2" onClick={() => navigate("/profile/edit")}>
        去完善
      </button>
      <button className="p-1 rounded-lg" style={{ color: "var(--color-text-muted)" }} onClick={() => setDismissed(true)}>
        <X size={16} />
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 在 Home.tsx 中引入横幅**

```tsx
import ProfileCompleteBanner from "../components/ProfileCompleteBanner";

// 在首页 return 的最顶部（header 下方）添加：
<ProfileCompleteBanner />
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/pages/Register.tsx frontend/src/components/ProfileCompleteBanner.tsx frontend/src/pages/Home.tsx
git commit -m "feat: simplified registration (4 fields), add profile complete banner"
```

---

## Task 10：访问控制（ProtectedRoute 扩展）

**Files:**
- Modify: `frontend/src/components/ProtectedRoute.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 更新 ProtectedRoute 支持 requireProfileComplete**

```tsx
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  requireProfileComplete?: boolean;
  redirectTo?: string;
}

export default function ProtectedRoute({
  children,
  requireAuth = true,
  requireProfileComplete = false,
  redirectTo = "/login",
}: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">
    <div className="w-8 h-8 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
  </div>;

  if (requireAuth && !user) return <Navigate to={redirectTo} replace />;

  if (requireProfileComplete && user && !user.profile_complete) {
    return <Navigate to="/profile/edit?hint=complete_required" replace />;
  }

  return <>{children}</>;
}
```

- [ ] **Step 2: 在 App.tsx 中应用路由保护**

确认以下路由已正确配置：

```tsx
// 需要登录的路由
<Route path="/profile" element={<ProtectedRoute><MyProfile /></ProtectedRoute>} />
<Route path="/profile/edit" element={<ProtectedRoute><EditProfile /></ProtectedRoute>} />

// 需要登录 + 完善资料的路由（Phase 3b 添加缘分相关页面时使用）
// <Route path="/fate/*" element={<ProtectedRoute requireProfileComplete><FatePage /></ProtectedRoute>} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ProtectedRoute.tsx frontend/src/App.tsx
git commit -m "feat: extend ProtectedRoute with requireProfileComplete guard"
```

---

## Task 11：联调验证

- [ ] **Step 1: 启动后端**

```bash
cd backend
python run.py
```

预期：`Uvicorn running on http://127.0.0.1:8000`，无报错

- [ ] **Step 2: 运行种子脚本**

```bash
cd backend
python scripts/seed_users.py
```

预期：输出 20 行用户创建信息

- [ ] **Step 3: 启动前端**

```bash
cd frontend
npm run dev
```

预期：`http://localhost:5173` 无编译报错

- [ ] **Step 4: 浏览器验证清单**

访问 `http://localhost:5173`，逐项检查：

1. **首页背景** - 深靛蓝渐变（非纯黑），有顶部发光效果
2. **用户卡片** - 显示 20 位用户，卡片有玻璃质感，hover 有上浮效果
3. **右下角心形** - 按钮可见，未登录点击后提示登录
4. **注册页** - 只有 4 个字段（昵称/性别/手机号/密码）
5. **登录** - 使用任意种子用户，如 `13800000001 / Test@123456`
6. **登录后横幅** - 若种子用户 profile_complete=True 则不显示横幅，登录后直接无横幅（种子用户已完善）
7. **字号** - 文字清晰可读，最小不低于 13px

- [ ] **Step 5: TypeScript 检查**

```bash
cd frontend
npm run typecheck
```

预期：0 errors

- [ ] **Step 6: 最终 Commit**

```bash
git add -A
git commit -m "feat: phase3a complete - INS UI, simplified registration, seed users, zodiac, profile_complete"
```

---

## 验收标准

- [ ] 数据库包含 `fate_candidates`、`fate_analyses`、`notifications` 三张新表
- [ ] `users` 表新增 `profile_complete`、`birth_date`、`zodiac_sign`、`chinese_zodiac` 字段
- [ ] 20 位测试用户已入库，密码 `Test@123456`，均有星座和属相
- [ ] 首页背景为深靛蓝（非纯黑），文字清晰可读
- [ ] 注册页只需昵称+性别+手机号+密码
- [ ] 未登录点击心动按钮跳转登录页
- [ ] TypeScript 编译 0 错误
