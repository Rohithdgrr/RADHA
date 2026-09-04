# Module 0 — Project Scaffolding & Tooling (S, ~0.3d)

> **Prereq for all modules:** Repo boots via `quickstart.md` before business logic. Exit: `docker-compose up --build` starts 4 services, `curl /health` placeholder ok, tests smoke.

## File Manifest (to create)

```
council/
├── docker-compose.yml              # postgres:15, redis (optional), backend:8000, frontend:3000, lmarenabridge:8001 stub
├── .env.example                    # from quickstart.md:15 (LMARENA_TOKEN placeholder, DATABASE_URL, SECRET_KEY 32+, etc.)
├── .gitignore                      # .env, __pycache__, node_modules, .next, backend/venv
├── Makefile                        # up/down/logs/test
├── backend/
│   ├── Dockerfile                  # python:3.11-slim + uvicorn
│   ├── requirements.txt            # fastapi 0.115, uvicorn, httpx 0.27, sqlalchemy 2 async+asyncpg, alembic 1.13, pydantic 2 + pydantic-settings, python-dotenv, structlog, slowapi, pybreaker, python-jose, passlib[bcrypt], pytest+pytest-asyncio
│   ├── alembic.ini                 # async URL placeholder
│   ├── pyproject.toml              # tool black/ruff/pytest
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI stub: GET /health 501 placeholder, CORS FRONTEND_ORIGIN, lifespan
│   │   ├── config.py               # Settings via pydantic-settings (mirrors docs/ENV.md)
│   │   └── db/base.py              # declarative Base, async engine factory (no models yet)
│   └── tests/
│       └── test_health_smoke.py    # placeholder
├── frontend/
│   ├── Dockerfile                  # node:18-alpine
│   ├── package.json                # next 14, react 18, typescript 5, tailwind 3, zustand 4, rhf 7, ai 3 (vercel)
│   ├── tsconfig.json               # strict
│   ├── tailwind.config.ts          # gray-900/#111827, cyan-500/#00BFFF, darkMode class
│   ├── next.config.mjs
│   ├── postcss.config.js
│   ├── app/{layout.tsx,page.tsx,globals.css} # dark theme shell, hero placeholder
│   └── lib/api.ts                  # NEXT_PUBLIC_API_URL stub
└── contracts/ (existing) + research.md etc unchanged
```

## Key Configs (quickstart-aligned)

- `docker-compose.yml` aligns ports: `postgres:5432`, `lmarenabridge:8001` (internal `http://lmarenabridge:8001`, local `http://localhost:8001`), `backend:8000` (`LMARENA_BRIDGE_URL=http://lmarenabridge:8001`), `frontend:3000`.
- `LMARENA_BRIDGE_URL` vs `8001` canonical per design-notes 2026-09-04.
- CORS `FRONTEND_ORIGIN=http://localhost:3000` only.
- `SECRET_KEY` 32+ min enforced in `app/config.py` (Field min_length 32).
- `frontend/.env.local.example` = `NEXT_PUBLIC_API_URL=http://localhost:8000`.

## Steps (sequential, testable)

1. Create `.gitignore`, `.env.example`, `Makefile`, `backend/app/db/base.py`, `app/config.py`, `app/main.py` stub (`/health` → 501 until M2 overwrites).
2. Scaffold `frontend` via config files (no `npx create` rerun — manual files to stay deterministic).
3. Write `docker-compose.yml` + both Dockerfiles.
4. Verify: `docker compose config` (no YAML errors), `cd backend && python -m compileall app`, `cd frontend && npm run build` smoke (after npm install), `pytest --collect-only`.

## Tests for Exit

- `docker compose config` passes
- `backend`: `pytest tests/test_health_smoke.py` (imports `app.main`)
- `frontend`: `npm run build` (or `npx tsc --noEmit` if no node)
- No secrets committed (check `.env` not tracked)

## Risks → Mitigations

- Port drift → compose uses `8001` for bridge consistently.
- Node not installed → smoke via `tsc` check only, not full build.
- Already have `docs/` → keep, don’t overwrite.

## Approval Request

Approve this manifest? Next: write files, verify, then Module 1 DB.
