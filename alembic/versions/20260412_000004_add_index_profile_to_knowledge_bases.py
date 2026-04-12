"""add indexing profile columns to knowledge bases

Revision ID: 20260412_000004
Revises: 20260405_000003
Create Date: 2026-04-12 20:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260412_000004"
down_revision = "20260405_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("profile_mode", sa.Text(), nullable=False, server_default="balanced"),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("chunk_size_tokens", sa.Integer(), nullable=False, server_default="320"),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("chunk_overlap_tokens", sa.Integer(), nullable=False, server_default="64"),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("chunk_keyword_limit", sa.Integer(), nullable=False, server_default="6"),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("document_keyword_limit", sa.Integer(), nullable=False, server_default="16"),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "document_keyword_limit")
    op.drop_column("knowledge_bases", "chunk_keyword_limit")
    op.drop_column("knowledge_bases", "chunk_overlap_tokens")
    op.drop_column("knowledge_bases", "chunk_size_tokens")
    op.drop_column("knowledge_bases", "profile_mode")
