"""add copyright job progress fields

Revision ID: 6c8f6f1b8b2f
Revises: 4f9b2b6c7d1e
Create Date: 2026-02-15 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c8f6f1b8b2f"
down_revision: Union[str, Sequence[str], None] = "4f9b2b6c7d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("copyright_jobs", sa.Column("stage", sa.String(length=30), nullable=True))
    op.add_column("copyright_jobs", sa.Column("message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("copyright_jobs", "message")
    op.drop_column("copyright_jobs", "stage")
