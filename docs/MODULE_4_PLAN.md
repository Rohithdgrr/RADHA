# Module 4 — Orchestrator: Fan-Out / Fan-In + SSE (XL ~3.5d)

> **Depends on:** M1 (DB), M2 (health), M3 (client+prompts) | **Delivers:** `POST /council/query` SSE per `contracts/openapi.yaml:69-136` + `contracts/sse-events.md`, `GET /council/session/{id}` + `GET /council/sessions` + `DELETE`

## File Manifest

```
backend/
├── app/
│   ├── routers/
│   │   ├── council.py      # POST /council/query (SSE StreamingResponse), GET /council/session/{id}, DELETE, GET /council/sessions
│   │   └── sessions.py     # alternative if split (optional)
│   ├── services/
│   │   ├── orchestrator.py # run_council core: gather, circuit breaker, persist
│   │   ├── synthesis.py    # (M5 hook) placeholder that orchestrator calls — will be fleshed in M5
│   │   └── breaker.py      # pybreaker CircuitBreaker per model (3 failures → open 5min) or simple in-memory
│   └── schemas/council.py  # already exists — add CouncilSessionRead with responses
├── tests/
│   ├── test_orchestrator.py # mocked client, 2-mock success, timeout, <2 failure→error event, breaker open
│   └── test_council_api.py  # POST /council/query SSE wire format, GET session, pagination
```

## Endpoint Contracts (contracts/openapi.yaml + sse-events.md)

- `POST /council/query` body `CouncilQueryRequest` (query 1..10000, models 2..8 unique, chairman in allow-list else 422, mode/depth enums). Auth optional (Bearer JWT — if present, tie `user_id` else NULL). Rate-limited via `slowapi` (100/hr anon, 500/hr auth — in-memory for Phase 1, Redis if `REDIS_URL` set). Returns `text/event-stream` with headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Content-Type: text/event-stream`, `Connection: keep-alive`. Event sequence per `contracts/sse-events.md:24`:
  1. `event: model_start` ×N (immediately after DB session create, status=running)
  2. `event: model_stream` *interleaved* (throttled 20ms, optional — may skip to just `model_done` for Phase 1 simplicity, but spec allows both)
  3. `event: model_done` ×N (per model latency/confidence/reasoning/final_answer)
  4. `event: synthesis_start` (once, after gather)
  5. `event: synthesis_stream` ×M (stream chairman tokens)
  6. `event: done` (terminal success with `session_id, synthesis, agreements, divergences, unique_insights, total_latency`)
  7. On error `<2 models` → `event: error` instead of `done` (no synthesis). `event: error` payload `{session_id, message, code: INSUFFICIENT_MODELS|BRIDGE_TIMEOUT}`.

- `GET /council/session/{session_id}` → `CouncilSessionRead` with `responses` array, deliberation_log. 404 if not found.
- `DELETE /council/session/{session_id}` → 204 if owner (or anon if no user_id? Decided 403 unless JWT owner matches, else anon deletable by anyone with id? For Phase 1: anon deletable, auth-owned requires owner — per `contracts/openapi.yaml:183` 403). 403/404 per spec.
- `GET /council/sessions?limit&offset&user_id` → paginated `{"total": int, "items": [...]}` filtered by `user_id` if auth matches else only caller’s sessions (anon → empty unless explicit id). Privacy: anon sessions not enumerated.

## Orchestrator Logic (app/services/orchestrator.py)

```python
# Pseudocode matching docs/BACKEND.md:39-63 but with SSE+breaker+DB

async def call_single_model(model, query, depth, show_reasoning, session_id):
    start = time.monotonic()
    msgs = [
      {"role":"system","content": reasoning_system_prompt(model, depth, show_reasoning)},
      {"role":"user","content": query},
    ]
    try:
        # check circuit breaker per model
        if breaker.is_open(model): raise BridgeError("circuit open")
        raw = await client.chat_completion(model, msgs, session_id=session_id)  # via M3
        latency = time.monotonic()-start
        reasoning, answer, conf = parse_reasoning_answer(raw)
        breaker.record_success(model)
        return {"model":model,"reasoning":reasoning,"final_answer":answer,"confidence":conf,"latency":latency,"status":"done","raw":raw}
    except asyncio.TimeoutError / BridgeTimeout -> status timeout, latency, breaker.record_failure
    except Exception -> status error, breaker.record_failure

async def run_council_sse(query, models, chairman, mode, depth, show_reasoning, user_id):
    council_id = str(uuid4())
    # create DB row status=running, deliberation_log=[]
    # emit model_start for each
    # gather via asyncio.gather(*tasks, return_exceptions=True) with asyncio.wait_for(REQUEST_TIMEOUT) per model + Semaphore(8)
    # for each result emit model_done (persist ModelResponse row per model via same transaction)
    # if len(valid) <2: emit error, update session status=error, return
    # else: emit synthesis_start, call chairman via client.chat_completion(chairman, synthesis_prompt) streaming → emit synthesis_stream deltas, parse via parse_synthesis (M5) → update council_sessions {synthesis,agreements,divergences,unique_insights,status=done,total_latency}
    # emit done
    # also persist deliberation_log only start/done + synthesis_start/done + errors (not every delta) per data-model §5
```

- **Session isolation:** `session_id = str(uuid4())` per model per request (research R-03). Not reused.
- **Timeout:** per-model `asyncio.wait_for(REQUEST_TIMEOUT)` (default 120s per settings).
- **Circuit breaker:** `pybreaker.CircuitBreaker(fail_max=3, reset_timeout=300)` per model stored in `app/services/breaker.py` dict. Open → short-circuit to `status=error` immediately, logs `circuit_open`.
- **Persistence:** `CouncilSession` created before fan-out (running), each `ModelResponse` inserted after model_done, synthesis updates row at end. `deliberation_log` appended in-memory then JSON dumped once at end (to avoid row locks per event).

## SSE StreamingResponse

`council.py`:

```python
from fastapi.responses import StreamingResponse
import json

async def event_gen():
    yield sse("model_start", {"model":m,"ts":now()})
    ...
def sse(event, data): return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.post("/query")
async def council_query(body: CouncilQueryRequest, request: Request, db: AsyncSession=Depends(get_db), user=Depends(optional_auth)):
    return StreamingResponse(run_council_sse(...), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no","Connection":"keep-alive"})
```

Validation 422 via Pydantic, 429 via slowapi.

## Tests

- `test_orchestrator_two_success` — mock `chat_completion` returns 2 answers + chairman JSON → assert `model_done`×2 + `synthesis_start` + `done` with synthesis parsed.
- `test_orchestrator_insufficient_models` — 0/1 success → `error` event code `INSUFFICIENT_MODELS`, status error, no synthesis.
- `test_orchestrator_timeout_partial` — one model timeout → `status=timeout` but if 2 successes → still `done`.
- `test_circuit_breaker_opens` — fail 3× same model → 4th call short-circuits.
- `test_council_api_sse_wire` — `POST /council/query` via `AsyncClient` streaming response `iter_text()` parse `event: ...` lines.
- `test_session_crud` — after `done`, `GET /council/session/{id}` returns responses, `GET /council/sessions?user_id=...` paginated, `DELETE` 403 vs 204.

## Approval Request

Approve this orchestration SSE contract? Next: write `breaker.py`, `orchestrator.py` (with synthesis placeholder), `council.py`, tests.
