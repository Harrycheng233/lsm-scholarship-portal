from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from ..config import settings


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, salt_b64, digest_b64 = password_hash.split("$", 2)
        expected = hash_password(password, base64.b64decode(salt_b64)).split("$", 2)[2]
        return hmac.compare_digest(expected, digest_b64)
    except Exception:
        return False


def _sign(data: bytes) -> str:
    return base64.urlsafe_b64encode(hmac.new(settings.secret_key.encode(), data, hashlib.sha256).digest()).decode().rstrip("=")


def create_token(user_id: int, email: str, ttl_seconds: int = 60 * 60 * 12) -> str:
    payload = {"sub": user_id, "email": email, "exp": int(time.time()) + ttl_seconds}
    data = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"{data}.{_sign(data.encode())}"


def verify_token(token: str) -> dict | None:
    try:
        data, signature = token.split(".", 1)
        if not hmac.compare_digest(_sign(data.encode()), signature):
            return None
        payload = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
        if int(payload["exp"]) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
