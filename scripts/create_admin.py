#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.models.auth import User  # noqa: E402
from backend.app.services.security import hash_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an LSM Portal admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrator")
    parser.add_argument("--password", default="")
    args = parser.parse_args()
    password = args.password or getpass.getpass("Password: ")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=args.email.strip().lower()).first()
        if not user:
            user = User(email=args.email.strip().lower(), password_hash="", full_name=args.name, role="admin", is_active=True)
            db.add(user)
        user.password_hash = hash_password(password)
        user.full_name = args.name
        user.role = "admin"
        user.is_active = True
        db.commit()
    print(f"Admin user ready: {args.email.strip().lower()}")


if __name__ == "__main__":
    main()
