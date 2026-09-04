# Module 2 — Backend Core: Health & Models (M, ~1d)

> **Depends on:** M1 (DB engine) + M0 (app stub) | **Delivers:** `GET /health` real ping + `GET /models` proxy with fallback, matching `contracts/openapi.yaml:24-67`

## File Manifest (to create/update)

```
backend/
├── app/
│   ├── main.py                 # update: include routers, CORS, slowapi, structlog, lifespan (create_tables)
│   ├── config.py               # already sqlite-adjusted
│   ├── db/base.py              # add get_db dep already, add create_tables helper for sqlite
│   └── routers/
│       ├── __init__.py
│       ├── health.py           # GET /health {status, version, bridge, db}
│       └── models.py           # GET /models proxy to LMARENA_BRIDGE_URL via httpx + static MODEL_MAPPINGS fallback
├── app/services/
│   ├── __init__.py
│   └── lmarena_models.py       # fallback static list + bridge proxy logic
├── app/core/
│   ├── __init__.py
│   └── logging.py              # structlog JSON processor (console)
└── tests/
    ├── test_health.py          # 200 ok, degraded, mocked bridge/db
    └── test_models.py          # mocked httpx, fallback, 502
```

## Endpoint Contracts

- `GET /health` per `contracts/openapi.yaml:24` → `{status: ok|degraded, version: 1.0.0, bridge: connected|disconnected, db: connected|disconnected}`. Logic: `SELECT 1` via `AsyncSession` (1s timeout) → `db`, `httpx GET {LMARENA_BRIDGE_URL}/models` 2s timeout → `bridge`. Both concurrent. Status `ok` only if both `connected` else `degraded` (never 500). structlog logs `health_check db=.. bridge=..`.
- `GET /models` per `:43-67` → `{"models": [{id, display_name, internal_id, available, latency_p50_ms}]}`. Logic: try bridge `GET {LMARENA_BRIDGE_URL}/v1/models` or `/models`, map to canonical `ModelId` enum. If bridge down/timeout → return static `MODEL_MAPPINGS` (claude/chatgpt/gemini/deepseek/qwen/kimi) with `available: true` + log warn, never 500 unless config missing. If bridge 5xx → 502 `BridgeError`.

## Static MODEL_MAPPINGS (fallback, mirrors docs/API-CONFIG.md:24)

```python
FALLBACK_MODELS = [
  {"id": "claude", "display_name": "Claude 3.5 Sonnet", "internal_id": "claude-3-5-sonnet-20241022", "available": True},
  {"id": "chatgpt", "display_name": "ChatGPT-4o", "internal_id": "gpt-4o-2024-08-06", "available": True},
  {"id": "gemini", "display_name": "Gemini 1.5 Pro", "internal_id": "gemini-1.5-pro", "available": True},
  {"id": "deepseek", "display_name": "DeepSeek V3", "internal_id": "deepseek-v3", "available": True},
  {"id": "qwen", "display_name": "Qwen 2.5 72B", "internal_id": "qwen-2.5-72b", "available": True},
  {"id": "kimi", "display_name": "Kimi", "internal_id": "moonshot-v1-8k", "available": True},
]
```

## Tests (exit gate)

- `test_health_ok` → mock DB ok + bridge ok → 200 ok.
- `test_health_degraded_db` → db timeout → 200 degraded.
- `test_models_fallback` → httpx MockTransport returns 500 → fallback list + 200 not 502.
- `test_models_bridge_success` → mock bridge JSON → maps correctly.
- CORS `allow_origins=[FRONTEND_ORIGIN]` preflight 200.
- `openapi.json` (/openapi.json) contains both paths.

## Approval Request

Approve this manifest? Next: update `app/main.py` + create `routers/health.py`/`models.py`/`services/lmarena_models.py`, wire logging, write tests.
