from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.core import MessageReply, MessageThread
from .rules import clean


SUBJECT_LIMIT = 200
BODY_LIMIT = 5000


def now_text() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def author_name(author) -> str:
    if not author:
        return "Unknown user"
    return clean(author.full_name) or author.email


def validate_text(value: str | None, field: str, limit: int) -> str:
    text = clean(value)
    if not text:
        raise ValueError(f"{field} is required.")
    if len(text) > limit:
        raise ValueError(f"{field} must be {limit} characters or fewer.")
    return text


def reply_row(reply: MessageReply) -> dict:
    return {
        "id": reply.id,
        "thread_id": reply.thread_id,
        "body": reply.body,
        "created_by_user_id": reply.created_by_user_id,
        "author_display_name": author_name(reply.author),
        "created_at": reply.created_at,
        "updated_at": reply.updated_at,
    }


def thread_row(thread: MessageThread, latest_activity_at: str | None = None, reply_count: int | None = None) -> dict:
    return {
        "id": thread.id,
        "subject": thread.subject,
        "body": thread.body,
        "created_by_user_id": thread.created_by_user_id,
        "author_display_name": author_name(thread.author),
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
        "latest_activity_at": latest_activity_at or thread.created_at,
        "reply_count": reply_count if reply_count is not None else len(thread.replies),
    }


def list_threads(db: Session) -> list[dict]:
    latest_reply = (
        select(
            MessageReply.thread_id.label("thread_id"),
            func.max(MessageReply.created_at).label("latest_reply_at"),
            func.count(MessageReply.id).label("reply_count"),
        )
        .group_by(MessageReply.thread_id)
        .subquery()
    )
    rows = db.execute(
        select(MessageThread, latest_reply.c.latest_reply_at, latest_reply.c.reply_count)
        .outerjoin(latest_reply, latest_reply.c.thread_id == MessageThread.id)
        .order_by(func.coalesce(latest_reply.c.latest_reply_at, MessageThread.created_at).desc(), MessageThread.id.desc())
    ).all()
    return [thread_row(thread, latest_reply_at, int(reply_count or 0)) for thread, latest_reply_at, reply_count in rows]


def get_thread_detail(db: Session, thread_id: int) -> dict:
    thread = db.get(MessageThread, thread_id)
    if not thread:
        raise ValueError("Message thread not found.")
    replies = db.scalars(select(MessageReply).where(MessageReply.thread_id == thread_id).order_by(MessageReply.created_at, MessageReply.id)).all()
    latest_activity_at = replies[-1].created_at if replies else thread.created_at
    data = thread_row(thread, latest_activity_at, len(replies))
    data["replies"] = [reply_row(reply) for reply in replies]
    return data


def create_thread(db: Session, payload: dict, user_id: int) -> dict:
    timestamp = now_text()
    thread = MessageThread(
        subject=validate_text(payload.get("subject"), "Subject", SUBJECT_LIMIT),
        body=validate_text(payload.get("body"), "Body", BODY_LIMIT),
        created_by_user_id=user_id,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(thread)
    db.commit()
    return {"ok": True, "id": thread.id}


def update_thread(db: Session, thread_id: int, payload: dict) -> dict:
    thread = db.get(MessageThread, thread_id)
    if not thread:
        raise ValueError("Message thread not found.")
    thread.subject = validate_text(payload.get("subject"), "Subject", SUBJECT_LIMIT)
    thread.body = validate_text(payload.get("body"), "Body", BODY_LIMIT)
    thread.updated_at = now_text()
    db.commit()
    return {"ok": True, "id": thread.id}


def delete_thread(db: Session, thread_id: int) -> dict:
    thread = db.get(MessageThread, thread_id)
    if not thread:
        raise ValueError("Message thread not found.")
    db.delete(thread)
    db.commit()
    return {"ok": True}


def create_reply(db: Session, thread_id: int, payload: dict, user_id: int) -> dict:
    if not db.get(MessageThread, thread_id):
        raise ValueError("Message thread not found.")
    timestamp = now_text()
    reply = MessageReply(
        thread_id=thread_id,
        body=validate_text(payload.get("body"), "Reply", BODY_LIMIT),
        created_by_user_id=user_id,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(reply)
    db.commit()
    return {"ok": True, "id": reply.id}


def delete_reply(db: Session, reply_id: int) -> dict:
    reply = db.get(MessageReply, reply_id)
    if not reply:
        raise ValueError("Message reply not found.")
    db.delete(reply)
    db.commit()
    return {"ok": True}
