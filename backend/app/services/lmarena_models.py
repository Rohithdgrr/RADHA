import httpx
import structlog
from app.config import settings

log = structlog.get_logger()

FALLBACK_MODELS = [
    # Sept 2026 latest — display_name shows exact version
    {"id": "claude", "display_name": "Claude Sonnet 4 (20250514)", "internal_id": "claude-sonnet-4-20250514", "available": True, "latency_p50_ms": 1800},
    {"id": "chatgpt", "display_name": "ChatGPT-5 (20250806)", "internal_id": "gpt-5-20250806", "available": True, "latency_p50_ms": 1700},
    {"id": "gemini", "display_name": "Gemini 2.5 Pro (20250617)", "internal_id": "gemini-2.5-pro-20250617", "available": True, "latency_p50_ms": 2500},
    {"id": "deepseek", "display_name": "DeepSeek V3.1 (20250715)", "internal_id": "deepseek-v3.1-20250715", "available": True, "latency_p50_ms": 1600},
    {"id": "qwen", "display_name": "Qwen3 72B (20250728)", "internal_id": "qwen3-72b-20250728", "available": True, "latency_p50_ms": 1400},
    {"id": "kimi", "display_name": "Kimi K2.5 (20250720)", "internal_id": "kimi-k2.5-20250720", "available": True, "latency_p50_ms": 1500},
    {"id": "kimi-k3", "display_name": "Kimi K3 (20250828) Preview", "internal_id": "kimi-k3-20250828", "available": True, "latency_p50_ms": 1700},
]


async def fetch_models_from_bridge() -> list[dict] | None:
    url_candidates = [
        f"{settings.LMARENA_BRIDGE_URL}/v1/models",
        f"{settings.LMARENA_BRIDGE_URL}/models",
    ]
    headers = {"Authorization": f"Bearer {settings.LMARENA_TOKEN}"} if settings.LMARENA_TOKEN else {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in url_candidates:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # OpenAI style: {"data": [{"id": "..."}]} or {"models": [...]}
                    if isinstance(data, dict) and "data" in data:
                        models = []
                        for item in data["data"]:
                            mid = item.get("id", "")
                            # map internal to canonical if possible
                            canonical = _map_internal_to_canonical(mid)
                            models.append({
                                "id": canonical,
                                "display_name": item.get("display_name", mid),
                                "internal_id": mid,
                                "available": True,
                            })
                        if models:
                            return models
                    if isinstance(data, dict) and "models" in data:
                        return data["models"]
                    if isinstance(data, list):
                        return data
            except Exception as e:
                log.warning("bridge models fetch failed", url=url, error=str(e))
                continue
    return None


def _map_internal_to_canonical(internal: str) -> str:
    mapping = {
        "claude-sonnet-4-20250514": "claude",
        "claude-3-5-sonnet-20241022": "claude",
        "claude": "claude",
        "gpt-5-20250806": "chatgpt",
        "gpt-4o-2024-08-06": "chatgpt",
        "gpt-4o": "chatgpt",
        "chatgpt": "chatgpt",
        "gemini-2.5-pro-20250617": "gemini",
        "gemini-1.5-pro": "gemini",
        "gemini": "gemini",
        "deepseek-v3.1-20250715": "deepseek",
        "deepseek-v3": "deepseek",
        "deepseek": "deepseek",
        "qwen3-72b-20250728": "qwen",
        "qwen-2.5-72b": "qwen",
        "qwen": "qwen",
        "kimi-k2.5-20250720": "kimi",
        "kimi-k2.5": "kimi",
        "kimi-k3-20250828": "kimi-k3",
        "kimi-k3": "kimi-k3",
        "moonshot-v1-8k": "kimi",
        "kimi": "kimi",
    }
    return mapping.get(internal, internal.split("-")[0] if internal else "unknown")
