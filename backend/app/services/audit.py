from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.core import AuditLog


def audit_now() -> str:
    return dt.datetime.now(ZoneInfo(settings.timezone)).isoformat(timespec="seconds")


def record_audit(
    db: Session,
    actor_email: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
    summary: str,
    commit: bool = False,
) -> None:
    db.add(
        AuditLog(
            actor_email=actor_email or "system",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            created_at=audit_now(),
        )
    )
    if commit:
        db.commit()


def audit_log_rows(db: Session, limit: int = 100) -> list[dict]:
    logs = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": log.id,
            "actor_email": log.actor_email,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "summary": log.summary,
            "created_at": log.created_at,
        }
        for log in logs
    ]
