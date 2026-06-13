"""initial tables - 创建所有 v2 数据表

Revision ID: 001
Revises:
Create Date: 2026-06-13

学习要点：
---------
- upgrade() 函数创建所有表，downgrade() 按相反顺序删除
- 表结构对应 models.py 中的 ORM 模型定义
- sa.schema="xinxi" 将表创建在 xinxi schema 下
  （避免与 LangFuse 的 public schema 冲突）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 【学习要点】所有表统一使用 xinxi schema
SCHEMA = "xinxi"


def upgrade() -> None:
    # ============================================================
    # users - 用户表（系统核心实体）
    # ============================================================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(20), nullable=False, comment="业务ID: U + 8位随机"),
        sa.Column("nickname", sa.String(50), nullable=False),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(50), nullable=False),
        sa.Column("province", sa.String(50), nullable=False),
        sa.Column("education", sa.String(20), server_default="本科"),
        sa.Column("annual_income", sa.String(30), server_default="未填写"),
        sa.Column("marital_status", sa.String(20), server_default="未婚"),
        sa.Column("mbti", sa.String(10), server_default="未知"),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("about_me", sa.Text(), server_default=""),
        sa.Column("ideal_partner", sa.Text(), server_default=""),
        sa.Column("hobbies", sa.Text(), server_default=""),
        # 择偶偏好
        sa.Column("target_gender", sa.String(10), nullable=False),
        sa.Column("target_age_min", sa.Integer(), server_default="18"),
        sa.Column("target_age_max", sa.Integer(), server_default="45"),
        sa.Column("target_city", sa.String(50), server_default="不限"),
        sa.Column("target_height_min", sa.Integer(), nullable=True),
        sa.Column("target_height_max", sa.Integer(), nullable=True),
        sa.Column("target_education", sa.String(20), nullable=True),
        # 认证字段
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        # 元数据
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        # 约束和索引
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
        sa.CheckConstraint("gender IN ('male', 'female')"),
        sa.CheckConstraint("age BETWEEN 18 AND 80"),
        schema=SCHEMA,
    )
    op.create_index("idx_users_gender_city", "users", ["gender", "city"], schema=SCHEMA)

    # ============================================================
    # match_records - 匹配记录表
    # ============================================================
    op.create_table(
        "match_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.String(20), nullable=False),
        sa.Column("user_id", sa.String(20), nullable=False),
        sa.Column("thread_id", sa.String(100), nullable=True),
        sa.Column("user_filters", JSONB(), server_default="{}"),
        sa.Column("match_letters", JSONB(), server_default="[]"),
        sa.Column("status", sa.String(20), server_default="completed"),
        sa.Column("evaluation", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.user_id"]),
        schema=SCHEMA,
    )
    op.create_index("idx_match_records_user_created", "match_records", ["user_id", "created_at"], schema=SCHEMA)

    # ============================================================
    # match_candidates - 匹配候选人表
    # ============================================================
    op.create_table(
        "match_candidates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.String(20), nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("reason", sa.Text(), server_default=""),
        sa.Column("rank", sa.Integer(), server_default="0"),
        sa.Column("is_viewed", sa.Boolean(), server_default="false"),
        sa.Column("is_liked", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["match_id"], [f"{SCHEMA}.match_records.match_id"]),
        sa.ForeignKeyConstraint(["candidate_id"], [f"{SCHEMA}.users.user_id"]),
        schema=SCHEMA,
    )
    op.create_index("idx_match_candidates_match_id", "match_candidates", ["match_id"], schema=SCHEMA)
    op.create_index("idx_match_candidates_candidate_id", "match_candidates", ["candidate_id"], schema=SCHEMA)

    # ============================================================
    # follow_relationships - 关注关系表
    # ============================================================
    op.create_table(
        "follow_relationships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("follower_id", sa.String(20), nullable=False),
        sa.Column("following_id", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["follower_id"], [f"{SCHEMA}.users.user_id"]),
        sa.ForeignKeyConstraint(["following_id"], [f"{SCHEMA}.users.user_id"]),
        sa.UniqueConstraint("follower_id", "following_id", name="uq_follow"),
        sa.CheckConstraint("follower_id != following_id", name="ck_no_self_follow"),
        schema=SCHEMA,
    )
    op.create_index("idx_follow_follower", "follow_relationships", ["follower_id"], schema=SCHEMA)
    op.create_index("idx_follow_following", "follow_relationships", ["following_id"], schema=SCHEMA)

    # ============================================================
    # conversations - 会话表
    # ============================================================
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.String(40), nullable=False),
        sa.Column("participant_a", sa.String(20), nullable=False),
        sa.Column("participant_b", sa.String(20), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id"),
        sa.UniqueConstraint("participant_a", "participant_b", name="uq_conv_participants"),
        sa.CheckConstraint("participant_a < participant_b", name="ck_conv_order"),
        sa.ForeignKeyConstraint(["participant_a"], [f"{SCHEMA}.users.user_id"]),
        sa.ForeignKeyConstraint(["participant_b"], [f"{SCHEMA}.users.user_id"]),
        schema=SCHEMA,
    )

    # ============================================================
    # messages - 消息表
    # ============================================================
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.String(20), nullable=False),
        sa.Column("conversation_id", sa.String(40), nullable=False),
        sa.Column("sender_id", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
        sa.ForeignKeyConstraint(["conversation_id"], [f"{SCHEMA}.conversations.conversation_id"]),
        sa.ForeignKeyConstraint(["sender_id"], [f"{SCHEMA}.users.user_id"]),
        schema=SCHEMA,
    )
    op.create_index("idx_msg_conv_time", "messages", ["conversation_id", "created_at"], schema=SCHEMA)

    # ============================================================
    # blacklist - 黑名单表
    # ============================================================
    op.create_table(
        "blacklist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(20), nullable=False),
        sa.Column("blocked_user_id", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(200), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.user_id"]),
        sa.ForeignKeyConstraint(["blocked_user_id"], [f"{SCHEMA}.users.user_id"]),
        sa.UniqueConstraint("user_id", "blocked_user_id", name="uq_blacklist"),
        sa.CheckConstraint("user_id != blocked_user_id", name="ck_no_self_block"),
        schema=SCHEMA,
    )
    op.create_index("idx_blacklist_user_id", "blacklist", ["user_id"], schema=SCHEMA)


def downgrade() -> None:
    """按相反顺序删除所有表（先删有外键依赖的表）。"""
    op.drop_table("blacklist", schema=SCHEMA)
    op.drop_table("messages", schema=SCHEMA)
    op.drop_table("conversations", schema=SCHEMA)
    op.drop_table("follow_relationships", schema=SCHEMA)
    op.drop_table("match_candidates", schema=SCHEMA)
    op.drop_table("match_records", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
