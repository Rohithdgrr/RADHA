# SSE Event Contracts — POST /council/query → text/event-stream

> **Transport:** `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`
> **Reconnection:** Client should use `Last-Event-ID` not needed Phase 1 (no resume); on disconnect, refetch `GET /council/session/{id}` for final state.
> **Related:** `research.md` U-04 decision SSE canonical, `contracts/openapi.yaml` SSEEvent schemas

## Wire Format

```
event: <event_type>
data: <JSON>
id: <optional monotonic>

event: model_start
data: {"model":"claude","ts":"2026-09-04T00:00:00.000Z"}

```

Every event MUST be `event: <type>\ndata: <json>\n\n`. `data` is always JSON string (never bare text).

## Event Catalog

| # | event | when | data shape | frontend action |
|---|-------|------|------------|-----------------|
| 1 | `model_start` | per model at fan-out start | `{model: ModelId, ts}` | Show spinner card |
| 2 | `model_stream` | per token chunk (optional throttled 20ms) | `{model, delta: string, ts}` | Append to card stream |
| 3 | `model_done` | per model success/fail | `{model, status: done|error|timeout, latency, reasoning?, final_answer, confidence?, token_count?, error_message?}` | Freeze card, show latency/confidence |
| 4 | `critique_done` | per critique (debate mode only) | `{reviewer, reviewee, critique: string, score: 0-10, ts}` | Append critique section |
| 5 | `synthesis_start` | after all `model_done` | `{chairman: ModelId, ts}` | Show unified answer spinner |
| 6 | `synthesis_stream` | per chairman token | `{delta: string}` | Stream unified answer |
| 7 | `done` | terminal success | `{session_id: UUID, total_latency, synthesis, agreements?, divergences?, unique_insights?}` | Persist session_id, enable Download Report |
| 8 | `error` | terminal error (<2 models succeeded) | `{session_id, message, code: "INSUFFICIENT_MODELS" | "BRIDGE_TIMEOUT"}` | Show error toast + retry |

## Sequence (Happy Path)

```
-> model_start (claude)
-> model_start (chatgpt)
-> model_start (gemini)
-> model_stream x N (interleaved, order non-deterministic due to gather)
-> model_done (claude)
-> model_done (gemini)
-> model_done (chatgpt)
-> synthesis_start
-> synthesis_stream x M
-> done
```

## Error Sequences

- **Single model timeout:** `model_done {status:timeout}` then continue; if ≥2 successes still go to synthesis.
- **Insufficient models:** `error {message: "Only 1 model succeeded, need ≥2"}`, no synthesis.
- **Bridge 502:** `error {code: BRIDGE_TIMEOUT}`.

## Frontend Handling (Vercel AI SDK / EventSource)

```ts
const es = new EventSource(`/api/council/query`); // or fetch + ReadableStream for POST
es.addEventListener("model_done", (e) => {
  const d = JSON.parse(e.data) as ModelDoneEvent; // validate with zod from council-query.json
  setCards(prev => prev.map(c => c.model===d.model ? {...c, ...d} : c));
});
es.addEventListener("done", (e) => {
  const {session_id} = JSON.parse(e.data);
  history.push(`/council/${session_id}`);
  es.close();
});
es.addEventListener("error", (e) => { showToast(JSON.parse(e.data).message); es.close(); });
```

## Validation

- Every `data` JSON validated with `zod` against `contracts/council-query.json` / `sse-events.md` shapes before render.
- `confidence` normalized 0-1 (bridge may send 0-100 → divide by 100).
- `reasoning` may be null if parser failed — show warning.
