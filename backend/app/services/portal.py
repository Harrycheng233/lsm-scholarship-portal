from __future__ import annotations

import datetime as dt
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models.core import Award, Document, Program, Scholar, School, VersionLog
from .audit import audit_log_rows
from .rules import (
    CONTINENTS,
    CURRENT_STATUSES,
    FOLLOWUP_STATUSES,
    PENDING_STATUSES,
    add_years,
    academic_year_from_award_time,
    clean,
    default_program_name,
    institution_key,
    issue_date_from_award_time,
    new_york_today,
    parse_iso_date,
    split_name,
)


INSTITUTION_STATUSES = {"Active", "Pending", "Awaiting Agreement", "Pause", "Paused", "Completed"}
SCHOLARSHIP_TYPES = {"Endowed", "One-time", "Multi-year", "Annual"}
SCHOLARSHIP_PLANS = {"One-time", "Multi-year"}
GENDERS = {"Prefer not to say", "Female", "Male", "Other"}


def row_dict(obj, fields: list[str]) -> dict:
    return {field: getattr(obj, field) for field in fields}


def ensure_program_for_school(db: Session, school_id: int) -> int:
    school = db.get(School, school_id)
    if not school:
        raise ValueError("Institution not found.")
    program = db.scalars(select(Program).where(Program.school_id == school_id).order_by(Program.id)).first()
    name = default_program_name(school)
    if program:
        program.name = name
        program.program_type = school.scholarship_type
        program.status = school.status
        db.flush()
        return program.id
    program = Program(
        school_id=school_id,
        name=name,
        program_type=school.scholarship_type,
        funding_model="Annual Appropriation",
        status=school.status,
    )
    db.add(program)
    db.flush()
    return program.id


def create_awards_for_scholar(db: Session, scholar_id: int, school_id: int, award_time: str, support_years: int) -> None:
    program_id = ensure_program_for_school(db, school_id)
    db.execute(delete(Award).where(Award.scholar_id == scholar_id))
    for idx in range(max(1, int(support_years or 1))):
        db.add(
            Award(
                scholar_id=scholar_id,
                program_id=program_id,
                academic_year=academic_year_from_award_time(award_time, idx),
                new_or_renewal="New" if idx == 0 else "Renewal",
                year_of_support=idx + 1,
                status="Active",
            )
        )
    db.flush()


def award_issue_date(award: Award) -> dt.date | None:
    return issue_date_from_award_time(award.scholar.award_time, award.year_of_support)


def issued_award_count(awards: list[Award], today: dt.date | None = None) -> int:
    today = today or new_york_today()
    return sum(1 for award in awards if (award_issue_date(award) or dt.date.max) <= today)


def scholar_issue_summary(scholar: Scholar, today: dt.date | None = None) -> dict:
    today = today or new_york_today()
    awards = sorted(scholar.awards, key=lambda award: (award.year_of_support, award.id))
    total = max(1, int(scholar.support_years or 1), len(awards))
    issued = issued_award_count(awards, today)
    next_issue = None
    for year in range(1, total + 1):
        issue_date = issue_date_from_award_time(scholar.award_time, year)
        if issue_date and issue_date > today:
            next_issue = issue_date
            break
    return {
        "issued": issued,
        "total": total,
        "progress": f"{issued}/{total}",
        "next_issue_date": next_issue.isoformat() if next_issue else "",
    }


def school_issued_count(db: Session, school_id: int, today: dt.date | None = None) -> int:
    today = today or new_york_today()
    awards = db.scalars(select(Award).join(Program, Program.id == Award.program_id).where(Program.school_id == school_id)).all()
    return issued_award_count(list(awards), today)


def institution_rows(db: Session) -> list[dict]:
    rows = []
    today = new_york_today()
    schools = db.scalars(select(School).order_by(School.name)).all()
    for school in schools:
        item = row_dict(
            school,
            ["id", "name", "program_department", "country", "continent", "scholarship_type", "status", "agreement_date", "notes", "created_at"],
        )
        item["scholarships_issued"] = school_issued_count(db, school.id, today)
        rows.append(item)
    return rows


def scholar_rows(db: Session) -> list[dict]:
    result = []
    today = new_york_today()
    scholars = db.scalars(select(Scholar).order_by(Scholar.full_name)).all()
    for scholar in scholars:
        school = scholar.school
        issue_summary = scholar_issue_summary(scholar, today)
        item = row_dict(
            scholar,
            [
                "id",
                "first_name",
                "last_name",
                "full_name",
                "gender",
                "nationality",
                "email",
                "data_status",
                "notes",
                "created_at",
                "major",
                "contact",
                "award_time",
                "school_id",
                "scholarship_plan",
                "support_years",
            ],
        )
        item["award_date"] = scholar.award_time
        item["institution_name"] = school.name if school else None
        item["country"] = school.country if school else None
        item["continent"] = school.continent if school else None
        item["scholarships_issued"] = issue_summary["issued"]
        item["scholarships_total"] = issue_summary["total"]
        item["scholarship_progress"] = issue_summary["progress"]
        item["next_issue_date"] = issue_summary["next_issue_date"]
        result.append(item)
    return result


def award_rows(db: Session) -> list[dict]:
    today = new_york_today()
    awards = db.scalars(select(Award).order_by(Award.academic_year.desc(), Award.id.desc())).all()
    result = []
    for award in awards:
        item = row_dict(award, ["id", "scholar_id", "program_id", "academic_year", "new_or_renewal", "year_of_support", "status", "notes", "created_at"])
        issue_date = award_issue_date(award)
        item["scholar_name"] = award.scholar.full_name
        item["program_name"] = award.program.name
        item["institution_name"] = award.program.school.name
        item["issue_date"] = issue_date.isoformat() if issue_date else ""
        item["issued"] = bool(issue_date and issue_date <= today)
        result.append(item)
    return result


def version_log_rows(db: Session) -> list[dict]:
    logs = db.scalars(select(VersionLog).order_by(VersionLog.released_at.desc(), VersionLog.id.desc())).all()
    return [row_dict(log, ["id", "version", "title", "notes", "released_at"]) for log in logs]


def count_by(items: list[dict], key_name: str, fallback: str = "Unspecified") -> list[dict]:
    counts: dict[str, int] = {}
    for item in items:
        label = clean(item.get(key_name)) or fallback
        counts[label] = counts.get(label, 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))]


def statistics(db: Session) -> dict:
    eligible_school_ids = [row[0] for row in db.execute(select(School.id).where(School.status.in_(CURRENT_STATUSES))).all()]
    scholars = []
    if eligible_school_ids:
        for scholar in db.scalars(select(Scholar).where(Scholar.school_id.in_(eligible_school_ids))).all():
            school = scholar.school
            scholars.append(
                {
                    "id": scholar.id,
                    "gender": scholar.gender,
                    "major": scholar.major,
                    "country": school.country if school else "",
                    "continent": school.continent if school else "",
                    "institution_name": school.name if school else "",
                }
            )

    annual: dict[str, dict] = {}
    country_buckets: dict[str, dict] = {}
    for school in db.scalars(select(School).where(School.status.in_(CURRENT_STATUSES))).all():
        country = clean(school.country) or "Unspecified"
        bucket = country_buckets.setdefault(country, {"country": country, "continent": clean(school.continent), "institution_keys": set(), "scholar_ids": set(), "scholarship_count": 0})
        bucket["institution_keys"].add(institution_key(school.name))

    for scholar in scholars:
        country = clean(scholar.get("country")) or "Unspecified"
        bucket = country_buckets.setdefault(country, {"country": country, "continent": clean(scholar.get("continent")), "institution_keys": set(), "scholar_ids": set(), "scholarship_count": 0})
        bucket["scholar_ids"].add(scholar["id"])

    today = new_york_today()
    awards = db.scalars(select(Award)).all()
    for award in awards:
        school = award.program.school
        scholar = award.scholar
        if not school or school.status not in CURRENT_STATUSES:
            continue
        issue_date = award_issue_date(award)
        if not issue_date or issue_date > today:
            continue
        year = (award.academic_year or "")[:4]
        if year:
            bucket = annual.setdefault(year, {"year": year, "institution_keys": set(), "scholar_ids": set(), "scholarship_count": 0})
            bucket["institution_keys"].add(institution_key(school.name))
            bucket["scholar_ids"].add(scholar.id)
            bucket["scholarship_count"] += 1
        country = clean(school.country) or "Unspecified"
        country_bucket = country_buckets.setdefault(country, {"country": country, "continent": clean(school.continent), "institution_keys": set(), "scholar_ids": set(), "scholarship_count": 0})
        country_bucket["scholarship_count"] += 1

    annual_rows = [
        {"year": year, "institution_count": len(bucket["institution_keys"]), "scholar_count": len(bucket["scholar_ids"]), "scholarship_count": bucket["scholarship_count"]}
        for year, bucket in sorted(annual.items())
    ]
    country_rows = [
        {"country": country, "continent": bucket["continent"], "institution_count": len(bucket["institution_keys"]), "scholar_count": len(bucket["scholar_ids"]), "scholarship_count": bucket["scholarship_count"]}
        for country, bucket in sorted(country_buckets.items(), key=lambda pair: pair[0].casefold())
    ]
    return {"genderCounts": count_by(scholars, "gender"), "majorCounts": count_by(scholars, "major"), "annual": annual_rows, "countryStats": country_rows}


def validate_date(value: str, field: str, required: bool = False) -> str:
    value = clean(value)
    if not value:
        if required:
            raise ValueError(f"{field} is required.")
        return ""
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid date.") from exc
    return value


def validate_institution_payload(payload: dict) -> dict:
    data = {
        "name": clean(payload.get("name")),
        "program_department": clean(payload.get("program_department")),
        "country": clean(payload.get("country")),
        "continent": clean(payload.get("continent")).upper(),
        "scholarship_type": payload.get("scholarship_type", "Annual"),
        "status": payload.get("status", "Active"),
        "agreement_date": validate_date(payload.get("agreement_date"), "Agreement date"),
        "notes": clean(payload.get("notes")),
    }
    if not data["name"]:
        raise ValueError("Institution name is required.")
    if not data["country"]:
        raise ValueError("Country is required.")
    if data["continent"] not in CONTINENTS:
        raise ValueError("Continent must be one of AS, EU, AF, NA, SA, or OC.")
    if data["scholarship_type"] not in SCHOLARSHIP_TYPES:
        raise ValueError("Scholarship type is not valid.")
    if data["status"] not in INSTITUTION_STATUSES:
        raise ValueError("Institution status is not valid.")
    return data


def validate_scholar_payload(db: Session, payload: dict) -> dict:
    full_name = clean(payload.get("full_name"))
    award_time = validate_date(payload.get("award_date") or payload.get("award_time"), "Award date", required=True)
    school_id = int(payload.get("school_id") or 0)
    plan = payload.get("scholarship_plan", "One-time")
    support_years = int(payload.get("support_years") or 1)
    gender = payload.get("gender", "Prefer not to say")
    if not full_name:
        raise ValueError("Full name is required.")
    if not school_id or not db.get(School, school_id):
        raise ValueError("Institution is required.")
    if plan not in SCHOLARSHIP_PLANS:
        raise ValueError("Scholarship duration is not valid.")
    if gender not in GENDERS:
        raise ValueError("Sex is not valid.")
    if plan != "Multi-year":
        support_years = 1
    if support_years < 1 or support_years > 10:
        raise ValueError("Number of years must be between 1 and 10.")
    return {
        "full_name": full_name,
        "award_time": award_time,
        "school_id": school_id,
        "scholarship_plan": plan,
        "support_years": support_years,
        "gender": gender,
        "major": clean(payload.get("major")),
        "contact": clean(payload.get("contact")),
        "notes": clean(payload.get("notes")),
    }


def dashboard(db: Session) -> dict:
    today = new_york_today()
    active_rows = []
    for row in institution_rows(db):
        if row["status"] in CURRENT_STATUSES:
            active_rows.append(row)

    by_institution: dict[str, dict] = {}
    for item in active_rows:
        key = institution_key(item["name"])
        if key not in by_institution:
            by_institution[key] = {
                "name": item["name"],
                "country": item["country"],
                "continent": item["continent"],
                "scholarships_issued": 0,
            }
        by_institution[key]["scholarships_issued"] += item["scholarships_issued"] or 0

    country_counts = {}
    continent_counts = {code: 0 for code in CONTINENTS}
    for item in by_institution.values():
        country = clean(item["country"])
        if country:
            country_counts[country] = country_counts.get(country, 0) + 1
        code = clean(item["continent"]).upper()
        if code in continent_counts:
            continent_counts[code] += 1

    pending_programs = [row for row in institution_rows(db) if row["status"] in PENDING_STATUSES]
    issued_awards = db.scalars(select(Award)).all()
    issued_count = issued_award_count(list(issued_awards), today)
    summary = {
        "institutions": len(by_institution),
        "recipients": db.scalar(select(func.count(Scholar.id))) or 0,
        "countries": len(country_counts),
        "pendingPrograms": len(pending_programs),
        "scholarshipsIssued": issued_count,
    }

    upcoming = []
    followup_counts = {"thisMonth": 0, "nextMonth": 0}
    next_month = 1 if today.month == 12 else today.month + 1
    next_month_year = today.year + 1 if today.month == 12 else today.year
    schools = db.scalars(select(School).where(School.status.in_(FOLLOWUP_STATUSES))).all()
    for school in schools:
        agreement_date = parse_iso_date(school.agreement_date)
        if not agreement_date:
            continue
        bucket = None
        follow_year = today.year
        if agreement_date.month == today.month:
            bucket = "thisMonth"
        elif agreement_date.month == next_month:
            bucket = "nextMonth"
            follow_year = next_month_year
        if bucket:
            due = add_years(agreement_date, follow_year - agreement_date.year)
            followup_counts[bucket] += 1
            upcoming.append(
                {
                    "school_id": school.id,
                    "institution_name": school.name,
                    "program_department": school.program_department,
                    "country": school.country,
                    "continent": school.continent,
                    "status": school.status,
                    "agreement_date": school.agreement_date,
                    "cycle": bucket,
                    "followup_date": due.isoformat(),
                    "days_until": (due - today).days,
                }
            )
    upcoming.sort(key=lambda x: x["followup_date"])

    scholarship_details = []
    for scholar in db.scalars(select(Scholar).order_by(Scholar.full_name)).all():
        school = scholar.school
        summary_row = scholar_issue_summary(scholar, today)
        if summary_row["issued"] <= 0:
            continue
        scholarship_details.append(
            {
                "scholar_name": scholar.full_name,
                "institution_name": school.name if school else "",
                "program_department": school.program_department if school else "",
                "award_date": scholar.award_time,
                "progress": summary_row["progress"],
                "issued": summary_row["issued"],
                "total": summary_row["total"],
                "next_issue_date": summary_row["next_issue_date"],
            }
        )

    details = {
        "institutions": sorted(by_institution.values(), key=lambda row: row["name"]),
        "countries": [{"country": country, "institution_count": count} for country, count in sorted(country_counts.items())],
        "pendingPrograms": sorted(pending_programs, key=lambda row: (row["status"], row["name"])),
        "scholarshipsIssued": scholarship_details,
    }
    return {"summary": summary, "followups": upcoming[:8], "followupCounts": followup_counts, "continentCounts": continent_counts, "details": details}


def collections(db: Session) -> dict:
    institutions = institution_rows(db)
    return {
        "institutions": institutions,
        "schools": institutions,
        "scholars": scholar_rows(db),
        "awards": award_rows(db),
        "statistics": statistics(db),
        "versionLogs": version_log_rows(db),
        "auditLogs": audit_log_rows(db),
    }


def bootstrap(db: Session) -> dict:
    return {"meta": {"version": "v2.0", "timezone": "America/New_York", "current_date": new_york_today().isoformat()}, "dashboard": dashboard(db), **collections(db)}


def create_institution(db: Session, payload: dict) -> dict:
    data = validate_institution_payload(payload)
    school = School(
        name=data["name"],
        program_department=data["program_department"],
        country=data["country"],
        continent=data["continent"],
        scholarship_type=data["scholarship_type"],
        status=data["status"],
        agreement_date=data["agreement_date"],
        notes=data["notes"],
        partner_type="University",
    )
    db.add(school)
    db.flush()
    ensure_program_for_school(db, school.id)
    db.commit()
    return {"ok": True, "id": school.id}


def update_institution(db: Session, institution_id: int, payload: dict) -> dict:
    school = db.get(School, institution_id)
    if not school:
        raise ValueError("Institution not found.")
    data = validate_institution_payload(payload)
    school.name = data["name"]
    school.program_department = data["program_department"]
    school.country = data["country"]
    school.continent = data["continent"]
    school.scholarship_type = data["scholarship_type"]
    school.status = data["status"]
    school.agreement_date = data["agreement_date"]
    school.notes = data["notes"]
    ensure_program_for_school(db, institution_id)
    db.commit()
    return {"ok": True, "id": institution_id}


def create_scholar(db: Session, payload: dict) -> dict:
    data = validate_scholar_payload(db, payload)
    full_name = data["full_name"]
    first_name, last_name = split_name(full_name)
    scholar = Scholar(
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        gender=data["gender"],
        major=data["major"],
        contact=data["contact"],
        award_time=data["award_time"],
        school_id=data["school_id"],
        scholarship_plan=data["scholarship_plan"],
        support_years=data["support_years"],
        data_status="Pending Human Verification",
        notes=data["notes"],
    )
    db.add(scholar)
    db.flush()
    create_awards_for_scholar(db, scholar.id, data["school_id"], data["award_time"], data["support_years"])
    db.commit()
    return {"ok": True, "id": scholar.id, "scholarships_issued": scholar_issue_summary(scholar)["issued"]}


def update_scholar(db: Session, scholar_id: int, payload: dict) -> dict:
    scholar = db.get(Scholar, scholar_id)
    if not scholar:
        raise ValueError("Scholar not found.")
    data = validate_scholar_payload(db, payload)
    full_name = data["full_name"]
    first_name, last_name = split_name(full_name)
    scholar.first_name = first_name
    scholar.last_name = last_name
    scholar.full_name = full_name
    scholar.gender = data["gender"]
    scholar.major = data["major"]
    scholar.contact = data["contact"]
    scholar.award_time = data["award_time"]
    scholar.school_id = data["school_id"]
    scholar.scholarship_plan = data["scholarship_plan"]
    scholar.support_years = data["support_years"]
    scholar.notes = data["notes"]
    create_awards_for_scholar(db, scholar_id, data["school_id"], data["award_time"], data["support_years"])
    db.commit()
    return {"ok": True, "id": scholar_id, "scholarships_issued": scholar_issue_summary(scholar)["issued"]}


def delete_institution(db: Session, institution_id: int) -> dict:
    scholar_ids = [row[0] for row in db.execute(select(Scholar.id).where(Scholar.school_id == institution_id)).all()]
    if scholar_ids:
        db.execute(delete(Document).where(Document.linked_type == "Scholar", Document.linked_id.in_(scholar_ids)))
        db.execute(delete(Award).where(Award.scholar_id.in_(scholar_ids)))
        db.execute(delete(Scholar).where(Scholar.id.in_(scholar_ids)))
    db.execute(delete(Program).where(Program.school_id == institution_id))
    db.execute(delete(School).where(School.id == institution_id))
    db.commit()
    return {"ok": True}


def delete_scholar(db: Session, scholar_id: int) -> dict:
    db.execute(delete(Document).where(Document.linked_type == "Scholar", Document.linked_id == scholar_id))
    db.execute(delete(Award).where(Award.scholar_id == scholar_id))
    db.execute(delete(Scholar).where(Scholar.id == scholar_id))
    db.commit()
    return {"ok": True}
