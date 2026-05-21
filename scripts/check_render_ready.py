#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def require_text(path: Path, snippets: list[str]) -> list[str]:
    text = path.read_text()
    return [snippet for snippet in snippets if snippet not in text]


def main() -> None:
    problems: list[str] = []
    warnings: list[str] = []

    problems += [f"render.yaml missing `{item}`" for item in require_text(ROOT / "render.yaml", ["alembic upgrade head", "DATABASE_URL", "AUTO_CREATE_TABLES", "COOKIE_SECURE"])]
    problems += [f"requirements.txt missing `{item}`" for item in require_text(ROOT / "requirements.txt", ["fastapi", "uvicorn", "sqlalchemy", "alembic", "psycopg[binary]"])]
    problems += [f"alembic.ini missing `{item}`" for item in require_text(ROOT / "alembic.ini", ["script_location = alembic"])]

    if not (ROOT / "alembic" / "env.py").exists():
        problems.append("alembic/env.py is missing")
    if not list((ROOT / "alembic" / "versions").glob("*.py")):
        problems.append("No Alembic migration files found")
    if not importlib.util.find_spec("alembic"):
        warnings.append("Alembic is not installed in this local Python environment; Render will install it from requirements.txt.")

    from backend.app.main import app

    if app.title != "LSM Scholarship Portal":
        problems.append("FastAPI app did not import with the expected title")

    if problems:
        print("Render readiness: FAILED")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)

    print("Render readiness: OK")
    for warning in warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
