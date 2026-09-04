# LMArenaBridge — Integration stub

This directory holds local bridge config. For Phase 2 dev, the backend uses **mock** if `LMARENA_BRIDGE_URL` not reachable (see `app/services/lmarena_models.py` fallback and `app/services/lmarena_client.py` BridgeError → orchestrator marks model error).

To run real bridge:
1. Clone `https://github.com/lmarenabridge/lmarenabridge` into `./lmarenabridge/repo`
2. Copy `config.json.example` → `config.json` and fill `tokens` with `arena-auth-prod-v1` cookies (see `quickstart.md:35`)
3. Run via docker: `docker-compose --profile with-bridge up -d` (currently profile `with-bridge` not default, so normal `docker-compose up` won't require bridge)

Phase 1 validates via `scripts/test-bridge.sh` (optional, needs real token).
