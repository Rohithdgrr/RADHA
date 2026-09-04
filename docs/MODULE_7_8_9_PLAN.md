# Modules 7-9 — Frontend (Next.js) — Plan (~4.5d)

> **Depends on:** M4 (SSE), M6 (auth), M0 (frontend scaffold) | **Delivers:** hero search + model selector + results (unified + cards + SSE) + history sidebar + download report, per `docs/UIUX.md`, `contracts/sse-events.md`

## Shared Stack (from docs/TECH-STACK.md FE)

`zustand@4.5.2` for council state, `react-hook-form@7`, `zod@3` for SSE validation, `ai@3.4.9` not required for Phase 1 (we use native `fetch` + `ReadableStream` for POST SSE — `EventSource` only GET, but `/council/query` is POST). Tailwind already configured.

## Module 7 — Foundation (M ~1.5d) — Already scaffolded, now wiring

**Files (update/create):**
```
frontend/
├── app/
│   ├── page.tsx (update from placeholder → real hero)
│   ├── layout.tsx (already)
│   ├── globals.css (already)
│   ├── council/[id]/page.tsx (replay)
│   └── auth/page.tsx (simple register/login)
├── components/
│   ├── HeroSearch.tsx
│   ├── ModelSelector.tsx (pill toggles 2..8 guard, horizontal)
│   ├── UnifiedAnswer.tsx (✨ + agree/diverge/insights)
│   ├── ModelCard.tsx (scrollable, header latency/status, reasoning <details>, confidence bar)
│   ├── HistorySidebar.tsx (GET /council/sessions, paginated)
│   └── ConfidenceBar.tsx
├── lib/
│   ├── api.ts (already — add fetchers: postCouncilQuery stream, getSession, getSessions, register, login)
│   ├── sse.ts (parse text/event-stream: split `event:` / `data:` → zod validate via contracts/council-query.json)
│   └── store.ts (zustand: query, models, mode, depth, showReasoning, chairman, status, responses, synthesis)
└── hooks/
    └── useCouncilStream.ts (useState + fetch POST + reader.getReader() + enqueue)
```

**Store shape (zustand):**
```ts
type CouncilState = {
  query: string; models: ModelId[]; mode: CouncilMode; depth: Depth; showReasoning: boolean; chairman: ModelId;
  status: "idle"|"streaming"|"done"|"error";
  sessionId: string | null;
  responses: Record<ModelId, ModelResponseRead & {status: "generating"|"done"|"error"}>;
  synthesis: string | null; agreements: string | null; divergences: string | null; insights: string[] | null;
  setQuery, toggleModel, startStream, etc.
}
```

**Page wiring:** `app/page.tsx` HeroSearch + ModelSelector below (pills cyan active per `UIUX.md:14`), mode/depth controls (Phase 1 only consensus enabled, others disabled + badge “Phase 2”). Submit → `useCouncilStream` POST → navigate to streaming view. `Ctrl+K` focuses search, `Esc` clears.

## Module 8 — Results Streaming (L ~2d)

**Component:** `hooks/useCouncilStream.ts`
```ts
async function* sseReader(res: Response) {
  const reader = res.body!.getReader(); decoder...
  while buffer contains "\n\n" split event: data: → dispatch
}
```
Handles 8 events: `model_start` → set card generating, `model_stream` → append delta (Phase 1 may not emit many, but handle), `model_done` → freeze card with latency/confidence, `synthesis_start` → show spinner top, `synthesis_stream` → stream unified answer, `done` → set sessionId + synthesis/agreements/.., `error` → toast.

**Cards:** `ModelCard` per `UIUX.md:38-48`: header `modelName • latency • status ✅/❌/...`, scrollable `final_answer`, collapsible `<details>` for `<reasoning>` if `showReasoning`, confidence progress bar (`width = confidence*100%` emerald). Horizontal scroll desktop (`flex overflow-x-auto snap`), stacked mobile (`grid grid-cols-1 lg:flex`).

**UnifiedAnswer:** top `✨ Answer` heading, synthesis markdown (simple render via `dangerouslySetInnerHTML` or lightweight `react-markdown` — keep zero-dep Phase 1 via `<pre>` wrapping), then sections `✅ Where models agree`, `⚠️ Where diverge`, `💡 Unique insights` bulleted.

**Replay:** `app/council/[id]/page.tsx` fetches `GET /council/session/{id}` via `lib/api.ts`, rehydrates store, renders same components non-streaming.

## Module 9 — History + Download (M ~1d)

- **HistorySidebar:** `GET /council/sessions?limit=20&offset=0` (JWT if logged → user’s, else anon). Stored in Zustand or local state, chronological. Click → push `/council/{id}`. Empty state “No history yet”.
- **Download Full Report:** button top of results → `GET /council/session/{id}` already fetched → generate client `Blob` (`report-{id}.html` with `<html><body><h1>Query...</h1><h2>Synthesis</h2>...<h2>Model: claude</h2><pre>...</pre></body></html>`). Also `.txt` fallback. No server export needed Phase 1.
- Keyboard `Ctrl+K/Esc/Enter` per `docs/USAGE.md:31`.

## Tests (frontend)

- `Jest/RTL`: ModelSelector enforces 2..8, toggle, Zustand, SSE parser validates `model_done` JSON shape.
- `Playwright` e2e with mocked SSE (no real backend): `test/e2e/council.spec.ts` hero submit → mocked `/council/query` returns 8 events → assert unified answer + 2 cards visible + history entry.

## Approval Request

Approve M7-9 frontend plan (zustand POST SSE + cards)? After approval, will update `frontend/` components + hooks + lib, then wire to backend via `NEXT_PUBLIC_API_URL`.

