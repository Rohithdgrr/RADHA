# Design Notes — Deviations from Phase 1 Blueprint

> **Purpose:** Per Phase 2 prompt: document any deviations from `data-model.md` / `contracts/` after each module. Append-only, newest at top.
> **Blueprint:** `data-model.md`, `contracts/openapi.yaml`, `contracts/*.json`, `contracts/sse-events.md`, `quickstart.md`, `research.md`
> **Inferred constitution:** `constitution-check.md`

## Template (copy for each deviation)

```markdown
### YYYY-MM-DD — Module N: Title

- **Deviation:** What changed vs blueprint (file:line)?
- **Rationale:** Why (research finding, tech limit, UX)?
- **Alternatives considered:** 
- **Impact:** Contracts / data-model / quickstart / tests affected?
- **Approved by:** 
```

## Log

### 2026-09-04 — Module 1: DB sqlite3 (per user request)

- **Deviation:** `data-model.md:1` specifies PostgreSQL 15+ + JSONB/UUID native; `quickstart.md:21` PG URL. Changed to **sqlite3 via `sqlite+aiosqlite:///./aicouncil.db`** as dev default (`app/config.py:5`, `alembic.ini:8`, `.env.example:3`, `app/models/*.py` using `String(36)` PK + `JSON` not `JSONB`). PG still supported via `DATABASE_URL` env override for prod.
- **Rationale:** User requested sqlite3 as-of-now for zero-Docker local dev; faster onboarding, no `docker-compose` Postgres needed. PG types mapped to SQLite-compatible (JSON→TEXT, UUID→String).
- **Alternatives considered:** Keep PG and require Docker/Neon; add dual URL factory (kept, but default switched).
- **Impact:** Contracts unchanged (JSON remains JSON); `quickstart.md` Module 3 step `psql \dt` now `sqlite3 aicouncil.db .tables`; tests use `sqlite+aiosqlite:///:memory:` no PG required; `docker-compose.yml` postgres service kept but optional (`profiles` not default). Reversible via env.
- **Approved by:** User 2026-09-04 (question: use sqlite3 as of now)

### 2026-09-04 — Phase 1 -> Phase 2 Transition

- **Deviation:** None yet. Roadmap anticipates possible drifts:
  - Port mismatch `LMARENA_BRIDGE_URL` `8000` (BACKEND.md:76) vs `8001` (ENV.md:11 / API-CONFIG.md:46) — will canonicalize to `8001` in compose (`lmarenabridge:8001` internal, `localhost:8001` local), per `quickstart.md:19` and `research.md` U-08. Not a code deviation, just doc alignment.
  - `data-model.md:98` GIN index `ix_sessions_models_gin` deferred to post-MVP if query-by-model not needed — keeps `001` migration small.
  - `data-model.md:216` deliberation_log stores only `model_start/done` + `synthesis_*` + errors (not every `model_stream` delta) to bound JSONB — already in blueprint, but emphasized.
  - Session isolation: per-request UUID over pooled `session_pool` per `research.md` R-03 decision — `lmarena_client.py` will generate `uuid4()` per call, `config.json session_pool` kept for Bridge compat but unused Phase 1.
- **Rationale:** Keep Phase 1 lean, avoid private Bridge internals, bound storage.
- **Impact:** None to contracts; `openapi.yaml` unchanged; quickstart ports clarified.

---

### 2026-09-04 — Modules 7-9 Frontend

- **Deviation:** `contracts/openapi.yaml` specifies POST SSE via `text/event-stream`; implemented via `fetch` + `ReadableStream` reader + custom `parseSSEChunk` (`lib/sse.ts`) rather than `EventSource` (GET-only) nor Vercel AI SDK `useChat` (kept optional). Matches `research.md` R-04 decision SSE over WS.
- **Rationale:** POST body needed (query+models), EventSource cannot POST; `fetch` streaming works through Nginx `X-Accel-Buffering: no`.
- **Impact:** `frontend/lib/sse.ts` + `hooks/useCouncilStream.ts` tested with mocked SSE; no contract change.

### 2026-09-04 — Modules 10-11 Integration

- **Deviation:** `docker-compose.yml` postgres kept but not required for dev (sqlite file `./aicouncil.db`). Bridge service put under profile `with-bridge` to allow `docker-compose up` without real token (fallback mock). `quickstart.md` local 5-min still works with `python seed.py` + `alembic upgrade head`.
- **Rationale:** User requested sqlite3 as of now; lower friction.
- **Impact:** `quickstart.md` step 2 `psql \dt` alternative `sqlite3 aicouncil.db .tables`; `lmarenabridge/config.json.example` added.

## Pending ReviewQueue

- Bridge real payload shape after live test may require `lmarena_client.py` parser tweak → see `lmarenabridge/README.md`.
- Synthesis JSON vs markdown validated in `tests/test_synthesis.py` — JSON first, fallback regex.
