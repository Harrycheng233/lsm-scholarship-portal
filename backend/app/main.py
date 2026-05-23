from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models.auth import User
from .models.core import Award, Program, Scholar, School, VersionLog
from .services import message_board
from .services import portal
from .services.audit import audit_log_rows, record_audit
from .services.exporter import build_backup_workbook
from .services.security import create_token, hash_password, verify_password, verify_token


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def seed_admin() -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.email == settings.admin_email))
        if exists:
            return
        db.add(
            User(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                full_name="Administrator",
                role="admin",
                is_active=True,
            )
        )
        db.commit()


def seed_version_logs() -> None:
    entries = [
        {
            "version": "2.0-dev",
            "title": "FastAPI migration foundation",
            "notes": "Adds the production-oriented backend foundation, compatible bootstrap API, authentication groundwork, and dashboard Excel backup export.",
            "released_at": "2026-05-21",
        },
        {
            "version": "1.9",
            "title": "Local scholarship portal baseline",
            "notes": "Local SQLite portal for partner institutions, scholars, awards, dashboard statistics, and scholarship issue scheduling.",
            "released_at": "2026-05-18",
        },
    ]
    with SessionLocal() as db:
        for entry in entries:
            exists = db.scalar(select(VersionLog).where(VersionLog.version == entry["version"]))
            if not exists:
                db.add(VersionLog(**entry))
        db.commit()


def startup() -> None:
    if settings.auto_create_tables:
        create_schema()
    seed_admin()
    seed_version_logs()


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(select(1))
    return {"ok": True, "service": settings.app_name}


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else request.cookies.get("lsm_token")
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    return user if user and user.is_active else None


def require_user(user: User | None = Depends(current_user)) -> User:
    # Compatibility mode: if no users exist yet, allow access so existing local workflows keep working.
    with SessionLocal() as db:
        user_count = db.query(User).count()
    if user_count == 0:
        return User(id=0, email="local", password_hash="", full_name="Local User", role="admin", is_active=True)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def user_summary(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "is_active": user.is_active}


def require_roles(*roles: str):
    def checker(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return user

    return checker


require_editor = require_roles("admin", "editor")
require_exporter = require_roles("admin", "editor", "viewer")
require_admin = require_roles("admin")


@app.post("/api/auth/login")
def login(payload: dict, response: Response, db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_token(user.id, user.email)
    response.set_cookie("lsm_token", token, httponly=True, samesite="lax", secure=settings.cookie_secure)
    record_audit(db, user.email, "login", "User", user.id, f"{user.email} signed in.", commit=True)
    return {"ok": True, "token": token, "user": user_summary(user)}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("lsm_token")
    return {"ok": True}


def user_rows(db: Session) -> list[dict]:
    users = db.scalars(select(User).order_by(User.email)).all()
    return [user_summary(user) for user in users]


@app.get("/api/users")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    return user_rows(db)


@app.post("/api/users")
def create_user(payload: dict, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "viewer")).strip()
    full_name = str(payload.get("full_name", "")).strip()
    first_real_user = db.query(User).count() == 0
    if first_real_user:
        role = "admin"
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required.")
    if role not in {"admin", "editor", "viewer"}:
        raise HTTPException(status_code=400, detail="Role must be admin, editor, or viewer.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="A user with this email already exists.")
    user = User(email=email, password_hash=hash_password(password), full_name=full_name, role=role, is_active=True)
    db.add(user)
    db.commit()
    record_audit(db, admin.email, "create", "User", user.id, f"Created user {email}.", commit=True)
    return {"ok": True, "id": user.id}


@app.put("/api/users/{user_id}")
def update_user(user_id: int, payload: dict, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    role = str(payload.get("role", user.role)).strip()
    if role not in {"admin", "editor", "viewer"}:
        raise HTTPException(status_code=400, detail="Role must be admin, editor, or viewer.")
    user.full_name = str(payload.get("full_name", user.full_name or "")).strip()
    user.role = role
    user.is_active = bool(payload.get("is_active", user.is_active))
    password = str(payload.get("password", ""))
    if password:
        user.password_hash = hash_password(password)
    db.commit()
    record_audit(db, admin.email, "update", "User", user.id, f"Updated user {user.email}.", commit=True)
    return {"ok": True, "id": user.id}


@app.delete("/api/users/{user_id}")
def deactivate_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = False
    db.commit()
    record_audit(db, admin.email, "deactivate", "User", user.id, f"Deactivated user {user.email}.", commit=True)
    return {"ok": True, "id": user.id}


@app.get("/api/me")
def me(user: User = Depends(require_user)) -> dict:
    return {"user": user_summary(user)}


@app.get("/api/bootstrap")
def api_bootstrap(user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    payload = portal.bootstrap(db)
    payload["currentUser"] = user_summary(user)
    payload["users"] = user_rows(db) if user.role == "admin" else []
    return payload


@app.get("/api/version-log")
def version_log(_: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return portal.version_log_rows(db)


@app.post("/api/version-log")
def create_version_log(payload: dict, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        result = portal.create_version_log(db, payload)
        record_audit(db, admin.email, "create", "VersionLog", result["id"], f"Created version log {payload.get('version', '')}.", commit=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/audit-log")
def audit_log(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    return audit_log_rows(db)


@app.get("/api/message-board/threads")
def list_message_threads(_: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return message_board.list_threads(db)


@app.post("/api/message-board/threads")
def create_message_thread(payload: dict, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    try:
        result = message_board.create_thread(db, payload, user.id)
        record_audit(db, user.email, "create", "MessageThread", result["id"], f"Created message thread {payload.get('subject', '')}.", commit=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/message-board/threads/{thread_id}")
def get_message_thread(thread_id: int, _: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        return message_board.get_thread_detail(db, thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/message-board/threads/{thread_id}")
def update_message_thread(thread_id: int, payload: dict, user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        result = message_board.update_thread(db, thread_id, payload)
        record_audit(db, user.email, "update", "MessageThread", thread_id, f"Updated message thread {payload.get('subject', '')}.", commit=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/message-board/threads/{thread_id}")
def delete_message_thread(thread_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        result = message_board.delete_thread(db, thread_id)
        record_audit(db, user.email, "delete", "MessageThread", thread_id, "Deleted message thread and replies.", commit=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/message-board/threads/{thread_id}/replies")
def create_message_reply(thread_id: int, payload: dict, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    try:
        result = message_board.create_reply(db, thread_id, payload, user.id)
        record_audit(db, user.email, "create", "MessageReply", result["id"], f"Replied to message thread #{thread_id}.", commit=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/message-board/replies/{reply_id}")
def delete_message_reply(reply_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        result = message_board.delete_reply(db, reply_id)
        record_audit(db, user.email, "delete", "MessageReply", reply_id, "Deleted message reply.", commit=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/institutions")
@app.post("/api/schools")
def create_institution(payload: dict, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    try:
        result = portal.create_institution(db, payload)
        record_audit(db, user.email, "create", "Institution", result["id"], f"Created institution {payload.get('name', '')}.", commit=True)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/institutions/{institution_id}")
def update_institution(institution_id: int, payload: dict, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    try:
        result = portal.update_institution(db, institution_id, payload)
        record_audit(db, user.email, "update", "Institution", institution_id, f"Updated institution {payload.get('name', '')}.", commit=True)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/institutions/{institution_id}")
def delete_institution(institution_id: int, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    result = portal.delete_institution(db, institution_id)
    record_audit(db, user.email, "delete", "Institution", institution_id, "Deleted institution and related records.", commit=True)
    return result


@app.post("/api/scholars")
def create_scholar(payload: dict, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    try:
        result = portal.create_scholar(db, payload)
        record_audit(db, user.email, "create", "Scholar", result["id"], f"Created scholar {payload.get('full_name', '')}.", commit=True)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/scholars/{scholar_id}")
def update_scholar(scholar_id: int, payload: dict, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    try:
        result = portal.update_scholar(db, scholar_id, payload)
        record_audit(db, user.email, "update", "Scholar", scholar_id, f"Updated scholar {payload.get('full_name', '')}.", commit=True)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/scholars/{scholar_id}")
def delete_scholar(scholar_id: int, user: User = Depends(require_editor), db: Session = Depends(get_db)) -> dict:
    result = portal.delete_scholar(db, scholar_id)
    record_audit(db, user.email, "delete", "Scholar", scholar_id, "Deleted scholar and related records.", commit=True)
    return result


@app.get("/api/export.xlsx")
def export_backup(user: User = Depends(require_exporter), db: Session = Depends(get_db)) -> Response:
    content = build_backup_workbook(db)
    record_audit(db, user.email, "export", "Workbook", None, "Exported Excel backup.", commit=True)
    headers = {"Content-Disposition": 'attachment; filename="lsm-scholarship-backup.xlsx"'}
    return Response(
        content,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def static_file(path: str) -> FileResponse:
    target = (settings.static_dir / path).resolve()
    if not str(target).startswith(str(settings.static_dir.resolve())) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target, media_type=mimetypes.guess_type(target.name)[0])


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return static_file("index.html")


@app.get("/{path:path}")
def static_assets(path: str) -> FileResponse:
    return static_file(path or "index.html")
