"""add_photos_field

Revision ID: e53210659e25
Revises: 001
Create Date: 2026-06-13 06:36:31.815956+00:00

学习要点：
- 给已有数据的表添加 NOT NULL 列时，需要提供 server_default
- server_default='[]' 让现有行的 photos 字段默认为空 JSON 数组
- 等添加完列后，可以选择移除 server_default（本项目保留，便于维护）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e53210659e25'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'photos',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',  # 已有行默认为空数组
            comment='用户照片 URL 列表，最多 6 张',
        ),
        schema='xinxi',
    )


def downgrade() -> None:
    op.drop_column('users', 'photos', schema='xinxi')
