from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models.auth import User
from backend.app.models.core import MessageReply, MessageThread
from backend.app.services.security import hash_password


def create_named_user(email: str, role: str, full_name: str) -> None:
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, password_hash="", full_name=full_name, role=role, is_active=True)
            db.add(user)
        user.password_hash = hash_password("password")
        user.full_name = full_name
        user.role = role
        user.is_active = True
        db.commit()


def login(client: TestClient, email: str) -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def post_thread(client: TestClient, headers: dict, subject: str = "Planning", body: str = "First line\nSecond line") -> int:
    response = client.post("/api/message-board/threads", headers=headers, json={"subject": subject, "body": body})
    assert response.status_code == 200
    return response.json()["id"]


def test_message_board_permissions_and_display_names():
    with TestClient(app) as client:
        create_named_user("message-admin@example.org", "admin", "Admin Name")
        create_named_user("message-editor@example.org", "editor", "Editor Name")
        create_named_user("message-viewer@example.org", "viewer", "Viewer Name")
        admin = login(client, "message-admin@example.org")
        editor = login(client, "message-editor@example.org")
        viewer = login(client, "message-viewer@example.org")

        admin_thread_id = post_thread(client, admin, "Admin thread")
        editor_thread_id = post_thread(client, editor, "Editor thread")

        assert client.post("/api/message-board/threads", headers=viewer, json={"subject": "No", "body": "No"}).status_code == 403
        assert client.post(f"/api/message-board/threads/{admin_thread_id}/replies", headers=admin, json={"body": "Admin reply"}).status_code == 200
        editor_reply = client.post(f"/api/message-board/threads/{admin_thread_id}/replies", headers=editor, json={"body": "Editor reply"})
        assert editor_reply.status_code == 200
        assert client.post(f"/api/message-board/threads/{admin_thread_id}/replies", headers=viewer, json={"body": "Viewer reply"}).status_code == 403

        detail = client.get(f"/api/message-board/threads/{admin_thread_id}", headers=viewer)
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["author_display_name"] == "Admin Name"
        assert [reply["author_display_name"] for reply in payload["replies"]] == ["Admin Name", "Editor Name"]
        assert payload["body"] == "First line\nSecond line"

        assert client.put(f"/api/message-board/threads/{editor_thread_id}", headers=editor, json={"subject": "Edit", "body": "Edit"}).status_code == 403
        assert client.put(f"/api/message-board/threads/{editor_thread_id}", headers=viewer, json={"subject": "Edit", "body": "Edit"}).status_code == 403
        assert client.put(f"/api/message-board/threads/{editor_thread_id}", headers=admin, json={"subject": "Edited", "body": "Updated"}).status_code == 200

        assert client.delete(f"/api/message-board/replies/{editor_reply.json()['id']}", headers=editor).status_code == 403
        assert client.delete(f"/api/message-board/replies/{editor_reply.json()['id']}", headers=viewer).status_code == 403
        assert client.delete(f"/api/message-board/replies/{editor_reply.json()['id']}", headers=admin).status_code == 200

        assert client.delete(f"/api/message-board/threads/{editor_thread_id}", headers=editor).status_code == 403
        assert client.delete(f"/api/message-board/threads/{editor_thread_id}", headers=viewer).status_code == 403
        assert client.delete(f"/api/message-board/threads/{editor_thread_id}", headers=admin).status_code == 200


def test_message_board_validation_ordering_and_thread_delete_cascades_replies():
    with TestClient(app) as client:
        create_named_user("message-order-admin@example.org", "admin", "Ordering Admin")
        admin = login(client, "message-order-admin@example.org")

        assert client.post("/api/message-board/threads", headers=admin, json={"subject": "   ", "body": "Body"}).status_code == 400
        assert client.post("/api/message-board/threads", headers=admin, json={"subject": "Subject", "body": "   "}).status_code == 400

        older_thread_id = post_thread(client, admin, "Older")
        newer_thread_id = post_thread(client, admin, "Newer")
        assert client.post(f"/api/message-board/threads/{older_thread_id}/replies", headers=admin, json={"body": "Latest activity"}).status_code == 200
        with SessionLocal() as db:
            reply = db.query(MessageReply).filter_by(thread_id=older_thread_id).one()
            reply.created_at = "2999-01-01T00:00:00+00:00"
            reply.updated_at = reply.created_at
            db.commit()

        threads = client.get("/api/message-board/threads", headers=admin).json()
        ordered_ids = [row["id"] for row in threads if row["id"] in {older_thread_id, newer_thread_id}]
        assert ordered_ids == [older_thread_id, newer_thread_id]

        assert client.delete(f"/api/message-board/threads/{older_thread_id}", headers=admin).status_code == 200
        with SessionLocal() as db:
            assert db.get(MessageThread, older_thread_id) is None
            assert db.query(MessageReply).filter_by(thread_id=older_thread_id).count() == 0
