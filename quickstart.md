# Quickstart — AI Council (Local Dev, 5 minutes)

> **Goal:** Get a minimal council running locally — query 3 models, see SSE stream + synthesis, no auth.
> **Prereqs:** Docker & Compose, Git, LMArena.ai account (free). Alternative manual without Docker at bottom.
> **Refs:** `docs/SETUP.md` (full), `docs/ENV.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`

## 1. Clone & Env

```bash
git clone https://github.com/yourname/ai-council.git
cd ai-council
cp .env.example .env
```

**.env.example** (commit this):
```env
# Bridge
LMARENA_TOKEN=replace_with_arena-auth-prod-v1
LMARENA_BRIDGE_URL=http://lmarenabridge:8001
# DB
DATABASE_URL=postgresql://admin:password@postgres:5432/aicouncil
# Backend
BACKEND_PORT=8000
FRONTEND_PORT=3000
FRONTEND_ORIGIN=http://localhost:3000
SECRET_KEY=change_me_32_chars_min________________________________
ADMIN_PASSWORD=change_me
# Optional
REDIS_URL=redis://redis:6379/0
MAX_MODELS_PER_QUERY=8
REQUEST_TIMEOUT=120
LOG_LEVEL=INFO
```

**Get token** (`docs/SETUP.md:Step 2`): Chrome → arena.ai login → F12 → Application → Cookies → `https://arena.ai` → `arena-auth-prod-v1` → copy base64 → paste into `.env` `LMARENA_TOKEN`. TTL unknown — if 401, repeat.

## 2. Run (Docker Compose — canonical Phase 1)

```bash
docker-compose up -d --build
docker-compose logs -f   # wait ~30s for healthy
```

Services:
- `postgres:5432` — `aicouncil` DB
- `lmarenabridge:8001` — OpenAI-proxy
- `backend:8000` — FastAPI `GET /health` `GET /models` `POST /council/query`
- `frontend:3000` — Next.js

Check:
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0","bridge":"connected","db":"connected"}

curl http://localhost:8000/models
# {"models":[{"id":"claude","available":true}, ...]}

# SSE test (Phase 1 contract)
curl -N -X POST http://localhost:8000/council/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is 2+2?","models":["claude","chatgpt"],"mode":"consensus","chairman":"claude"}'
# event: model_start
# event: model_done ...
# event: synthesis_start
# event: done
```

Open `http://localhost:3000` → hero search → pick 2-3 models → type query → Enter → see model cards streaming + unified answer top. History sidebar empty until you run a query (anon session stored).

## 3. Migrations (if backend not auto-migrated)

```bash
docker-compose exec backend alembic upgrade head
# or locally: cd backend && alembic upgrade head
```

Verify DB:
```bash
docker-compose exec postgres psql -U admin -d aicouncil -c "\dt"
# users, council_sessions, model_responses
```

## 4. Manual (no Docker)

**Backend:**
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # http://localhost:3000, set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
```

**Bridge:** Follow `lmarenabridge/lmarenabridge` README to run on `http://localhost:8001` with same `LMARENA_TOKEN`.

**DB:** Local PostgreSQL 15+ `createdb aicouncil`, set `DATABASE_URL`, run `alembic upgrade head`.

## 5. Next Steps

- Read `contracts/sse-events.md` to wire frontend `EventSource` vs `Vercel AI SDK`.
- Try shareable URL: after `done` event, `GET /council/session/{session_id}` returns full JSON — open `/council/{id}` to replay.
- Run tests: `cd backend && pytest` (mocks bridge), `cd frontend && npm test`.
- For auth: `POST /auth/register` then `Authorization: Bearer <jwt>` on `/council/query` to tie history to user.

## 6. Troubleshooting (subset of docs/SETUP.md)

| Symptom | Fix |
|---------|-----|
| `Connection refused` to bridge | `LMARENA_BRIDGE_URL` wrong — compose = `http://lmarenabridge:8001`, local = `http://localhost:8001` |
| `401 Unauthorized` | Token expired → re-copy `arena-auth-prod-v1`, `docker-compose restart lmarenabridge backend` |
| `PG connection failed` | Wait 10s after `up`, check `DATABASE_URL` password |
| Slow Gemini | Disable it in model selector (known slower) |
| `429 Rate limit` | 100/hr anon, 500/hr auth — wait 60s, check `Retry-After` |

## 7. What’s Deferrred (Phase 2)

Debate/Specialist/Weighted modes return `501`, file uploads 501, OAuth Google/GitHub deferred (email/password only), Redis cache optional.

---

**Time to first streamed answer: ~2–3 minutes after `docker-compose up`.**
