# Backend (FastAPI)

## Local development

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # adjust for your local Postgres, etc.

uvicorn app.main:app --reload
```

```bash
curl localhost:8000/healthz
```

## Tests

```bash
pytest
```

Tests run against a real PostgreSQL database (`TEST_DATABASE_URL`, default
`postgresql+psycopg://sandbox:sandbox@localhost:5432/sandbox`) rather than
SQLite, because the credit-spend concurrency test relies on genuine
`SELECT ... FOR UPDATE` row locking.

## Creating the first admin user

There's no self-registration (spec Section 21/48). Seed the first account
via the CLI, run once inside the backend container/pod (or locally against
your dev database):

```bash
python -m app.cli create-admin --username root --password <password>
```

## Migrations

```bash
alembic upgrade head              # apply
alembic revision --autogenerate -m "description"   # generate a new one after model changes
```

## Layout

```text
app/
├── main.py         # FastAPI app, routers, health/metrics endpoints
├── config.py        # pydantic-settings, all env-driven configuration
├── database.py       # SQLAlchemy engine/session
├── models/          # SQLAlchemy models (Phase 2)
├── schemas/          # Pydantic request/response schemas (Phase 2+)
├── api/             # FastAPI routers: auth, instances, credits, admin (Phase 2+)
├── services/          # Business logic: credit ledger, instance lifecycle, cleanup (Phase 3+)
├── kubernetes/        # Kubernetes client wrapper (Phase 4+)
├── auth/             # Password hashing, API keys, WebSocket tickets (Phase 2/5+)
└── terminal/          # WebSocket terminal <-> Kubernetes exec bridge (Phase 5)
```

No business logic lives directly in `main.py` beyond wiring routers —
`create_sandbox_instance(...)`-style plain functions in `services/`, not a
hierarchy of abstract providers (see spec Section 43).
