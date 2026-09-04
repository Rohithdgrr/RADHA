# Module 1 — Database Schema & Migrations (M, ~1d)

> **Goal:** Materialize `data-model.md:25-326` in Postgres with async SQLAlchemy + Alembic. Exit: `alembic upgrade head` creates 3 tables + 7 indexes, seed loads, tests pass without bridge.

## File Manifest

```
backend/
├── app/
│   ├── db/base.py (existing — keep, add Base import helper)
│   └── models/
│       ├── __init__.py  (re-export User, CouncilSession, ModelResponse, Base)
│       ├── user.py
│       ├── council_session.py
│       └── model_response.py
├── app/schemas/
│   ├── __init__.py
│   ├── user.py        (UserCreate/UserRead from data-model §2)
│   ├── council.py     (CouncilSessionCreate/Read etc from §3)
│   └── model_response.py (from §4)
├── migrations/
│   ├── env.py         (async engine, target_metadata=Base.metadata, offline/online)
│   ├── script.py.mako
│   └── versions/001_init_users_sessions_responses.py
├── seed.py            # creates 1 user + 1 anon council session with 3 responses, for dev
└── tests/test_db.py   # async SQLite in-memory (or mocked asyncpg) — tests below
```

## Adjustment per approval (2026-09-04): Use sqlite3 (aiosqlite)

Per user request: Phase 2 dev DB is **sqlite3 via `sqlite+aiosqlite`** (file `./aicouncil.db`) instead of Postgres. `DATABASE_URL` defaults to `sqlite+aiosqlite:///./aicouncil.db` in `app/config.py` and `alembic.ini`. PG URL remains supported via `DATABASE_URL=postgresql+asyncpg://...` env override for prod. JSONB → `JSON` (SQLite stores as TEXT, SQLAlchemy `JSON` type handles both). UUID stored as `String(36)`/`UUID` compat — Python `uuid4` str.

Deviation logged to `design-notes.md`.

## Model Details (from data-model.md, with sqlite compat)

- **User** `users`: UUID PK, email VARCHAR(320) unique lower, password_hash, display_name(100), created_at TIMESTAMPTZ server_default now(), last_login, lmarena_token TEXT nullable, is_active BOOLEAN default true. Indexes `ux_users_email lower(email)`, `ix_users_created`.
- **CouncilSession** `council_sessions`: UUID PK, user_id FK SET NULL nullable index, user_query TEXT NOT NULL, selected_models JSONB NOT NULL, chairman_model VARCHAR(50) NOT NULL, mode/depth VARCHAR(20) + show_reasoning BOOLEAN + synthesis/agreements/divergences/unique_insights/deliberation_log JSONB + total_latency Float + status VARCHAR(20) default running + timestamps. Indexes 4 + GIN deferred (design-notes).
- **ModelResponse** `model_responses`: UUID PK, session_id FK CASCADE index, model_name VARCHAR(50) index, reasoning TEXT, final_answer TEXT NOT NULL, confidence 0-1 Float, latency Float NOT NULL, token_count, status, error_message, critique, critique_score 0-10, raw_payload JSONB, created_at. Indexes + `ux_responses_session_model` unique(session_id, model_name).
- **Relationships:** `User.sessions ↔ CouncilSession.user`, `CouncilSession.responses ↔ ModelResponse.session` (cascade delete sessions→responses, SET NULL for users→sessions).

## Migrations (sqlite-aware)

- `migrations/env.py` async with `sqlite+aiosqlite` by default; `sqlalchemy.url` = `sqlite+aiosqlite:///./aicouncil.db`, sync url = `sqlite:///./aicouncil.db` for offline.
- `001` creates tables, FKs, unique indexes; SQLite `CHECK` for enums kept simple or omitted (Pydantic primary guard); `JSON` type used instead of `JSONB`.
- Downgrade drops tables reverse order.

## Seed (dev optional)

`seed.py` uses `AsyncSessionLocal`: creates `user@example.com` / `password123`, anon session `What is quantum computing?` 3 models + synthesis. Run `python seed.py` after `alembic upgrade head`.

## Tests (sqlite, no PG required)

- `test_create_user_session_response_flow` — create via ORM, query with selectinload, assert cascade; uses `sqlite+aiosqlite` memory.
- `test_unique_email_lower` — duplicate case-insensitive → IntegrityError.
- `test_unique_session_model` — duplicate model per session violates unique.
- `test_anon_session` — `user_id NULL` allowed.
- `test_alembic_upgrade_downgrade` — `sqlite:///./test.db` upgrade head → downgrade → upgrade via `Alembic Config`.
- All tests run with `sqlite+aiosqlite:///:memory:` or file `./test.db` — no PG required.

## Approval Request

Approve this manifest? Next: write `app/models/*.py`, `app/schemas/*.py`, `migrations/env.py` + `001`, `seed.py`, `tests/test_db.py`.
