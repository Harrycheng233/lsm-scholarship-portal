"""Add institution duration and normalize v2 vocabularies.

Revision ID: 20260522_0002
Revises: 20260521_0001
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260522_0002"
down_revision = "20260521_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schools", sa.Column("duration_years", sa.Integer(), nullable=False, server_default="1"))
    op.execute("UPDATE schools SET status = 'Paused' WHERE status = 'Pause'")
    op.execute("UPDATE schools SET status = 'Awaiting Agreement' WHERE status IN ('Pending', 'Waiting Agreement')")
    op.execute("UPDATE schools SET scholarship_type = 'Endowed' WHERE scholarship_type = 'Annual'")
    op.execute("UPDATE programs SET status = 'Paused' WHERE status = 'Pause'")
    op.execute("UPDATE programs SET status = 'Awaiting Agreement' WHERE status IN ('Pending', 'Waiting Agreement')")
    op.execute("UPDATE programs SET program_type = 'Endowed' WHERE program_type IN ('Annual', 'Annual Grant')")


def downgrade() -> None:
    op.drop_column("schools", "duration_years")
