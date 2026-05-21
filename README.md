# LSM Scholarship Portal

A scholarship management portal for partner schools, programs, scholars, and awards.

## Start v2

From this folder:

```bash
uvicorn backend.app.main:app --reload --port 8788
```

Then open:

```text
http://127.0.0.1:8788
```

The legacy v1.9 local server is still available in `server.py` while the FastAPI migration is underway.

## Data

- Records are stored in `lsm_portal.db`.
- Daily workflow pages are `Dashboard`, `Institutions`, `Scholars`, `Statistics`, `Users`, and `Audit Log`.
- Version Log opens from the lower-left dot, matching the v1.9 UI.
- Scholars can be entered as one-time or multi-year recipients. Multi-year entries automatically create the corresponding scholarship issued records.
- Dashboard includes an Excel backup export with `Schools` and `Scholars` tabs.

## Production Notes

- Set `DATABASE_URL` to PostgreSQL for deployment.
- Set `SECRET_KEY` in production.
- Optional first admin user can be seeded with `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
- Render deployment scaffolding is provided in `render.yaml`.
- Render runs `alembic upgrade head` before starting the web service.
- File upload has been removed from the product workflow; legacy document metadata remains only for safe migration compatibility.

## Admin and Migration Utilities

Create or update an admin user:

```bash
python3 scripts/create_admin.py --email admin@example.org
```

User roles:

- `admin`: full access, including audit log.
- `editor`: create, update, delete, and export records.
- `viewer`: read-only access to portal data.

Migrate an existing SQLite database into another SQLAlchemy database target:

```bash
python3 scripts/migrate_sqlite_to_database.py --sqlite lsm_portal.db --database-url "$DATABASE_URL" --replace
```

Check deployment readiness locally:

```bash
python3 scripts/check_render_ready.py
```
