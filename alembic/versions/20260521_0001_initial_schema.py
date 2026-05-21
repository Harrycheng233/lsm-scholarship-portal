"""Initial production schema.

Revision ID: 20260521_0001
Revises:
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("continent", sa.Text()),
        sa.Column("partner_type", sa.Text(), nullable=False, server_default="University"),
        sa.Column("status", sa.Text(), nullable=False, server_default="Active"),
        sa.Column("contact_person", sa.Text()),
        sa.Column("contact_email", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text()),
        sa.Column("program_department", sa.Text()),
        sa.Column("scholarship_type", sa.Text(), nullable=False, server_default="Annual"),
        sa.Column("agreement_date", sa.Text()),
    )
    op.create_table(
        "programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("program_type", sa.Text(), nullable=False, server_default="Annual Grant"),
        sa.Column("funding_model", sa.Text(), nullable=False, server_default="Annual Appropriation"),
        sa.Column("established_year", sa.Integer()),
        sa.Column("status", sa.Text(), nullable=False, server_default="Active"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text()),
    )
    op.create_table(
        "scholars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.Text()),
        sa.Column("last_name", sa.Text()),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("gender", sa.Text(), nullable=False, server_default="Prefer not to say"),
        sa.Column("nationality", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("data_status", sa.Text(), nullable=False, server_default="Pending Human Verification"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text()),
        sa.Column("major", sa.Text()),
        sa.Column("contact", sa.Text()),
        sa.Column("award_time", sa.Text()),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id")),
        sa.Column("scholarship_plan", sa.Text(), nullable=False, server_default="One-time"),
        sa.Column("support_years", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "awards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scholar_id", sa.Integer(), sa.ForeignKey("scholars.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.Text(), nullable=False),
        sa.Column("new_or_renewal", sa.Text(), nullable=False, server_default="New"),
        sa.Column("year_of_support", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.Text(), nullable=False, server_default="Active"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text()),
        sa.UniqueConstraint("scholar_id", "program_id", "academic_year"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("linked_type", sa.Text(), nullable=False),
        sa.Column("linked_id", sa.Integer()),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("stored_name", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="editor"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "version_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("released_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_version_logs_version", "version_logs", ["version"], unique=True)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_version_logs_version", table_name="version_logs")
    op.drop_table("version_logs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("documents")
    op.drop_table("awards")
    op.drop_table("scholars")
    op.drop_table("programs")
    op.drop_table("schools")
