"""add knowledge base to documents

Revision ID: 20260405_000002
Revises: 20260403_000001
Create Date: 2026-04-05 03:25:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260405_000002"
down_revision: Union[str, Sequence[str], None] = "20260403_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS knowledge_base TEXT NOT NULL DEFAULT 'default'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
        DROP COLUMN IF EXISTS knowledge_base
        """
    )
