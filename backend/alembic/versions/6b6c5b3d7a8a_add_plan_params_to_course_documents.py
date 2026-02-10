"""add plan_params to course_documents

Revision ID: 6b6c5b3d7a8a
Revises: 21fe841fe1b6
Create Date: 2026-02-09 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b6c5b3d7a8a"
down_revision: Union[str, Sequence[str], None] = "21fe841fe1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("course_documents", sa.Column("plan_params", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("course_documents", "plan_params")
