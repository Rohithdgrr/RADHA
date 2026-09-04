# 📡 API Configuration Guide

This document explains how to configure the backend API for your environment.

## Environment Variables (`.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LMARENA_TOKEN` | Your base64-encoded LMArena auth token. | (required) |
| `LMARENA_BRIDGE_URL` | URL of the LMArenaBridge service. | `http://localhost:8001` |
| `DATABASE_URL` | PostgreSQL connection string. | `postgresql://...` |
| `BACKEND_PORT` | Port for FastAPI. | `8000` |
| `FRONTEND_ORIGIN` | Allowed frontend URL for CORS. | `http://localhost:3000` |
| `SECRET_KEY` | Used for JWT signing. Must be 32+ characters. | (required) |
| `ADMIN_PASSWORD` | Password for admin dashboard (if enabled). | (required) |
| `REDIS_URL` | Optional Redis cache URL. | (optional) |
| `MAX_MODELS_PER_QUERY` | Maximum models user can select. | `8` |
| `REQUEST_TIMEOUT` | Model response timeout in seconds. | `120` |

## Model Mappings (updated 2026-09 — latest versions)

LMArena uses internal model IDs. Configure `MODEL_MAPPINGS` in `config.yaml`:

```yaml
model_mappings:
  # Latest stable versions (Sept 2026) — LMArena exposes these internal IDs
  claude: "claude-sonnet-4-20250514"      # also available: claude-opus-4.5, claude-sonnet-4.5
  chatgpt: "gpt-5-20250806"               # also: gpt-5-mini, gpt-4o-2024-08-06 (legacy)
  gemini: "gemini-2.5-pro-20250617"        # also: gemini-2.5-flash
  deepseek: "deepseek-v3.1-20250715"      # also: deepseek-r1, deepseek-v3-0324
  qwen: "qwen3-72b-20250728"               # also: qwen2.5-72b (legacy), qwen3-32b
  kimi: "kimi-k2.5-20250720"               # Kimi K2.5 (latest)
  kimi-k3: "kimi-k3-20250828"              # Kimi K3 (preview) — alias for kimi
  # Optional aliases — LMArena may expose versioned IDs directly:
  # kimi-k2.5: "kimi-k2.5"  → same as kimi
```

> **Kimi versions:** `kimi-k2.5` (K2.5, Jul 2025, 128k, strong RAG) and `kimi-k3` (K3, Aug 2025, 256k, reasoning) are both supported — `kimi` defaults to `kimi-k2.5` for stability; select `kimi-k3` explicitly for longest context. Legacy `moonshot-v1-8k` still works but is deprecated.

Available via `GET /models` — each entry shows `id` (canonical), `display_name`, `internal_id` (exact LMArena version), `available`.

## LMArenaBridge Configuration

LMArenaBridge has its own `config.json`:

```json
{
  "tokens": ["base64-token-1", "base64-token-2"],
  "session_pool": {
    "claude": ["session_a", "session_b"],
    "chatgpt": ["session_c"]
  },
  "mode": "direct_chat",
  "file_bed_enabled": false,
  "websocket_port": 8001
}
```

- **Tokens**: You can provide multiple tokens for load balancing.
- **Session Pool**: Assign different session IDs to different models to prevent context interference.

## Admin Dashboard (Future)

In Phase 3, an admin endpoint will be available at `/admin` with:
- View all running sessions.
- Manually expire tokens.
- View real-time logs.
- Set global rate limits.

## Swagger Documentation

Once the backend is running, access interactive API docs at:
- `http://localhost:8000/docs` – Swagger UI.
- `http://localhost:8000/redoc` – ReDoc.

## Testing the API with cURL

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/models

# Submit query (SSE stream)
curl -N -X POST http://localhost:8000/council/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is AI?","models":["claude","chatgpt"],"mode":"consensus"}'
```
