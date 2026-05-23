"""Add internal message board tables.

Revision ID: 20260523_0003
Revises: 20260522_0002
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260523_0003"
down_revision = "20260522_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_message_threads_created_at", "message_threads", ["created_at"])
    op.create_table(
        "message_replies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_message_replies_thread_id", "message_replies", ["thread_id"])
    op.create_index("ix_message_replies_created_at", "message_replies", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_message_replies_created_at", table_name="message_replies")
    op.drop_index("ix_message_replies_thread_id", table_name="message_replies")
    op.drop_table("message_replies")
    op.drop_index("ix_message_threads_created_at", table_name="message_threads")
    op.drop_table("message_threads")
