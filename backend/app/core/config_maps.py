MODEL_MAP: dict[str, str] = {
    # Real arena.ai publicNames (scraped from arena.ai initialModels).
    # NOTE: arena rotates models frequently; if a name 404s, refresh from
    # GET http://localhost:8001/v1/models and update here.
    "claude": "claude-sonnet-4-20250514",
    "chatgpt": "gpt-5.5-instant",
    "gemini": "gemini-3-pro",
    "deepseek": "deepseek-v3.1-20250715",  # not currently listed on arena; 404s gracefully if selected
    "qwen": "qwen3-max-2025-09-23",
    "kimi": "kimi-k2.5-instant",  # Kimi K2.5 default
    "kimi-k3": "kimi-k3-20250828",  # not currently listed on arena; 404s gracefully if selected
    "kimi-k2.5": "kimi-k2.5-instant",
    "grok": "grok-4.20-multi-agent-beta-0309",
    "llama": "llama-3.1-405b-20250715",  # not currently listed on arena; 404s gracefully if selected
}


def to_internal(canonical: str) -> str:
    return MODEL_MAP.get(canonical, canonical)
