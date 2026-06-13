"""phase3_schema

Revision ID: c8cb8df8bf88
Revises: e53210659e25
Create Date: 2026-06-13 07:43:04.484734+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8cb8df8bf88'
down_revision: Union[str, None] = 'e53210659e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建新表
    op.create_table('fate_analyses',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('analysis_id', sa.String(length=40), nullable=False),
    sa.Column('initiator_id', sa.String(length=20), nullable=False),
    sa.Column('analysis_type', sa.String(length=30), nullable=False, comment='group_overview | deep_compatibility | comm_advice | comparison'),
    sa.Column('candidate_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('match_params_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parent_analysis_id', sa.String(length=40), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['initiator_id'], ['xinxi.users.user_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('analysis_id'),
    schema='xinxi'
    )
    op.create_index('idx_fate_analyses_initiator', 'fate_analyses', ['initiator_id', 'created_at'], unique=False, schema='xinxi')
    op.create_index(op.f('ix_xinxi_fate_analyses_initiator_id'), 'fate_analyses', ['initiator_id'], unique=False, schema='xinxi')
    op.create_table('fate_candidates',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=20), nullable=False),
    sa.Column('candidate_id', sa.String(length=20), nullable=False),
    sa.Column('note', sa.String(length=200), nullable=True),
    sa.Column('added_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('user_id != candidate_id', name='ck_fate_no_self'),
    sa.ForeignKeyConstraint(['candidate_id'], ['xinxi.users.user_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['xinxi.users.user_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'candidate_id', name='uq_fate_candidate'),
    schema='xinxi'
    )
    op.create_index(op.f('ix_xinxi_fate_candidates_candidate_id'), 'fate_candidates', ['candidate_id'], unique=False, schema='xinxi')
    op.create_index(op.f('ix_xinxi_fate_candidates_user_id'), 'fate_candidates', ['user_id'], unique=False, schema='xinxi')
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('notif_id', sa.String(length=40), nullable=False),
    sa.Column('recipient_id', sa.String(length=20), nullable=False),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('actor_id', sa.String(length=20), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['xinxi.users.user_id'], ),
    sa.ForeignKeyConstraint(['recipient_id'], ['xinxi.users.user_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('notif_id'),
    schema='xinxi'
    )
    op.create_index('idx_notifications_recipient', 'notifications', ['recipient_id', 'is_read', 'created_at'], unique=False, schema='xinxi')
    op.create_index(op.f('ix_xinxi_notifications_recipient_id'), 'notifications', ['recipient_id'], unique=False, schema='xinxi')

    # users 表新增字段
    op.add_column('users', sa.Column('birth_date', sa.Date(), nullable=True, comment='生日，用于自动计算星座和属相'), schema='xinxi')
    op.add_column('users', sa.Column('zodiac_sign', sa.String(length=10), nullable=True, comment='西方星座'), schema='xinxi')
    op.add_column('users', sa.Column('chinese_zodiac', sa.String(length=10), nullable=True, comment='属相'), schema='xinxi')
    # server_default='false' 确保已有行不报 NOT NULL 错误
    op.add_column('users', sa.Column('profile_complete', sa.Boolean(), nullable=False, server_default='false', comment='是否完成资料填写，True 才能出现在发现列表并发起匹配'), schema='xinxi')
    op.alter_column('users', 'age', existing_type=sa.INTEGER(), nullable=True, schema='xinxi')


def downgrade() -> None:
    op.alter_column('users', 'age', existing_type=sa.INTEGER(), nullable=False, schema='xinxi')
    op.drop_column('users', 'profile_complete', schema='xinxi')
    op.drop_column('users', 'chinese_zodiac', schema='xinxi')
    op.drop_column('users', 'zodiac_sign', schema='xinxi')
    op.drop_column('users', 'birth_date', schema='xinxi')
    op.drop_index(op.f('ix_xinxi_notifications_recipient_id'), table_name='notifications', schema='xinxi')
    op.drop_index('idx_notifications_recipient', table_name='notifications', schema='xinxi')
    op.drop_table('notifications', schema='xinxi')
    op.drop_index(op.f('ix_xinxi_fate_candidates_user_id'), table_name='fate_candidates', schema='xinxi')
    op.drop_index(op.f('ix_xinxi_fate_candidates_candidate_id'), table_name='fate_candidates', schema='xinxi')
    op.drop_table('fate_candidates', schema='xinxi')
    op.drop_index(op.f('ix_xinxi_fate_analyses_initiator_id'), table_name='fate_analyses', schema='xinxi')
    op.drop_index('idx_fate_analyses_initiator', table_name='fate_analyses', schema='xinxi')
    op.drop_table('fate_analyses', schema='xinxi')
