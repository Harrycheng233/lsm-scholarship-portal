from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    continent: Mapped[str | None] = mapped_column(Text)
    partner_type: Mapped[str] = mapped_column(Text, default="University", nullable=False)
    status: Mapped[str] = mapped_column(Text, default="Active", nullable=False)
    contact_person: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(Text)
    program_department: Mapped[str | None] = mapped_column(Text)
    scholarship_type: Mapped[str] = mapped_column(Text, default="Endowed", nullable=False)
    agreement_date: Mapped[str | None] = mapped_column(Text)
    duration_years: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    programs: Mapped[list["Program"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    scholars: Mapped[list["Scholar"]] = relationship(back_populates="school")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    program_type: Mapped[str] = mapped_column(Text, default="Endowed", nullable=False)
    funding_model: Mapped[str] = mapped_column(Text, default="Annual Appropriation", nullable=False)
    established_year: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, default="Active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(Text)

    school: Mapped[School] = relationship(back_populates="programs")
    awards: Mapped[list["Award"]] = relationship(back_populates="program", cascade="all, delete-orphan")


class Scholar(Base):
    __tablename__ = "scholars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[str] = mapped_column(Text, default="Prefer not to say", nullable=False)
    nationality: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    data_status: Mapped[str] = mapped_column(Text, default="Pending Human Verification", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(Text)
    major: Mapped[str | None] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(Text)
    award_time: Mapped[str | None] = mapped_column(Text)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"))
    scholarship_plan: Mapped[str] = mapped_column(Text, default="One-time", nullable=False)
    support_years: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    school: Mapped[School | None] = relationship(back_populates="scholars")
    awards: Mapped[list["Award"]] = relationship(back_populates="scholar", cascade="all, delete-orphan")


class Award(Base):
    __tablename__ = "awards"
    __table_args__ = (UniqueConstraint("scholar_id", "program_id", "academic_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scholar_id: Mapped[int] = mapped_column(ForeignKey("scholars.id", ondelete="CASCADE"), nullable=False)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    academic_year: Mapped[str] = mapped_column(Text, nullable=False)
    new_or_renewal: Mapped[str] = mapped_column(Text, default="New", nullable=False)
    year_of_support: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="Active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(Text)

    scholar: Mapped[Scholar] = relationship(back_populates="awards")
    program: Mapped[Program] = relationship(back_populates="awards")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    linked_type: Mapped[str] = mapped_column(Text, nullable=False)
    linked_id: Mapped[int | None] = mapped_column(Integer)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    stored_name: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(Text)


class VersionLog(Base):
    __tablename__ = "version_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    released_at: Mapped[str] = mapped_column(Text, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
