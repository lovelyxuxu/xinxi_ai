"""
心犀AI - SQLAlchemy ORM 模型
=============================
定义所有 PostgreSQL 数据表的结构。

学习要点：
---------
- SQLAlchemy 2.0 使用 Mapped[] 类型注解声明字段（替代旧版的 Column()）
- mapped_column() 是 2.0 的新 API，同时定义列类型和约束
- relationship() 定义表之间的关联，支持懒加载和预加载
- __tablename__ 指定表名，不写则默认用类名的小写

设计原则：
  1. 每张表都有自增 id 作为主键（内部关联用）
  2. 同时有业务 ID（如 user_id）作为唯一索引（对外暴露用）
  3. 所有表都有 created_at 时间戳
  4. 使用 JSONB 类型存储灵活结构（如匹配参数、评估结果）
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Text, Boolean, DateTime, Float,
    ForeignKey, UniqueConstraint, CheckConstraint, Index,
    MetaData,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明基类。

    学习要点：
    - 所有 ORM 模型都继承这个 Base
    - Alembic 通过 Base.metadata 检测表结构变化，自动生成迁移脚本
    - DeclarativeBase 是 2.0 的新写法（替代旧版的 declarative_base()）
    - 设置默认 schema="xinxi"，将我们的表放在独立 schema 中
      避免与 LangFuse 自带的 public schema 中的 users 等表冲突
    """
    # 【学习要点】MetaData(schema=...) 为所有表设置默认 schema
    # 这样我们的表创建在 xinxi schema 下，LangFuse 的表在 public schema 下
    # 两者完全隔离，互不影响
    metadata = MetaData(schema="xinxi")


# ============================================================
# users - 用户表
# ============================================================

class User(Base):
    """
    用户表 - 系统的核心实体。

    学习要点：
    - Mapped[str] 表示"这个字段是字符串类型，不能为 None"
    - Mapped[Optional[str]] 表示"可以为 None"
    - mapped_column(String(50)) 指定数据库列类型和长度
    - relationship() 定义 ORM 关联，back_populates 指定反向引用名称

    Agent 集成：
    - target_* 字段被 parse_intent 节点读取，构建搜索条件
    - about_me + ideal_partner + hobbies 被嵌入为向量，用于语义搜索
    """
    __tablename__ = "users"

    # === 主键和业务 ID ===
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True,
        comment="业务ID: U + 8位随机字符",
    )

    # === 基本信息 ===
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    education: Mapped[str] = mapped_column(String(20), default="本科")
    annual_income: Mapped[str] = mapped_column(String(30), default="未填写")
    marital_status: Mapped[str] = mapped_column(String(20), default="未婚")
    mbti: Mapped[str] = mapped_column(String(10), default="未知")
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    about_me: Mapped[str] = mapped_column(Text, default="")
    ideal_partner: Mapped[str] = mapped_column(Text, default="")
    hobbies: Mapped[str] = mapped_column(Text, default="")

    # === 择偶偏好（Agent 读取这些字段构建搜索条件）===
    target_gender: Mapped[str] = mapped_column(String(10), nullable=False)
    target_age_min: Mapped[int] = mapped_column(Integer, default=18)
    target_age_max: Mapped[int] = mapped_column(Integer, default=45)
    target_city: Mapped[str] = mapped_column(String(50), default="不限")
    target_height_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_height_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_education: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # === 认证字段 ===
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)

    # === 元数据 ===
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    photos: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        comment="用户照片 URL 列表，最多 6 张",
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
    )

    # === ORM 关联 ===
    # 我发起的匹配记录
    match_records: Mapped[List["MatchRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<User {self.user_id} {self.nickname}>"

    def to_dict(self) -> dict:
        """转换为前端兼容的字典（不包含敏感字段）"""
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


# ============================================================
# match_records - 匹配记录表
# ============================================================

class MatchRecord(Base):
    """
    匹配记录表 - 每次匹配一条记录。

    学习要点：
    - user_filters 用 JSONB 存储用户自定义筛选参数
    - thread_id 关联 LangGraph 的检查点，可回溯 Agent 执行过程
    - status 字段支持 pending/completed/failed，方便前端展示匹配状态
    """
    __tablename__ = "match_records"
    __table_args__ = (
        Index("idx_match_records_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    thread_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    match_letters: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    evaluation: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )

    # === ORM 关联 ===
    user: Mapped["User"] = relationship(back_populates="match_records")
    candidates: Mapped[List["MatchCandidate"]] = relationship(
        back_populates="match_record", cascade="all, delete-orphan",
        order_by="MatchCandidate.rank",
    )


# ============================================================
# match_candidates - 匹配候选人表
# ============================================================

class MatchCandidate(Base):
    """
    匹配候选人表 - 一条匹配记录中的每位候选人。

    学习要点：
    - 从 match_records 中拆出，实现一对多关系
    - is_viewed / is_liked 支持用户交互状态追踪
    - rank 字段用于排序（1 = 最佳候选人）
    """
    __tablename__ = "match_candidates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("match_records.match_id"), nullable=False, index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(Text, default="")
    rank: Mapped[int] = mapped_column(Integer, default=0)
    is_viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_liked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )

    # === ORM 关联 ===
    match_record: Mapped["MatchRecord"] = relationship(back_populates="candidates")
    candidate: Mapped["User"] = relationship(foreign_keys=[candidate_id])


# ============================================================
# follow_relationships - 关注关系表
# ============================================================

class FollowRelationship(Base):
    """
    关注关系表 - 类似抖音/小红书的关注系统。

    学习要点：
    - UniqueConstraint 防止重复关注（同一个人不能关注两次）
    - CheckConstraint 防止自己关注自己
    - 查询粉丝数：SELECT COUNT(*) WHERE following_id = ?
    - 查询关注数：SELECT COUNT(*) WHERE follower_id = ?
    """
    __tablename__ = "follow_relationships"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follow"),
        CheckConstraint("follower_id != following_id", name="ck_no_self_follow"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    follower_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    following_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )


# ============================================================
# conversations - 会话表
# ============================================================

class Conversation(Base):
    """
    会话表 - 两个用户之间的对话通道。

    学习要点：
    - participant_a 和 participant_b 约定 a < b（字典序），保证唯一性
    - 这样同一对用户只有一个会话，不会重复创建
    - last_message_at 用于会话列表排序（最近的排前面）
    """
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("participant_a", "participant_b", name="uq_conv_participants"),
        CheckConstraint("participant_a < participant_b", name="ck_conv_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False,
    )
    participant_a: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False,
    )
    participant_b: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )

    # === ORM 关联 ===
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
    )


# ============================================================
# messages - 消息表
# ============================================================

class Message(Base):
    """
    消息表 - 私信内容。

    学习要点：
    - is_read 标记实现"未读消息"功能
    - conversation_id + created_at 联合索引加速按时间查询
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_msg_conv_time", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    conversation_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("conversations.conversation_id"), nullable=False,
    )
    sender_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )

    # === ORM 关联 ===
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# ============================================================
# blacklist - 黑名单表
# ============================================================

class Blacklist(Base):
    """
    黑名单表 - 在匹配时排除特定用户。

    学习要点：
    - Agent 的 retrieval_agent 检索候选人时查询此表
    - 将黑名单用户从搜索结果中过滤掉
    """
    __tablename__ = "blacklist"
    __table_args__ = (
        UniqueConstraint("user_id", "blocked_user_id", name="uq_blacklist"),
        CheckConstraint("user_id != blocked_user_id", name="ck_no_self_block"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False, index=True,
    )
    blocked_user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.user_id"), nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )
