# 🔐 Environment Variables Reference

This is a comprehensive list of all environment variables used in the AI Council project.

## Backend (.env)

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `LMARENA_TOKEN` | ✅ | Your LMArena authentication cookie (base64). | `eyJhbGciOiJIUzI1NiIs...` |
| `LMARENA_BRIDGE_URL` | ✅ | URL where LMArenaBridge is hosted. | `http://localhost:8001` |
| `DATABASE_URL` | ✅ | PostgreSQL connection string. | `postgresql://admin:pass@db:5432/aicouncil` |
| `SECRET_KEY` | ✅ | Strong secret key for JWT. Min 32 characters. | `django-insecure-abc123...` |
| `BACKEND_PORT` | ❌ | Port for FastAPI. | `8000` |
| `FRONTEND_ORIGIN` | ❌ | CORS allowed origin. | `http://localhost:3000` |
| `ADMIN_PASSWORD` | ❌ | Password for admin dashboard (if used). | `supersecret` |
| `REDIS_URL` | ❌ | Redis cache URL (optional). | `redis://redis:6379/0` |
| `MAX_MODELS_PER_QUERY` | ❌ | Max models user can select. | `8` |
| `REQUEST_TIMEOUT` | ❌ | Timeout per model in seconds. | `120` |
| `LOG_LEVEL` | ❌ | Logging verbosity. | `INFO` |
| `SENTRY_DSN` | ❌ | Error tracking (Sentry). | `https://...@sentry.io/...` |

## Frontend (.env.local)

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL. | `http://localhost:8000` |
| `NEXT_PUBLIC_WEBSOCKET_URL` | ✅ | WebSocket endpoint. | `ws://localhost:8000/ws` |
| `NEXT_PUBLIC_GOOGLE_ANALYTICS` | ❌ | GA4 tracking ID. | `G-XXXXXXXXXX` |

## Docker Compose

The `docker-compose.yml` references these variables and also defines internal service names.

## Security Notes

- **Never commit `.env` to version control.** Add it to `.gitignore`.
- Rotate secrets (`SECRET_KEY`, `LMARENA_TOKEN`) periodically.
- Use a vault (e.g., HashiCorp Vault) in production environments.
