# Module 5 — Chairman Synthesis & Parsing (M, ~1d)

> **Depends on:** M4 (orchestrator) | **Delivers:** `app/services/synthesis.py` JSON-first + markdown fallback, depth-aware, `parse_synthesis` + `build_synthesis_prompt` already in `prompts.py`

## Status — Already Implemented in M4

This module was implemented as part of M4 to keep streaming cohesive:

- `app/services/prompts.py:build_synthesis_prompt` builds chairman prompt with `{synthesis, agreements, divergences, unique_insights}` JSON instruction
- `app/services/synthesis.py:parse_synthesis` tries `json.loads` (handles ```json fences) → fallback regex for markdown headings `## Agreements` etc → returns `(synthesis, agreements, divergences, insights)`
- `app/services/orchestrator.py` calls chairman via `LMArenaClient.chat_completion`, emits `synthesis_stream` chunked 200 chars with throttle, then `parse_synthesis` and persists to `CouncilSession`.

## Remaining Tasks (if any)

- Depth selector already in `reasoning_system_prompt`; synthesis depth may be refined (brief→ short, detailed→ longer). Already uses `build_synthesis_prompt` which respects mode.
- Non-consensus modes (`debate`, `specialist`, `weighted`) still emit `error` event code `NOT_IMPLEMENTED` per `orchestrator.py:130` — approved deferral per `design-notes.md` (501 analog via SSE error).

## Tests (exit gate already covered)

- `tests/test_orchestrator.py` asserts `synthesis == Unified answer` via JSON synthesis path.
- Additional unit `tests/test_synthesis.py` will be added to cover markdown fallback + fence handling.

## Approval Request

Consider M5 code-complete (reusing M4 artifacts). Approve to proceed to M6 Auth, or request extraction to separate tests?
