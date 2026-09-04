# Implementation Roadmap — Phase 2: Core Development (AI Council)

> **Source blueprint:** `data-model.md`, `contracts/openapi.yaml`, `contracts/council-query.json`, `contracts/sse-events.md`, `quickstart.md`, `research.md`, `docs/BACKEND.md|DATABASE.md|UIUX.md|TECH-STACK.md`
> **Method:** Sequential, testable modules. For each module: `Plan (this doc § per-module plan) → Approval → Code → Tests pass → Design-notes entry if deviates`.
> **Stack pinned:** Next.js 14/TS 5/Tailwind 3/Zustand 4/Vercel AI SDK 3, FastAPI 0.115/Python 3.11/SQLAlchemy 2 async/Alembic 1.13/Pydantic 2/httpx 0.27/structlog/slowapi/pybreaker, PG 15+ (asyncpg), Docker Compose canonical (quickstart).
> **Date:** 2026-09-04 | **Status:** Awaiting approval before coding

## How Modules Are Ordered

Dependency chain: **DB → Backend core (health→models→query) → LMArenaBridge client → Orchestrator+Synthesis → Auth → Frontend (search→results→history→report) → Integration/E2E**. Each module is independently testable with mocks; no module assumes a later one. `design-notes.md` logs any deviation from `data-model.md`/`contracts/`.

### Effort Scale
- **S** = <0.5 day (small), **M** = 0.5–1.5 days, **L** = 1.5–3 days, **XL** = 3–5 days
- Estimates for **one engineer** familiar with stack; assumes `quickstart.md` env works, LMArena token available. Buffer included for tests/docs.
- Total **~14–19 engineer-days** if done sequentially (real calendar ~3–4 weeks with review).

---

## Module 0 — Project Scaffolding & Tooling (Prerequisite, S)

**Goal:** Repo boots via `quickstart.md` before any business logic.

| Item | Detail |
|------|--------|
| **Tasks** | Create `backend/` (`pyproject.toml`/`requirements.txt`, `app/main.py`, `app/config.py`, `app/db.py`, `.env.example`), `frontend/` (`npx create-next-app@14`, Tailwind, TS strict), `docker-compose.yml` (postgres, redis optional, backend, frontend, lmarenabridge stub), `.gitignore`, `README` link to quickstart, `Makefile`, `backend/alembic.ini`, `frontend/.env.local.example` |
| **Files** | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.env.example`, `AGENTS.md` already updated |
| **Blueprint refs** | `quickstart.md:15-41`, `docs/ENV.md`, `docs/TECH-STACK.md` |
| **Tests** | `docker compose config` passes, `pytest --collect-only` smoke, `npm run build` smoke, `curl /health` 501 placeholder |
| **Exit** | `docker-compose up --build` starts 4 services, `/docs` swagger placeholder, no violations of `constitution-check.md` |
| **Effort** | **S** (0.3d) |
| **Deviation risk** | Port mismatch `8000 vs 8001` — fix in compose env (research U-08) |

---

## Module 1 — Database Schema & Migrations (Foundation, M)

**Goal:** `data-model.md` §2–§6 materialized in Postgres with async SQLAlchemy.

| Item | Detail |
|------|--------|
| **Plan first?** | Yes — share ORM sketch from `data-model.md:220-245` for approval before migration |
| **Tasks** | 1. `backend/app/db/base.py` (declarative Base, async engine, session `get_db` dep) 2. `backend/app/models/{user,council_session,model_response}.py` from `data-model.md` §2-§4 (UUID PK, JSONB, FKs, unique `ux_responses_session_model`, checks) 3. `backend/app/schemas/*` Pydantic mirrors (§2-§4, `contracts/*.json` validation) 4. Alembic env async + `migrations/versions/001_init_users_sessions_responses.py` (autogenerate + manual `lower(email)` unique, GIN) 5. `backend/seed.py` optional (1 anon session + 1 user) |
| **Files** | `backend/app/models/`, `backend/app/schemas/`, `backend/migrations/`, `backend/seed.py` |
| **Blueprint refs** | `data-model.md` full, `contracts/council-session.json`, `docs/DATABASE.md` indexes |
| **Tests** | `pytest -k test_models`: create user→session→responses, cascade delete, unique violation, `user_id NULL` anon, Alembic `upgrade head`/`downgrade -1` round-trip, `asyncpg` connection |
| **Exit** | `docker-compose exec postgres psql … \dt` shows 3 tables + 7 indexes, `alembic current` = head, seed loads |
| **Effort** | **M** (1d) — includes async SQLAlchemy 2.0 caveats |
| **Risks** | `JSONB GIN` not needed Phase 1 → defer to keep migration small; `TIMESTAMPTZ` vs naive |

---

## Module 2 — Backend Core: App Bootstrap, Health & Models (M)

**Goal:** FastAPI skeleton with CORS/middleware/routing + first two contracts live.

| Item | Detail |
|------|--------|
| **Tasks** | 1. `app/main.py` (FastAPI, CORS `FRONTEND_ORIGIN`, `slowapi` limiter, `structlog` JSON, `/docs` Swagger) 2. `app/routers/{health,models}.py` 3. `app/config.py` (`pydantic-settings` mirroring `docs/ENV.md`: `LMARENA_TOKEN`, `LMARENA_BRIDGE_URL`, `DATABASE_URL`, `SECRET_KEY`, `MAX_MODELS_PER_QUERY`) 4. `app/services/lmarena_bridge.py` stub (just `GET /models` proxy via `httpx.AsyncClient`) 5. `GET /health` returns `{status, version, bridge, db}` with DB ping + bridge ping (2s timeout) 6. `GET /models` proxies bridge `GET /models` or static `MODEL_MAPPINGS` fallback if bridge down (502 mapping per `contracts/openapi.yaml:66`) |
| **Blueprint refs** | `contracts/openapi.yaml:24-67`, `docs/BACKEND.md:5-9`, `research.md` R-01, `quickstart.md:50-56` |
| **Tests** | `TestHealth`: 200 ok, db down → 200 degraded; `TestModels`: mocked `httpx.MockTransport` returns 6 models + unavailable bridge → 502 bridge error schema; CORS preflight; rate-limit 429 after 100; Swagger loads |
| **Exit** | `curl /health`, `curl /models` match `contracts/openapi.yaml` examples; `pytest` green |
| **Effort** | **M** (1d) |
| **Dependencies** | Module 1 (DB ping), 0 |

---

## Module 3 — LMArenaBridge Client (Streaming Core, L)

**Goal:** Production `httpx.AsyncClient` that speaks `POST /v1/chat/completions` with SSE/WebSocket upgrade, per `research.md` U-01/U-03/U-04 decisions.

| Item | Detail |
|------|--------|
| **Plan first?** | Yes — present `lmarena_client.py` interface + prompt templates for approval |
| **Tasks** | 1. `app/services/lmarena_client.py` (`LMArenaClient` class matching `docs/BACKEND.md:65-86` but corrected): per-request UUID `session_id`, `Authorization: Bearer`, `{"model": mappedInternalId, "messages": [{role,content}], "stream": true, "session_id": uuid}`, timeout 120s, `response_format` not needed 2. `app/services/prompts.py` (reasoning system prompt `<reasoning>`→`<answer>` + depth variants Brief/Standard/Detailed, confidence instruction) 3. Streaming parser: handle `text/event-stream` chunks (`data: {choices:[{delta:{content}}]}` vs bridge custom), WS fallback 4. `MODEL_MAPPINGS` loader from `config.yaml`/`env` (`claude→claude-3-5-sonnet-...`) 5. Single-token + multi-token pool support, 401 detection → log `token expired` |
| **Blueprint refs** | `research.md` R-01/R-03/R-05, `docs/BACKEND.md:65-86`, `docs/API-CONFIG.md:22-48`, `contracts/sse-events.md` |
| **Tests** | `TestLMArenaClient` with `httpx.MockTransport` emitting mocked SSE chunks → `confidence` parse, timeout→`status=timeout`, 401→ error, session_id unique per `gather`; `TestPrompts` assert `<reasoning>` tag present |
| **Exit** | Client can be called standalone `await client.chat_completion("claude", msgs)` returning streaming async generator; mocked integration in orchestrator |
| **Effort** | **L** (2d) — streaming parsers are fiddly |
| **Risks** | Bridge private format drift → design-notes fallback to raw text; decide to stub bridge locally with mock server for CI |

---

## Module 4 — Orchestrator: Fan-Out / Fan-In + SSE (Core, XL)

**Goal:** `POST /council/query` SSE stream per `contracts/openapi.yaml:69-136` + `contracts/sse-events.md` sequence, using `Module 3` client.

| Item | Detail |
|------|--------|
| **Plan first?** | Yes — present `orchestrator.py` flow diagram for approval (fan-out → gather → synthesis → persist) |
| **Tasks** | 1. `app/routers/council.py` (`POST /council/query` → `StreamingResponse(text/event-stream)`) 2. `app/services/orchestrator.py` (`run_council(query, config)`): create `CouncilSession` row (status running), `asyncio.gather(*[call_model(m)])` with `Semaphore(8)` + `asyncio.wait_for(120s)`, collect valid/failed, circuit breaker `pybreaker` 3-strike 5-min backoff, if <2 successes → `event: error` + `status=error`, persist `ModelResponse` rows 3. Emit events in order: `model_start`×N → `model_stream` interleaved → `model_done`×N → `synthesis_start` → `synthesis_stream` → `done` (or `error`) per `contracts/sse-events.md:24-38` 4. Deliberation log persist (only start/done, not every delta per `data-model.md:216`) 5. `httpx` error → `BridgeError 502`, rate-limit via `slowapi` (100 anon/500 auth) |
| **Blueprint refs** | `docs/WORKING.md:6-34`, `docs/BACKEND.md:34-63`, `data-model.md:102`, `contracts/sse-events.md`, `research.md` R-04/R-09 |
| **Tests** | `TestOrchestrator`: 2 models success → synthesis called, 0/1 success → error event, 1 timeout → partial, gather concurrency 8, `pybreaker` open after 3 fails, SSE wire `event: model_done\ndata: ...` exact, idempotent `ux_responses_session_model` |
| **Exit** | `curl -N POST /council/query '{query,models:[claude,chatgpt]}'` streams valid SSE that frontend can consume; `GET /council/session/{id}` returns `status done` + 2 responses; no regressions on `/health` `/models` |
| **Effort** | **XL** (3.5d) — hardest module, includes SSE backpressure, timeout, breaker |
| **Deps** | Modules 1,2,3 |

---

## Module 5 — Chairman Synthesis & Parsing (M, parallelizable with 4 late)

**Goal:** Synthesis prompt → chairman call → structured parse `synthesis/agreements/divergences/unique_insights`.

| Item | Detail |
|------|--------|
| **Tasks** | 1. `app/services/synthesis.py` (`build_synthesis_prompt(query, responses, mode, depth)` template from `docs/WORKING.md:30-31` + `research.md` R-06 JSON instruction: `You are chair... Return JSON {synthesis, agreements, divergences, unique_insights}` + fallback markdown) 2. `parse_synthesis(raw)` — try `json.loads` (response_format json) → else regex for `### Agreements` sections + confidence 0-100→0-1 3. Depth selector mutates prompt length (brief 80-120 tokens vs detailed 400+). 4. If `mode != consensus` → 501 Not Implemented per `data-model.md:77` 5. Persist `synthesis/agreements/divergences/unique_insights` + `total_latency` to `CouncilSession` |
| **Blueprint refs** | `docs/WORKING.md:28-34`, `data-model.md:77-83`, `research.md` R-06, `contracts/openapi.yaml` DoneEvent |
| **Tests** | `TestSynthesis`: JSON parse happy path, markdown fallback, malformed → error_message, depth variants affect prompt length, non-consensus 501 |
| **Exit** | `POST /council/query` with mocked bridge synthesis returns `done.data` with all four fields parsable; `GET /council/session` stores them |
| **Effort** | **M** (1d) |
| **Deps** | Module 4 (called inside orchestrator) |

---

## Module 6 — Auth & Session Management (M)

**Goal:** `POST /auth/register|login`, `GET /auth/me`, JWT middleware, `GET /council/sessions` + `DELETE /council/session/{id}` with ownership checks.

| Item | Detail |
|------|--------|
| **Tasks** | 1. `app/auth/{security,router}.py` (`python-jose` JWT `{sub=email, exp}` 24h, `passlib[bcrypt]` hash, `SECRET_KEY` 32+ min) 2. `POST /auth/register` 409 on duplicate `lower(email)`, `POST /auth/login` 401 bad creds, `GET /auth/me` 401 without Bearer 3. `app/routers/sessions.py`: `GET /council/sessions?limit&offset&user_id` filtered by `request.state.user` or anon blocked, `GET /council/session/{id}` public if anon but anon not enumerated, `DELETE` 403 if not owner (anon deletable only by creator? decision: 403 for anon delete) 4. Tie `CouncilSession.user_id` from JWT if present else `NULL` 5. `lmarena_token` per-user override not Phase 1 (global only) — note in design-notes |
| **Blueprint refs** | `contracts/openapi.yaml:243-325`, `data-model.md:25-42`, `research.md` R-11, `docs/BACKEND.md:29-32` |
| **Tests** | `TestAuth`: register→login→me flow, duplicate 409, wrong pwd 401, expired JWT 401, `TestSessions`: owner can delete, non-owner 403, anon list privacy, pagination |
| **Exit** | Auth flow via `curl` matches `quickstart.md:111`; seeded user history appears in `/council/sessions`; anon session not leaked |
| **Effort** | **M** (1.2d) |
| **Deps** | Module 1 (users table), 2 (router) |

---

## Module 7 — Frontend Foundation (Next.js, M)

**Goal:** Dark Perplexity shell that can call `Module 2/4` APIs, per `docs/UIUX.md`, `docs/TECH-STACK.md` FE.

| Item | Detail |
|------|--------|
| **Tasks** | 1. Tailwind config `gray-900/#111827` `cyan-500/#00BFFF` per `UIUX.md:14-22`, Inter + JetBrains Mono via `next/font`, Zustand store `councilStore` (query, models, mode, depth, showReasoning, chairman), React Hook Form 2. `components/{HeroSearch,ModelSelector,PillToggle}` 3. API client `lib/api.ts` (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WEBSOCKET_URL` from `docs/ENV.md`), `lib/sse.ts` (`EventSource` fallback + `fetch` stream post handling) 4. `app/page.tsx` hero search + model selector (min 2 max 8, pills), mode/depth controls (Phase 1 disabled modes show 501 badge) 5. Layout `HistorySidebar` placeholder |
| **Blueprint refs** | `docs/UIUX.md:10-35`, `docs/TECH-STACK.md:7-16`, `quickstart.md:95-100`, `research.md` R-04 |
| **Tests** | `Jest/RTL`: model toggle enforces 2..8, `Ctrl+K` focuses search, dark theme snapshot, Zustand state |
| **Exit** | `npm run dev` hero at `localhost:3000`, toggle 6 models, `POST /council/query` from UI via mocked API returns cards (no streaming yet) |
| **Effort** | **M** (1.5d) |
| **Deps** | Module 0 |

---

## Module 8 — Frontend Results: Streaming + Model Cards + Unified Answer (L)

**Goal:** Live SSE rendering per `contracts/sse-events.md`, model cards, synthesis section, latency/confidence.

| Item | Detail |
|------|--------|
| **Plan first?** | Yes — present component tree + SSE hook for approval |
| **Tasks** | 1. `hooks/useCouncilStream.ts` (Vercel AI SDK vs native `ReadableStream`: read `text/event-stream`, parse `event: model_done` → zod `contracts/*.json`) 2. `components/{UnifiedAnswer,ModelCard,ConfidenceBar,DeliberationLog}` per `UIUX.md:38-48` (✨ unified top with agree/diverge/insights, cards horizontal scroll desktop / stack mobile, `<details>` for `<reasoning>`, latency/confidence, spinner→✅/❌) 3. `app/council/[id]/page.tsx` replay via `GET /council/session/{id}` 4. Error handling: timeout/error toast, retry button |
| **Blueprint refs** | `contracts/sse-events.md`, `docs/UIUX.md:52-69`, `docs/WORKING.md:40-48` |
| **Tests** | `Jest`: SSE event parsing, `model_done`→card frozen, synthesis streams; Playwright `test/e2e/council.spec.ts` with mocked SSE (no real bridge needed) |
| **Exit** | Type query → see `model_start` spinners → deltas streaming → unified answer appears after synthesis → `GET /council/session/{id}` replay works; responsive breakpoints pass |
| **Effort** | **L** (2d) |
| **Deps** | Modules 4,5,7 |

---

## Module 9 — Frontend History Sidebar, Session Replay, Download Report (M)

**Goal:** Persisted history + share + export per `docs/USAGE.md:25-35`.

| Item | Detail |
|------|--------|
| **Tasks** | 1. `HistorySidebar` calls `GET /council/sessions?user_id=&limit=20` (JWT if logged) with pagination, chronological, click → `GET /council/session/{id}` replay 2. Shareable URL `/council/{id}` deep link 3. `Download Full Report` button: client-side generate `.html`/`.txt` with synthesis + all responses (or server `GET` export) 4. Keyboard `Ctrl+K`/`Esc`/`Enter` per `USAGE.md:31` 5. Auth-aware: logged-in history persists, anon localStorage fallback or just ephemeral |
| **Blueprint refs** | `docs/USAGE.md:33-48`, `docs/BACKEND.md:26`, `contracts/openapi.yaml:202-241` |
| **Tests** | Playwright history flow: run query → sidebar lists it → click replays identical synthesis |
| **Exit** | History sidebar lists past `done` sessions, download produces non-empty report, share URL opens correctly |
| **Effort** | **M** (1d) |
| **Deps** | Modules 6,8 |

---

## Module 10 — LMArenaBridge Configuration & Connectivity (S, can be parallel 2+)

**Goal:** Bridge actually reachable, token + session pool correct, then integration.

| Item | Detail |
|------|--------|
| **Tasks** | 1. Provide `lmarenabridge/config.json` template (tokens array, session_pool per `docs/API-CONFIG.md:34-48`), `docker-compose.yml` service `lmarenabridge:8001` 2. Configure `MODE=direct_chat`, `file_bed_enabled=false`, `websocket_port:8001` 3. Health check loop: backend `GET {LMARENA_BRIDGE_URL}/health` or `/models`, log `arena-auth-prod-v1` 401 rotation 4. Manual `curl -N POST {LMARENA_BRIDGE_URL}/v1/chat/completions -H "Authorization: Bearer $LMARENA_TOKEN"` for each of 6 models → capture real `choices/delta` shape to lock `Module 3` parser (feed to `design-notes.md` if drift) |
| **Blueprint refs** | `research.md` R-01/R-02, `docs/API-CONFIG.md:34-48`, `docs/SETUP.md:38-48`, `quickstart.md:35` |
| **Tests** | `scripts/test-bridge.sh` (or `pytest -k test_bridge_live --run-live` gated by env) hits bridge per model, asserts stream yields delta; CI skips by default with stub |
| **Exit** | `curl http://localhost:8000/models` returns ≥6 available models (proxied), bridge logs no `session_id` leakage; fallback static mapping works if bridge down |
| **Effort** | **S** (0.5d) + waiting on token |
| **Deps** | Module 0, token from user |

---

## Module 11 — Integration & E2E (M)

**Goal:** `user query (FE) → BE → Bridge → models → SSE → synthesis → FE display` end-to-end, env wiring correct per `quickstart.md:15-56`.

| Item | Detail |
|------|--------|
| **Tasks** | 1. Wire `frontend/.env.local` `NEXT_PUBLIC_API_URL=http://localhost:8000` compose vs vercel, CORS `FRONTEND_ORIGIN` 2. Nginx `X-Accel-Buffering: no` / `proxy_buffering off` for SSE (tested per research R-04) 3. Seed+demo script (`scripts/demo.sh`): `curl -N POST /council/query` + open `http://localhost:3000/council/{id}` 4. `design-notes.md` update with any contract/data-model drift 5. Smoke Checklist per `quickstart.md:50-68` all green, `docker-compose logs` no errors, `GET /health` both services ok |
| **Blueprint refs** | `quickstart.md` full, `docs/ARCHITECTURE.md:46-55` data flow, `constitution-check.md` |
| **Tests** | Playwright `e2e/full.spec.ts`: hero search → toggle 3 models → submit → wait for `done` → assert unified answer + 3 cards + download report exists; `pytest e2e` with real bridge if flag, else mocked |
| **Exit** | Recorded Loom/demo shows hero→cards→unified answer→history→download, `design-notes.md` current, no regressions on `pytest` + `npm test` + `playwright` |
| **Effort** | **M** (1d) |
| **Deps** | All modules |

---

## Suggested Build Order & Calendar

```
Week 1: M0 (S) → M1 (M) → M2 (M)  [DB+health vertical slice done]
Week 2: M3 (L) → M4 (XL)  [core council streaming — hardest]
Week 3: M5 (M) → M6 (M) → M7 (M)  [synthesis+auth+FE shell, can parallel M10 anytime]
Week 4: M8 (L) → M9 (M) → M10 (S) → M11 (M)  [streaming UI+history+integration]
```

Dependencies graph: `M0 → (M1→M2→M3→M4→M5→M8→M9→M11)` and `M6` branches after M1, `M7` after M0, `M10` anytime after M0. Critical path is `M3+M4` (5.5d) — start early.

## Test Strategy (after each module, per prompt)

- **Backend:** `pytest` + `pytest-asyncio` + `httpx.MockTransport` (no real bridge in CI). Each module ships with `tests/test_<module>.py`.
- **Frontend:** `Jest/RTL` unit + `Playwright` e2e with mocked SSE (bridge mocked). `npm run build` must pass.
- **Contracts:** `openapi.yaml` + `contracts/*.json` validated in CI (`python -c "yaml.safe_load(...)"`).
- **Gate:** After each module, `pytest -q && npm test -- --passWithNoTests && playwright test --project=chromium --grep=mocked` green before next module PR. Coverage target 80% per `docs/PROCESS.md`.

## Deviation Policy

All differences from `data-model.md`/`contracts/` logged in `design-notes.md` with `Decision/Rationale/Alternatives`. Example deviations anticipated: port `8000↔8001`, `GIN` deferred, `per-request session_id` over pooled (U-03), `confidence` fallback null.

## Risks & Mitigations (from research.md §6)

| Risk | Mitigates in Roadmap |
|------|----------------------|
| Bridge format drift (High/High) | M3 parser has fallback, design-notes, pinned SHA, `TestLMArenaClient` with real capture |
| Token rotation 401 | M10 health loop + M3 401 handling, user provides token per quickstart |
| SSE buffering via Vercel/ALB | R-04 spike in M4, `Cache-Control`/`X-Accel-Buffering`, M11 nginx check |
| Reasoning XML non-compliance | M3 fallback regex, M5 synthesis fallback markdown per `research.md` R-05/R-06 |

---

## Approval Request

> **Please confirm: (1) module order & dependencies above, (2) effort estimates, (3) `M3+M4` critical path focus, (4) test gates per module. After approval, I will proceed module-by-module: for each, present a focused implementation plan → your approval → code + tests → design-notes entry if deviates.**

Artifacts still pending: none — this roadmap is the gate before coding.
