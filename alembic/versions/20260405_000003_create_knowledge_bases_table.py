"""create knowledge bases table

Revision ID: 20260405_000003
Revises: 20260405_000002
Create Date: 2026-04-05 01:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260405_000003"
down_revision = "20260405_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        """
        INSERT INTO knowledge_bases(name, created_at)
        SELECT knowledge_base, MIN(created_at)
        FROM documents
        WHERE knowledge_base IS NOT NULL AND knowledge_base <> ''
        GROUP BY knowledge_base
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("knowledge_bases")
