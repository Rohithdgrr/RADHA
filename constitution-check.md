# Constitution / Rules Re-evaluation (Phase 1 Gate)

> **Date:** 2026-09-04
> **Checked against:** `docs/PROCESS.md`, `docs/ARCHITECTURE.md` §Security, `docs/BACKEND.md` §Security, `docs/ENV.md`
> **Original `constitution.md`:** Not found — inferred from PROCESS.md + ARCHITECTURE.md. If canonical constitution.md is later added to `docs/`, re-run this check.

## Inferred Architectural Constraints

1. **GitFlow + Conventional Commits + Squash-Merge + 1 reviewer** — `PROCESS.md:5-25`
2. **80% coverage, Swagger at `/docs` required, env never committed** — `PROCESS.md:33-48,72` + `docs/ENV.md` Security Notes
3. **Secrets never to FE, CORS only FRONTEND_ORIGIN, DB private subnet, token in vault (Phase 3)** — `ARCHITECTURE.md:64-68`, `BACKEND.md:99-104`
4. **Phase gates: no code before design review** — `PHASEWISEPLAN.md` + research.md §7, `PROCESS.md` Documentation Standards

## Design Compliance Check

| # | Constraint | Phase 1 Design | Status | Evidence |
|---|------------|----------------|--------|----------|
| C-01 | No secrets to frontend | `contracts/openapi.yaml`: auth via Bearer JWT only; `LMARENA_TOKEN` stays in backend env, `DATABASE_URL` server-only. Frontend env only `NEXT_PUBLIC_API_URL` | ✅ PASS | `ENV.md` split Backend vs Frontend, `ARCHITECTURE.md` Security Boundaries |
| C-02 | CORS minimal | `BACKEND.md:101` CORS configured to `FRONTEND_ORIGIN` only | ✅ PASS | `data-model.md` not exposing CORS wildcard; `ENV.md` lists `FRONTEND_ORIGIN` |
| C-03 | DB private | `data-model.md` uses asyncpg, private subnet intent; `ARCHITECTURE.md:68` DB private subnet | ✅ PASS | No FE direct DB access, only via `/council/*` API |
| C-04 | Swagger required | `contracts/openapi.yaml` complete OpenAPI 3.1, Swagger at `/docs` per `API-CONFIG.md:62` | ✅ PASS | OpenAPI file + schemas, ready for FastAPI auto-docs |
| C-05 | 80% coverage, lint, tests | Phase 1 test harness: `pytest+pytest-asyncio+httpx.Mocks`, `Jest/RTL`, `Playwright` per `research.md` R-12; CI via GH Actions `PROCESS.md:54-67` | ✅ PASS (plan) | No code yet — harness defined, not yet implemented |
| C-06 | Conventional Commits, GitFlow | `PROCESS.md:15-25` — Phase 1 commits will follow `feat(contracts):` `feat(data-model):` etc., PR to `develop` | ✅ PASS | Documented, no violation |
| C-07 | Env never committed | `.env.example` committed, `.env` gitignored per `ENV.md:35` | ✅ PASS | `quickstart.md` instructs `cp .env.example .env` |
| C-08 | No code before design review | `research.md:14-15 Phase 0 Exit Criteria`, `data-model.md:11 Review Checklist`, this check — blocks `orchestrator.py` until approval | ✅ PASS | All Phase 1 artifacts are docs only, no `backend/app/` code yet |
| C-09 | Secrets in vault Phase 3 | `research.md` R-02 notes vault for prod, plaintext dev only | ✅ PASS | No vault code in Phase 1 |
| C-10 | Free, no API keys to user | Design uses `LMArenaBridge` + `arena-auth-prod-v1` token server-side only; user never needs keys | ✅ PASS | Aligned with `README.md` Free pillar |

## Scope Creep Guard

- **File upload / RAG:** Explicitly deferred to Phase 2 per `research.md` R-10 / `data-model.md:10` / `contracts/openapi.yaml` 501 for unsupported modes. No buckets/vectors in Phase 1 schema.
- **OAuth Google/GitHub:** Deferred to Phase 2 per `research.md` R-11; Phase 1 only email/password JWT.
- **Debate/Specialist/Weighted modes:** `contracts/openapi.yaml` allows enum but backend returns 501 if not `consensus` in Phase 1 — prevents half-built consensus algorithms.

## Decision

**✅ Design is CONSTITUTION-COMPLIANT. Approved to proceed to design review, then coding.**

Next gate: Human review of `research.md`, `data-model.md`, `contracts/*`, `quickstart.md` — then `feature/orchestrator` branch may start.

## Sign-off

- [ ] Tech Lead review
- [ ] Security check (secrets/CORS)
- [x] Agent context updated via `.specify/scripts/bash/update-agent-context.sh opencode`
