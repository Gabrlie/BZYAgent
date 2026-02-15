"""add copyright project tables

Revision ID: 4f9b2b6c7d1e
Revises: 6b6c5b3d7a8a
Create Date: 2026-02-15 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f9b2b6c7d1e"
down_revision: Union[str, Sequence[str], None] = "6b6c5b3d7a8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "copyright_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("system_name", sa.String(length=200), nullable=True),
        sa.Column("software_abbr", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("output_type", sa.String(length=20), nullable=False),
        sa.Column("generation_mode", sa.String(length=20), nullable=False),
        sa.Column("include_sourcecode", sa.Boolean(), nullable=False),
        sa.Column("include_ui_desc", sa.Boolean(), nullable=False),
        sa.Column("include_tech_desc", sa.Boolean(), nullable=False),
        sa.Column("requirements_text", sa.Text(), nullable=True),
        sa.Column("ui_description", sa.Text(), nullable=True),
        sa.Column("tech_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_copyright_projects_id"), "copyright_projects", ["id"], unique=False)
    op.create_index(
        op.f("ix_copyright_projects_user_id"),
        "copyright_projects",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "copyright_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("output_zip_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["copyright_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_copyright_jobs_id"), "copyright_jobs", ["id"], unique=False)
    op.create_index(
        op.f("ix_copyright_jobs_project_id"),
        "copyright_jobs",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_copyright_jobs_project_id"), table_name="copyright_jobs")
    op.drop_index(op.f("ix_copyright_jobs_id"), table_name="copyright_jobs")
    op.drop_table("copyright_jobs")
    op.drop_index(op.f("ix_copyright_projects_user_id"), table_name="copyright_projects")
    op.drop_index(op.f("ix_copyright_projects_id"), table_name="copyright_projects")
    op.drop_table("copyright_projects")
