# Phase 0: Setup, Goal & Research — AI Council Website

> **Status:** Phase 0 Complete | **Date:** 2026-09-04 | **Owner:** AI Council Team
> **Source Docs Loaded:** `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/WORKING.md`, `docs/BACKEND.md`, `docs/DATABASE.md`, `docs/TECH-STACK.md`, `docs/API-CONFIG.md`, `docs/ENV.md`, `docs/FEATURELIST.md`, `docs/PHASEWISEPLAN.md`, `docs/UIUX.md`, `docs/DEPLOYMENT.md`, `docs/PROCESS.md`
> **Missing Docs Checked:** `PRD.md` (not found - consolidated from docs/), `constitution.md` (not found - inferred from PROCESS.md/ARCHITECTURE.md), `.specify/scripts/bash/update-agent-context.sh` (not found - will create in Phase 1)

---

## 1. Load Context — Summary of Foundational Documents

| Doc | Key Takeaway |
|-----|--------------|
| **README.md** | Perplexity-style, dark-themed Next.js+FastAPI app querying 6+ models in parallel via LMArenaBridge, no API keys. Three pillars: parallel execution, chairman synthesis, full transparency. |
| **ARCHITECTURE.md** | 4-tier: Frontend (Next.js) → Backend (FastAPI orchestrator + consensus + session mgr) → LMArenaBridge (OpenAI-proxy) → LMArena.ai. SSE/WebSocket streaming, PostgreSQL, stateless backend, PgBouncer, LMArenaBridge pool. |
| **WORKING.md** | 3-stage pipeline: Fan-Out (`asyncio.gather`) → Peer Review/Debate (optional) → Fan-In/Chairman synthesis. 8 event types (`model_start` → `done`). Four consensus modes (Consensus, Majority Voting, Confidence Weighting, Debate). Prompt engineering via `<reasoning>`/`<answer>` XML. |
| **BACKEND.md** | REST + SSE: `GET /health`, `GET /models`, `POST /council/query` (SSE), `GET/DELETE /council/session/{id}`, `POST /auth/*`. Core `run_council()` + `LMArenaClient.chat_completion()` via `httpx.AsyncClient` + WS upgrade. Circuit breaker 120s, 3 strikes backoff. |
| **DATABASE.md** | PostgreSQL 15+ with 3 entities: `users` (UUID, email unique), `council_sessions` (FK user_id nullable for anon, JSONB selected_models, synthesis/agreements/divergences/insights), `model_responses` (FK session_id, reasoning/final_answer/confidence/latency/status/critique/raw_payload JSONB). Alembic migrations, 3 indexes, Redis cache. |
| **TECH-STACK.md** | FE: Next.js 14, React 18, TS 5, Tailwind 3, Vercel AI SDK 3, Zustand 4, RHF 7. BE: FastAPI 0.115, Python 3.11, Uvicorn, SQLAlchemy 2 (async), Alembic, Pydantic 2, httpx 0.27. Infra: Docker Compose, GH Actions, Vercel/AWS, Prometheus. |
| **API-CONFIG.md** | Env-driven, `MODEL_MAPPINGS` YAML, LMArenaBridge `config.json` (tokens array, session_pool, direct_chat), Swagger at `/docs`. |
| **FEATURELIST.md** | MVP = hero search, dark theme, model toggles, unified answer, cards, SSE, orchestrator, PG, auth. Phase 2 = modes, critique, depth, uploads, PWA. |
| **UIUX.md** | Perplexity-inspired, Inter/JetBrains Mono, gray-900/cyan-500, hero search → unified answer (✨) → scrollable cards → status indicators. WCAG 2.1 AA, responsive 3 breakpoints. |

No `constitution.md` found — inferred constraints from `PROCESS.md` (Conventional Commits, GitFlow, 80% coverage, Squash-Merge, Swagger required) and `ARCHITECTURE.md` (secrets never to FE, CORS, private DB subnet).

---

## 2. Refined Goal (1–2 Sentences)

**Primary Objective:** Build a free, open-source **Perplexity-style AI Council** that fans a user query out to 6+ frontier models in parallel via **LMArenaBridge** (headless-browser gateway), then fans in through a designated **Chairman model** to synthesize a single transparent answer — streaming every model's full reasoning and final answer token-by-token via SSE, persisting sessions in PostgreSQL, and delivering it through a dark-themed Next.js UI without requiring any API keys.

Alternative one-liner: *Deliberate with 6 AIs at once, get one honest answer — free, transparent, streamed.*

---

## 3. Unknowns — NEEDS CLARIFICATION

### U-01: LMArenaBridge Exact API Contract
**Question:** `BACKEND.md:68-85` shows `POST /v1/chat/completions` with `{model, messages, stream, session_id}` + `Authorization: Bearer <token>` + WS upgrade, but is it OpenAI-spec compliant (choices/delta/finish_reason), what are error codes, rate limits, file upload format, and does `GET /models` proxy dynamically or static? Docs reference `arena.ai` vs `lmarena.ai` domain mismatch.
**Impact:** Blocks `lmarena_client.py` implementation, retry logic, model availability polling.

### U-02: Auth Token Lifecycle (arena-auth-prod-v1)
**Question:** Extraction via DevTools cookies is documented in `SETUP.md`, but what is TTL, refresh mechanism, expiry signal (401 vs custom), multi-token rotation strategy in `config.json`, and per-user token storage (DATABASE.md:56 `lmarena_token` nullable) vs global `LMARENA_TOKEN` env?
**Impact:** Determines secrets management, token-rotation cron, UX for "Token expired" troubleshooting.

### U-03: Session Isolation & Concurrency
**Question:** `API-CONFIG.md:40-44` shows per-model `session_pool` with pre-allocated UUIDs. Do we generate UUID per request (`lmarena_client.py:72`) or reuse pooled sessions? How to avoid context leakage when parallel `asyncio.gather()` shares same LMArena auth? Does LMArenaBridge enforce `direct_chat` vs `battle` mode semantics?
**Impact:** Affects orchestrator correctness, concurrency bugs, answer contamination.

### U-04: Streaming Transport — SSE vs WebSocket
**Question:** `WORKING.md:40-48` lists SSE events (`model_start` etc.), `ARCHITECTURE.md:15` says SSE/WebSocket, `TECH-STACK.md` lists `Vercel AI SDK` + `Websockets 11.x` + `httpx`. Should BE→FE be SSE (`text/event-stream`) or WebSocket (`/ws`)? How to handle reconnection, sticky sessions when horizontally scaled?
**Impact:** Frontend SDK choice, Nginx/ALB config, failure modes for slow Gemini etc.

### U-05: Reasoning Extraction Prompt Contract
**Question:** `WORKING.md:18` instructs `<reasoning>`/`<answer>` XML. Do all models obey reliably? How to parse malformed XML, extract confidence (self-reported 0-100 vs 0-1?), token counts? What fallback if model ignores system prompt? Depth selector (Brief/Standard/Detailed) — how does it mutate prompts?
**Impact:** Defines prompt templates, parser robustness, confidence normalization.

### U-06: Synthesis & Consensus Logic
**Question:** `WORKING.md:30-31` synthesis prompt mentions agreements/divergences/unique insights, but `BACKEND.md:53-54` does `parse_synthesis(final_answer)` — is Chairman output unstructured text requiring regex parsing or structured JSON (e.g., `response_format: json_object`)? How is Majority Voting / Weighted Voting implemented without Chairman? `FEATURELIST.md` marks these as unchecked — scope for Phase 1?
**Impact:** Determines if synthesis is deterministic/parasable, API schema for `CouncilResult`.

### U-07: Persistence & Anonymous Sessions
**Question:** `DATABASE.md:64` `user_id nullable` allows anon sessions. What is retention policy, shareable URL (`/council/abc-123` per `USAGE.md`), pagination for `History sidebar`? JSONB `deliberation_log` exact shape? Do we store SSE timeline for replay vs just final state?
**Impact:** History API design, DB indexing, GDPR deletion.

### U-08: Deployment Target Decision
**Question:** `DEPLOYMENT.md` lists 3 options (Docker Compose self-hosted, Vercel+AWS ECS+RDS, single VM). Which is canonical for Phase 1 local dev? Does `FRONTEND_PORT`/`BACKEND_PORT` assume compose networking (`http://lmarenabridge:8000` vs `localhost:8001` mismatch in ENV.md vs API-CONFIG.md)? How to handle SSL/WebSocket upgrade in each?
**Impact:** Blocks `quickstart.md`, `.env.example`, `docker-compose.yml` correctness.

### U-09: Rate Limiting & Circuit Breaker Policy
**Question:** `BACKEND.md:89-92` circuit breaker 3 failures → backoff, 120s timeout; `BACKEND.md:101-102` rate limit 100/hr anon, 500/hr auth. Are limits per-IP via Redis or in-memory? Queue management for 8 parallel models per query — connection pool size? What status codes for throttling vs model failure?
**Impact:** Needed before load testing, prevents LMArena bans.

### U-10: File Upload & RAG Scope
**Question:** `FEATURELIST.md:35` lists file uploads via LMArena file bed server (disabled in `API-CONFIG.md:46`). Is this in MVP or Phase 2 defer? If deferred, do we stub `file_bed_enabled`? RAG via vector DB (Pinecone) is Future Scope — exclude now?
**Impact:** Scope creep risk; keep Phase 1 lean.

### U-11: Auth Implementation (JWT + OAuth)
**Question:** `BACKEND.md:29-32` auth endpoints `POST /auth/register|login` return JWT. Which library (`python-jose`, `passlib[bcrypt]`)? OAuth Google/GitHub per `FEATURELIST.md:27` — is it MVP or Phase 2? `SECRET_KEY` 32+ chars, `ADMIN_PASSWORD` scope?
**Impact:** Affects `users` table, middleware, frontend auth flow.

### U-12: Observability & Testing Harness
**Question:** `PHASEWISEPLAN.md Phase 3` promises Prometheus+Grafana, Pytest/Jest/Playwright with 80% coverage. For Phase 1, what is minimal test harness (pytest-asyncio + httpx mock for LMArenaBridge) and structured logging (`structlog` JSON) fields?
**Impact:** Determines early CI pipeline shape.

---

## 4. Initial Research Plan (Tasks Only — No Code Yet)

| ID | Unknown | Research Task | Method | Success Criterion | Owner |
|----|---------|---------------|--------|-------------------|-------|
| R-01 | U-01 API Contract | Clone `lmarenabridge/lmarenabridge` (if public), inspect `openapi.json`/`config.json`, `curl -N POST http://localhost:8001/v1/chat/completions` with dummy token, capture request/response + SSE chunks, compare with `BACKEND.md` snippet, document delta | Repo read + local curl/Wireshark | OpenAPI spec file in `contracts/lmarena-bridge.openapi.yaml` with correct `session_id` semantics, error codes mapped | BE |
| R-02 | U-02 Token | Create LMArena.ai account, extract `arena-auth-prod-v1` in Chrome DevTools, decode base64, check expiry `exp` claim, test 401 after logout, test multi-token array in bridge config with 2 accounts | Manual browser + JWT decode (jwt.io) | Token TTL documented, refresh SOP in `research.md` addendum, env `LMARENA_TOKEN` vs `lmarena_token` per-user decision | Infra |
| R-03 | U-03 Sessions | Load-test: fire 6 parallel `gather()` with same vs distinct `session_id`, verify via bridge logs if context leaks; read bridge `session_pool` code path; test `direct_chat` vs `battle` mode | Python script + bridge logs | Decision: per-model UUID per request (isolated) vs pooled reuse, documented in `data-model.md` | BE |
| R-04 | U-04 Streaming | Spike: implement minimal FastAPI SSE endpoint `StreamingResponse(text/event-stream)` vs `WebSocket`, test with `Vercel AI SDK useChat` vs native `EventSource`, test through Nginx/ALB with `proxy_buffering off`, horizontal scale with Redis pub/sub | Two-branch spike | ADR: SSE is canonical BE→FE (simpler, Vercel-friendly), WS reserved for Bridge→LMArena internal | FE/BE |
| R-05 | U-05 Reasoning | Prompt-engineering experiment: send `<reasoning>` system prompt to each of 6 models via bridge, collect 20 samples, evaluate XML compliance rate, test fallback regex `re.DOTALL` + confidence extraction pattern, test depth variants (Brief/Standard/Detailed) prompt deltas | Bridge + qualitative eval | Parser spec + confidence normalization (0-1 float) + depth prompt templates committed to `contracts/prompts.md` | BE |
| R-06 | U-06 Synthesis | Test Chairman synthesis: feed 3 synthetic responses to Claude/GPT-4o, ask for agreements/divergences/insights in JSON vs markdown, measure parsability, define fallback to unstructured + `parse_synthesis` heuristics, scope Majority/Weighted Voting to Phase 2 | Prompt eval | Decision: Chairman returns JSON `{synthesis, agreements, divergences, unique_insights}` with `response_format: json_object` else regex fallback | BE |
| R-07 | U-07 Persistence | Review `DATABASE.md` ERD vs `FEATURELIST.md` History requirement, query Supabase/Neon vs local PG perf, define `council_sessions` lifecycle (create on query start, update on synthesis done), define `deliberation_log` JSONB event timeline schema, define anon retention (7 days) vs auth indefinite | DB design session | ERD finalized in `data-model.md`, `/council/session/{id}` contract with `deliberation_log` example | BE/DB |
| R-08 | U-08 Deploy | Validate `docker-compose.yml` from `SETUP.md` by running `docker compose config`, fix port mismatch (8000 vs 8001), test `localhost:3000 → 8000 → 8001` chain, compare Vercel+AWS vs Compose cost/complexity matrix, pick Phase 1 target | Docker dry-run + decision matrix | `quickstart.md` local compose is canonical Phase 1, `ARCHITECTURE.md` port alignment fixed | Infra |
| R-09 | U-09 Resilience | Bench `httpx` timeout 120s vs 60s for Gemini, test circuit breaker (fail 3× → open 60s → half-open) using `pybreaker` or custom, test rate limit via `slowapi` with Redis vs memory, simulate 8-model thundering herd | Chaos test | Policy doc: 120s timeout, 3-strike breaker 5-min backoff, 100/500 per hr, queue via `asyncio.Semaphore(8)` | BE |
| R-10 | U-10 Upload/RAG | Check bridge `file_bed_enabled` code path, test image upload if enabled, confirm RAG is out-of-scope for Phase 1, stub API as 501 Not Implemented | Code read + manual test | ADR: Defer file/RAG to Phase 2, keep flag false, no UI for uploads in MVP | PM |
| R-11 | U-11 Auth | Compare `python-jose` vs `PyJWT` + `passlib[bcrypt]`, test OAuth flow via `authlib` Google/GitHub, confirm JWT shape `{sub, exp, email}`, decide OAuth defer to Phase 2 (email/password only for MVP) | Library eval | Decision: JWT via `python-jose` + bcrypt, OAuth deferred, `users` table as spec'd | BE |
| R-12 | U-12 Obs/Test | Set up `pytest` + `pytest-asyncio` + `httpx.MockTransport` mocking bridge, `structlog` JSON processor test, define minimal E2E via Playwright against mocked SSE | Tool eval | Test harness + logging schema defined, CI stub in `PROCESS.md` | QA |

**Phase 0 Exit Criteria:** All R-01..R-12 tasks have a written finding in this doc's §5 (to be filled after running tasks) before proceeding to code. No data models or endpoints are implemented in this phase.

---

## 5. Research Findings & Decisions (to be filled after executing R-01–R-12)

> **Current:** Assumed decisions pending validation — will be updated after spike. Initial assumptions:

- **Bridge contract** assumed OpenAI-compatible + `session_id` extension + WS upgrade — *validate with R-01*.
- **SSE** assumed canonical for BE→FE — *validate with R-04*.
- **Chairman JSON** assumed — *validate with R-06* else fallback to markdown parsing.
- **Deployment** assumed `docker-compose.yml` local is Phase 1 target — *validate with R-08*.
- **Auth** assumed email/password MVP, OAuth Phase 2 — *validate with R-11*.
- **File upload/RAG** assumed deferred — *validate with R-10*.

After R-tasks, update here with `Decision:` + `Rationale:` + `Alternatives rejected:` per ADR template.

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LMArenaBridge private/breaking changes | High | High | Pin commit SHA, add contract tests, fallback to headless Playwright if gateway fails |
| `arena-auth-prod-v1` rotation bans account | Med | High | Pool multiple tokens, exponential backoff, never expose to FE, rotate via vault |
| SSE through Vercel/ALB buffering | Med | Med | `Cache-Control: no-cache`, `X-Accel-Buffering: no`, test early (R-04) |
| Reasoning XML non-compliance per model | High | Med | Robust regex parser + confidence default `null`, show raw if parse fails |
| PG JSONB query perf at scale | Low | Med | GIN index on `deliberation_log`, archive old anon sessions |

---

## 7. Next Phase Gate

- [ ] R-01..R-12 executed and §5 filled
- [ ] `data-model.md`, `contracts/`, `quickstart.md` drafted in Phase 1
- [ ] Design review approved before `orchestrator.py` coding
- [ ] `update-agent-context.sh` run (Phase 1)

**Artifacts produced this phase:** `research.md` (this file) — single source of truth for Phase 1.
