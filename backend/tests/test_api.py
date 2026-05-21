from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "lsm_api_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from fastapi.testclient import TestClient

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models.auth import User
from backend.app.services.security import hash_password


def create_user(email: str, role: str) -> None:
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, password_hash="", full_name=email, role=role, is_active=True)
            db.add(user)
        user.password_hash = hash_password("password")
        user.role = role
        user.is_active = True
        db.commit()


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200
    return response.json()["token"]


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_export_records_audit_event():
    with TestClient(app) as client:
        create_user("exporter@example.org", "admin")
        token = login(client, "exporter@example.org")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/export.xlsx", headers=headers)
        audit = client.get("/api/audit-log", headers=headers)

    assert response.status_code == 200
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "export"


def test_viewer_can_read_and_export_but_cannot_mutate():
    with TestClient(app) as client:
        create_user("viewer@example.org", "viewer")
        token = login(client, "viewer@example.org")
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/api/bootstrap", headers=headers).status_code == 200
        assert client.post("/api/institutions", headers=headers, json={}).status_code == 403
        assert client.get("/api/export.xlsx", headers=headers).status_code == 200
        assert client.get("/api/audit-log", headers=headers).status_code == 403


def test_admin_can_read_audit_log():
    with TestClient(app) as client:
        create_user("admin@example.org", "admin")
        token = login(client, "admin@example.org")
        response = client.get("/api/audit-log", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
