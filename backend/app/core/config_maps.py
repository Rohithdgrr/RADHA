MODEL_MAP: dict[str, str] = {
    # Sept 2026 latest — see docs/API-CONFIG.md
    "claude": "claude-sonnet-4-20250514",
    "chatgpt": "gpt-5-20250806",
    "gemini": "gemini-2.5-pro-20250617",
    "deepseek": "deepseek-v3.1-20250715",
    "qwen": "qwen3-72b-20250728",
    "kimi": "kimi-k2.5-20250720",  # Kimi K2.5 default
    "kimi-k3": "kimi-k3-20250828",  # Kimi K3 preview (alias)
    "kimi-k2.5": "kimi-k2.5-20250720",
    "grok": "grok-2-20250701",
    "llama": "llama-3.1-405b-20250715",
}


def to_internal(canonical: str) -> str:
    return MODEL_MAP.get(canonical, canonical)
