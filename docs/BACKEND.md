# ⚙️ Backend Architecture

This document details the FastAPI backend – the brain of the AI Council.

## API Endpoints

### Health & Info
- `GET /health` – Check service status.
- `GET /models` – List all available models (fetched from LMArena).

### Council Orchestration
- `POST /council/query` – Submit a new query (main endpoint).
  - **Request Body**:
    ```json
    {
      "query": "What is quantum computing?",
      "models": ["claude", "chatgpt", "gemini", "deepseek"],
      "mode": "consensus",
      "depth": "detailed",
      "show_reasoning": true,
      "chairman": "claude"
    }
    ```
  - **Supported `models` values (canonical → LMArena internal, Sept 2026):**
    ```json
    ["claude", "chatgpt", "gemini", "deepseek", "qwen", "kimi"]
    // kimi defaults to kimi-k2.5; use "kimi-k3" alias for Kimi K3 preview
    // internal IDs: claude-sonnet-4-20250514, gpt-5-20250806, gemini-2.5-pro-20250617,
    //               deepseek-v3.1-20250715, qwen3-72b-20250728, kimi-k2.5-20250720 / kimi-k3-20250828
    ```
  - **Response**: Server-Sent Events (SSE) stream. MIME type `text/event-stream`.

- `GET /council/session/{session_id}` – Retrieve a past council session (JSON).
- `DELETE /council/session/{session_id}` – Delete a session.
- `GET /council/sessions` – List recent sessions (history). No auth required.

> **Auth:** No website login. Only **LMArena login** is required to obtain the `arena-auth-prod-v1` token (see `SETUP.md`). All `POST /auth/*` endpoints from Phase 1 are removed; sessions are stored anonymously (`user_id = null`) and shareable via URL. Rate limiting is per-IP.

## Orchestration Core (`orchestrator.py`)

### Main Function: `run_council(query, config)`

```python
async def run_council(query: str, config: CouncilConfig):
    # Step 1: Fan-Out
    tasks = []
    for model in config.models:
        tasks.append(send_to_lmarena(model, query, config.show_reasoning))
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Step 2: Handle failures
    valid_responses = [r for r in responses if not isinstance(r, Exception)]
    
    # Step 3: Synthesize
    synthesis_prompt = build_synthesis_prompt(query, valid_responses, config.mode)
    final_answer = await send_to_lmarena(config.chairman, synthesis_prompt, False)
    
    # Step 4: Extract structured data
    agreements, divergences, insights = parse_synthesis(final_answer)
    
    return CouncilResult(
        unified_answer=final_answer,
        agreements=agreements,
        divergences=divergences,
        unique_insights=insights,
        individual_responses=valid_responses
    )
```

### LMArenaBridge Client (`lmarena_client.py`)

```python
class LMArenaClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.session_id = str(uuid.uuid4())
    
    async def chat_completion(self, model: str, messages: list, stream: bool = True):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "session_id": self.session_id
        }
        # Uses httpx.AsyncClient with WebSocket upgrade for streaming
```

## Error Handling

- **Circuit Breaker**: If a model fails 3 times in a row, it is temporarily disabled (backoff).
- **Timeouts**: Each model has a 120-second timeout. If exceeded, the model is skipped.
- **Fallback**: If fewer than 2 models respond, the system returns an error.

## Logging

- Structured JSON logs using `structlog`.
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
- Logs include `session_id`, `model`, `latency`, and `status`.

## Security

- CORS configured to allow only the frontend origin.
- Rate limiting per IP (100 requests/hour for non-authenticated, 500/hour for authenticated).
- All environment secrets encrypted at rest.
