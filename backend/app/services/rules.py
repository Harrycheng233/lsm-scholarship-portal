from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from ..config import settings


CURRENT_STATUSES = ("Active", "Pending", "Completed", "Pause", "Paused")
PENDING_STATUSES = ("Pending", "Awaiting Agreement")
FOLLOWUP_STATUSES = ("Active",)
CONTINENTS = ("AS", "EU", "AF", "NA", "SA", "OC")


def clean(value) -> str:
    return str(value or "").strip()


def institution_key(value) -> str:
    return " ".join(clean(value).lower().split())


def split_name(full_name: str) -> tuple[str, str]:
    parts = clean(full_name).split()
    first_name = " ".join(parts[:-1]) if len(parts) > 1 else clean(full_name)
    last_name = parts[-1] if len(parts) > 1 else ""
    return first_name, last_name


def academic_year_from_award_time(award_time: str, offset: int = 0) -> str:
    year, month = [int(x) for x in award_time.split("-")[:2]]
    start = year if month >= 7 else year - 1
    start += offset
    return f"{start}-{start + 1}"


def month_minus_one(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def new_york_today() -> dt.date:
    return dt.datetime.now(ZoneInfo(settings.timezone)).date()


def next_followup_date(award_time: str, today: dt.date | None = None) -> dt.date:
    today = today or new_york_today()
    _, month = [int(x) for x in award_time.split("-")[:2]]
    follow_year, follow_month = month_minus_one(today.year, month)
    candidate = dt.date(follow_year, follow_month, 1)
    if candidate < today:
        follow_year, follow_month = month_minus_one(today.year + 1, month)
        candidate = dt.date(follow_year, follow_month, 1)
    return candidate


def default_program_name(institution) -> str:
    department = clean(getattr(institution, "program_department", ""))
    return department or f"{institution.name} Scholarship Program"
