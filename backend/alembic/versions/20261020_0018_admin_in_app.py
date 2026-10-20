"""installation_state.admin_in_app: users managed in the app or only in the owner panel

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-20 10:00:56.128870
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('installation_state', sa.Column('admin_in_app', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('installation_state', 'admin_in_app')
