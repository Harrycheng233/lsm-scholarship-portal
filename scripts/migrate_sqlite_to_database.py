#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database import Base  # noqa: E402
from backend.app.models.auth import User  # noqa: E402
from backend.app.models.core import AuditLog, Award, Document, Program, Scholar, School, VersionLog  # noqa: E402
from backend.app.services.rules import institution_key  # noqa: E402


TABLES = [
    ("schools", School),
    ("programs", Program),
    ("scholars", Scholar),
    ("awards", Award),
    ("documents", Document),
]


def sqlite_rows(path: Path, table: str) -> list[dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
    finally:
        conn.close()


def clear_target(session) -> None:
    for model in (AuditLog, Document, Award, Scholar, Program, School):
        session.execute(delete(model))
    session.commit()


def migrate(sqlite_path: Path, database_url: str, replace: bool) -> None:
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        if replace:
            clear_target(session)
        for table, model in TABLES:
            rows = sqlite_rows(sqlite_path, table)
            for row in rows:
                session.merge(model(**row))
            print(f"{table}: {len(rows)} rows")
        seed_version_log(session)
        session.commit()
        validate_counts(sqlite_path, session)


def seed_version_log(session) -> None:
    existing = session.query(VersionLog).filter_by(version="2.0-dev").first()
    if existing:
        return
    session.add(
        VersionLog(
            version="2.0-dev",
            title="FastAPI migration foundation",
            notes="Migrated from the local v1.9 SQLite portal into the v2 backend schema.",
            released_at="2026-05-21",
        )
    )


def validate_counts(sqlite_path: Path, session) -> None:
    print("Validation")
    for table, model in TABLES:
        source_count = len(sqlite_rows(sqlite_path, table))
        target_count = session.query(model).count()
        marker = "OK" if source_count == target_count else "MISMATCH"
        print(f"{marker}: {table}: source={source_count} target={target_count}")
    institution_names = [row["name"] for row in sqlite_rows(sqlite_path, "schools")]
    deduped = len({institution_key(name) for name in institution_names})
    print(f"normalized institution count: {deduped}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate LSM Portal SQLite data into a SQLAlchemy target database.")
    parser.add_argument("--sqlite", default=str(ROOT / "lsm_portal.db"), help="Path to source SQLite database.")
    parser.add_argument("--database-url", required=True, help="Target SQLAlchemy database URL, for example PostgreSQL on Render.")
    parser.add_argument("--replace", action="store_true", help="Delete target business data before importing.")
    args = parser.parse_args()
    migrate(Path(args.sqlite), args.database_url, args.replace)


if __name__ == "__main__":
    main()
