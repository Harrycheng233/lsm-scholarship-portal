from __future__ import annotations

import datetime as dt
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.auth import User
from backend.app.models.core import AuditLog, Award, Document, Program, Scholar, School, VersionLog
from backend.app.services.audit import audit_log_rows, record_audit
from backend.app.services.security import create_token, hash_password, verify_password, verify_token
from backend.app.services.exporter import build_backup_workbook
from backend.app.services.portal import bootstrap, create_institution, create_scholar, version_log_rows


def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    return Session()


def add_school(db, name, department, status="Active"):
    result = create_institution(
        db,
        {
            "name": name,
            "program_department": department,
            "country": "United States",
            "continent": "NA",
            "scholarship_type": "Annual",
            "status": status,
            "agreement_date": "2026-01-01",
            "notes": "",
        },
    )
    return result["id"]


def test_dashboard_deduplicates_departments_under_same_institution():
    db = session()
    add_school(db, "Columbia University", "School of Art")
    add_school(db, "  columbia   university ", "School of Design")

    data = bootstrap(db)

    assert data["dashboard"]["summary"]["institutions"] == 1
    assert data["dashboard"]["summary"]["countries"] == 1
    assert len(data["dashboard"]["details"]["institutions"]) == 1


def test_awaiting_agreement_is_pending_but_not_partnered():
    db = session()
    add_school(db, "Awaiting School", "Department", status="Awaiting Agreement")

    data = bootstrap(db)

    assert data["dashboard"]["summary"]["institutions"] == 0
    assert data["dashboard"]["summary"]["pendingPrograms"] == 1


def test_pause_counts_as_partnered_but_is_excluded_from_followups():
    db = session()
    school_id = add_school(db, "Paused School", "Department", status="Pause")
    next_month = (dt.date.today().replace(day=1) + dt.timedelta(days=35)).replace(day=15)
    create_scholar(
        db,
        {
            "full_name": "Paused Scholar",
            "gender": "Female",
            "major": "Math",
            "contact": "paused@example.org",
            "award_date": next_month.isoformat(),
            "school_id": school_id,
            "scholarship_plan": "One-time",
            "support_years": 1,
        },
    )

    data = bootstrap(db)

    assert data["dashboard"]["summary"]["institutions"] == 1
    assert data["dashboard"]["followups"] == []


def test_multi_year_awards_use_scholar_award_date_not_agreement_date():
    db = session()
    school_id = add_school(db, "Lifecycle University", "Department")
    create_scholar(
        db,
        {
            "full_name": "Multi Year Scholar",
            "gender": "Female",
            "major": "Physics",
            "contact": "scholar@example.org",
            "award_date": "2026-06-15",
            "school_id": school_id,
            "scholarship_plan": "Multi-year",
            "support_years": 3,
        },
    )

    awards = [row.academic_year for row in db.query(Award).order_by(Award.year_of_support).all()]

    assert awards == ["2025-2026", "2026-2027", "2027-2028"]


def test_manual_entry_validation_rejects_invalid_institution_continent():
    db = session()

    with pytest.raises(ValueError, match="Continent"):
        create_institution(
            db,
            {
                "name": "Invalid Continent University",
                "program_department": "Department",
                "country": "United States",
                "continent": "XX",
                "scholarship_type": "Annual",
                "status": "Active",
            },
        )


def test_manual_entry_validation_rejects_invalid_support_years():
    db = session()
    school_id = add_school(db, "Validation University", "Department")

    with pytest.raises(ValueError, match="between 1 and 10"):
        create_scholar(
            db,
            {
                "full_name": "Too Long Scholar",
                "gender": "Female",
                "award_date": "2026-09-01",
                "school_id": school_id,
                "scholarship_plan": "Multi-year",
                "support_years": 11,
            },
        )


def test_excel_export_contains_schools_and_scholars_tabs_with_input_fields():
    db = session()
    school_id = add_school(db, "Export University", "Business School")
    create_scholar(
        db,
        {
            "full_name": "Export Scholar",
            "gender": "Male",
            "major": "Finance",
            "contact": "export@example.org",
            "award_date": "2026-09-01",
            "school_id": school_id,
            "scholarship_plan": "One-time",
            "support_years": 1,
        },
    )

    workbook = load_workbook(BytesIO(build_backup_workbook(db)))

    assert workbook.sheetnames == ["Schools", "Scholars"]
    assert workbook["Schools"]["A1"].value == "Institution"
    assert workbook["Schools"]["B2"].value == "Business School"
    assert workbook["Scholars"]["A1"].value == "Full Name"
    assert workbook["Scholars"]["A2"].value == "Export Scholar"


def test_version_log_rows_are_newest_first():
    db = session()
    db.add_all(
        [
            VersionLog(version="1.9", title="Baseline", notes="Local portal", released_at="2026-05-18"),
            VersionLog(version="2.0-dev", title="Migration", notes="FastAPI foundation", released_at="2026-05-21"),
        ]
    )
    db.commit()

    rows = version_log_rows(db)

    assert [row["version"] for row in rows] == ["2.0-dev", "1.9"]


def test_password_hash_and_token_round_trip():
    password_hash = hash_password("correct horse battery staple")
    token = create_token(42, "admin@example.org")

    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong", password_hash)
    assert verify_token(token)["sub"] == 42


def test_audit_log_rows_are_newest_first():
    db = session()
    record_audit(db, "admin@example.org", "create", "Institution", 1, "Created A.", commit=True)
    record_audit(db, "admin@example.org", "export", "Workbook", None, "Exported backup.", commit=True)

    rows = audit_log_rows(db)

    assert rows[0]["action"] == "export"
    assert rows[0]["summary"] == "Exported backup."
    assert rows[1]["entity_type"] == "Institution"
