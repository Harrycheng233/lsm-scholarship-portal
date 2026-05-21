from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    app_name = "LSM Scholarship Portal"
    timezone = os.environ.get("APP_TIMEZONE", "America/New_York")
    database_url = os.environ.get("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'lsm_portal.db'}")
    secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
    cookie_secure = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    auto_create_tables = os.environ.get("AUTO_CREATE_TABLES", "true").lower() == "true"
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    static_dir = PROJECT_ROOT / "static"


settings = Settings()
