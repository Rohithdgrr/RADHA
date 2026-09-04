# Module 3 — LMArenaBridge Client (Streaming Core, L ~2d)

> **Depends on:** M2 (bridge proxy) | **Delivers:** `app/services/lmarena_client.py` streaming async generator + prompt templates, per `research.md` R-01/R-03/R-05, `docs/BACKEND.md:65-86` corrected.

## File Manifest

```
backend/
├── app/
│   ├── services/
│   │   ├── lmarena_client.py   # LMArenaClient class: chat_completion streaming + non-stream
│   │   └── prompts.py          # reasoning system prompt + depth variants + synthesis prompt builder (M5 hook)
│   └── core/
│       └── config_maps.py      # MODEL_MAPPINGS: canonical → internal_id
└── tests/
    ├── test_lmarena_client.py  # httpx.MockTransport streaming, timeout, 401, session_id uniqueness
    └── test_prompts.py         # <reasoning> tags, depth variants
```

## Interface (approved shape, matches BACKEND.md fix)

```python
class LMArenaClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = base_url or settings.LMARENA_BRIDGE_URL
        self.token = token or settings.LMARENA_TOKEN

    async def chat_completion_stream(
        self,
        model: ModelId,
        messages: list[dict],  # [{"role":"system","content":...},{"role":"user","content":...}]
        session_id: str | None = None,  # generated uuid4 if None → per-request isolation per research R-03
        timeout: float = 120.0,
    ) -> AsyncGenerator[str, None]:  # yields delta strings (OpenAI choices[0].delta.content)
        # POST {LMARENA_BRIDGE_URL}/v1/chat/completions {model: internal_id, messages, stream: true, session_id}
        # header Authorization: Bearer <token>
        # parse text/event-stream: lines starting data: {choices:[{delta:{content}}]} or bridge custom {"delta":".."} or {"content":".."}
        # raises BridgeTimeout, BridgeAuthError, BridgeError

    async def chat_completion(
        self, model: ModelId, messages: list[dict], session_id: str | None = None
    ) -> str:  # collects stream -> full string (for Chairman fallback)
        return "".join([d async for d in self.chat_completion_stream(...)])
```

## MODEL_MAPPINGS

`app/core/config_maps.py`:
```python
MODEL_MAP = {
  "claude": "claude-3-5-sonnet-20241022",
  "chatgpt": "gpt-4o-2024-08-06",
  "gemini": "gemini-1.5-pro",
  "deepseek": "deepseek-v3",
  "qwen": "qwen-2.5-72b",
  "kimi": "moonshot-v1-8k",
  "grok": "grok-2",
  "llama": "llama-3.1-405b",
}
```
Env can override via `MODEL_MAPPINGS_YAML` file if needed; fallback to key==value.

## Prompts (research R-05 decision)

`prompts.py: reasoning_system_prompt(depth, show_reasoning)`:

- **If show_reasoning True:** `You are Council member {model}. Think step by step but output EXACTLY:\n<reasoning>your private chain-of-thought</reasoning>\n<answer>final answer for user</answer>\nAlso at end include line "Confidence: XX%" (0-100). Be concise per depth.`
  - `depth=brief` → add `Keep <answer> to 80-120 words.`
  - `standard` → `150-250 words.`
  - `detailed` → `300-500 words, with bullet points and citations if helpful.`
- **If show_reasoning False:** no XML, just answer + confidence.

Confidence parsed as `r"Confidence:\s*(\d{1,3})%"` → normalized 0-1 else None.
Reasoning extracted via `re.search(r"<reasoning>(.*?)</reasoning>", dotall, re.IGNORECASE)` else None; answer via `<answer>` or fallback to full text minus reasoning.

Synthesis prompt (M5 hook): `build_synthesis_prompt(query, responses, mode)` same file.

## Streaming Parser Details

Handle 3 shapes seen in bridge variants:
1. OpenAI: `data: {"choices":[{"delta":{"content":"Hello"}}]}` → `delta.content`
2. Custom: `data: {"delta":"Hello"}` or `{"content":"Hello"}` or `{"text":"Hello"}`
3. Final: `data: [DONE]` → stop

Timeout 120s via `httpx.AsyncClient(timeout=httpx.Timeout(120))`, `asyncio.wait_for` optional.

Errors: map `httpx.ConnectError` → `BridgeError(502, BRIDGE_UNAVAILABLE)`, `401` → `BridgeAuthError`, `Timeout` → `BridgeTimeout`.

## Tests

- `test_chat_completion_stream_mocked` — MockTransport emits 3 SSE chunks OpenAI style + [DONE] → assert collected `Hello world`.
- `test_session_id_unique` — two calls generate different uuid4.
- `test_internal_mapping` — canonical `claude` maps to `claude-3-5-sonnet...` in request payload.
- `test_timeout` — MockTransport sleep > timeout raises.
- `test_prompts_have_tags` — every `show_reasoning=True` prompt contains `<reasoning>`.

## Approval Request

Approve this interface? Next: write `lmarena_client.py`, `prompts.py`, `config_maps.py`, tests.
