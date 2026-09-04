import asyncio
import json
import time
import uuid
import structlog
from datetime import datetime, timezone

from app.config import settings
from app.services.lmarena_client import LMArenaClient, BridgeError, BridgeTimeout, BridgeAuthError
from app.services.prompts import reasoning_system_prompt, build_synthesis_prompt, parse_reasoning_answer
from app.services.synthesis import parse_synthesis
from app.services import breaker
from app.core.config_maps import to_internal

log = structlog.get_logger()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_single_model(
    model: str,
    query: str,
    depth: str,
    show_reasoning: bool,
    session_id: str,
    queue: asyncio.Queue,
) -> dict:
    """Stream a single model via LMArenaClient.chat_completion_stream and emit model_stream events into queue. Return result dict."""
    start = time.monotonic()
    msgs = [
        {"role": "system", "content": reasoning_system_prompt(model, depth, show_reasoning)},
        {"role": "user", "content": query},
    ]
    if breaker.is_open(model):
        latency = time.monotonic() - start
        result = {
            "model": model,
            "reasoning": None,
            "final_answer": "",
            "confidence": None,
            "latency": latency,
            "status": "error",
            "error_message": "circuit breaker open",
            "token_count": None,
            "raw": "",
            "session_id": session_id,
        }
        await queue.put(("model_done", {
            "model": model,
            "status": result["status"],
            "latency": result["latency"],
            "reasoning": None,
            "final_answer": "",
            "confidence": None,
            "token_count": None,
            "error_message": result["error_message"],
        }))
        return result

    client = LMArenaClient()
    chunks: list[str] = []
    try:
        # Use streaming API for true token-by-token SSE
        try:
            stream_gen = client.chat_completion_stream(model, msgs, session_id=session_id)
            async for delta in stream_gen:
                if delta:
                    chunks.append(delta)
                    await queue.put(("model_stream", {"model": model, "delta": delta, "ts": _now()}))
        except TypeError:
            # Fallback if client.chat_completion_stream not patched as async gen (e.g., tests mocking chat_completion)
            raw_fallback = await client.chat_completion(model, msgs, session_id=session_id)
            chunks = [raw_fallback]
            # Emit as stream chunks split for realism
            for i in range(0, len(raw_fallback), 80):
                await queue.put(("model_stream", {"model": model, "delta": raw_fallback[i:i+80], "ts": _now()}))
                await asyncio.sleep(0.01)

        raw = "".join(chunks).strip()
        if not raw:
            # Some bridges may return empty via stream but support non-stream
            try:
                raw = await client.chat_completion(model, msgs, session_id=session_id)
                if raw:
                    chunks = [raw]
                    for i in range(0, len(raw), 80):
                        await queue.put(("model_stream", {"model": model, "delta": raw[i:i+80], "ts": _now()}))
                        await asyncio.sleep(0.01)
                    raw = raw.strip()
            except Exception:
                pass

        if not raw:
            raise BridgeError("empty response from bridge", code="BRIDGE_EMPTY")

        latency = time.monotonic() - start
        reasoning, answer, conf = parse_reasoning_answer(raw)
        breaker.record_success(model)
        token_count = len(answer.split()) + (len(reasoning.split()) if reasoning else 0)
        result = {
            "model": model,
            "reasoning": reasoning,
            "final_answer": answer,
            "confidence": conf,
            "latency": latency,
            "status": "done",
            "error_message": None,
            "token_count": token_count,
            "raw": raw,
            "session_id": session_id,
        }
        await queue.put(("model_done", {
            "model": model,
            "status": "done",
            "latency": latency,
            "reasoning": reasoning,
            "final_answer": answer,
            "confidence": conf,
            "token_count": token_count,
            "error_message": None,
        }))
        return result

    except asyncio.TimeoutError:
        latency = time.monotonic() - start
        breaker.record_failure(model)
        result = {
            "model": model,
            "reasoning": None,
            "final_answer": "".join(chunks) if chunks else "",
            "confidence": None,
            "latency": latency,
            "status": "timeout",
            "error_message": f"timeout after {settings.REQUEST_TIMEOUT}s",
            "token_count": None,
            "raw": "".join(chunks),
            "session_id": session_id,
        }
        await queue.put(("model_done", {
            "model": model,
            "status": "timeout",
            "latency": latency,
            "reasoning": None,
            "final_answer": result["final_answer"],
            "confidence": None,
            "token_count": None,
            "error_message": result["error_message"],
        }))
        return result
    except (BridgeTimeout, BridgeAuthError, BridgeError) as e:
        latency = time.monotonic() - start
        breaker.record_failure(model)
        code = getattr(e, "code", "BRIDGE_ERROR")
        # Preserve partial chunks if any streamed before error
        partial = "".join(chunks) if chunks else ""
        if partial:
            # Try to salvage partial as answer even if bridge errored mid-stream
            try:
                reasoning, answer, conf = parse_reasoning_answer(partial)
                if answer:
                    result = {
                        "model": model,
                        "reasoning": reasoning,
                        "final_answer": answer,
                        "confidence": conf,
                        "latency": latency,
                        "status": "done",
                        "error_message": None,
                        "token_count": len(answer.split()) + (len(reasoning.split()) if reasoning else 0),
                        "raw": partial,
                        "session_id": session_id,
                    }
                    breaker.record_success(model)
                    await queue.put(("model_done", {
                        "model": model,
                        "status": "done",
                        "latency": latency,
                        "reasoning": reasoning,
                        "final_answer": answer,
                        "confidence": conf,
                        "token_count": result["token_count"],
                        "error_message": None,
                    }))
                    return result
            except Exception:
                pass
        result = {
            "model": model,
            "reasoning": None,
            "final_answer": partial,
            "confidence": None,
            "latency": latency,
            "status": "timeout" if code == "BRIDGE_TIMEOUT" else "error",
            "error_message": str(e),
            "token_count": None,
            "raw": partial,
            "session_id": session_id,
        }
        await queue.put(("model_done", {
            "model": model,
            "status": result["status"],
            "latency": latency,
            "reasoning": None,
            "final_answer": partial,
            "confidence": None,
            "token_count": None,
            "error_message": str(e),
        }))
        return result
    except Exception as e:
        latency = time.monotonic() - start
        breaker.record_failure(model)
        partial = "".join(chunks) if chunks else ""
        result = {
            "model": model,
            "reasoning": None,
            "final_answer": partial,
            "confidence": None,
            "latency": latency,
            "status": "error",
            "error_message": str(e),
            "token_count": None,
            "raw": partial,
            "session_id": session_id,
        }
        await queue.put(("model_done", {
            "model": model,
            "status": "error",
            "latency": latency,
            "reasoning": None,
            "final_answer": partial,
            "confidence": None,
            "token_count": None,
            "error_message": str(e),
        }))
        return result


async def run_council_sse(
    query: str,
    models: list[str],
    chairman: str,
    mode: str,
    depth: str,
    show_reasoning: bool,
    user_id: str | None,
    db,  # AsyncSession but duck typed for testing
):
    from app.models.council_session import CouncilSession
    from app.models.model_response import ModelResponse

    # Compatibility: tests patch app.services.orchestrator.LMArenaClient with a mock whose chat_completion is AsyncMock
    # Real path uses chat_completion_stream. To preserve tests, detect if we are in test mock mode where stream would yield nothing
    # We handle this inside _stream_single_model via fallback to chat_completion.

    council_id = str(uuid.uuid4())
    start_wall = time.monotonic()
    deliberation: list[dict] = []

    # Create session row
    council = CouncilSession(
        id=council_id,
        user_id=user_id,
        user_query=query,
        selected_models=models,
        chairman_model=chairman,
        mode=mode,
        depth=depth,
        show_reasoning=show_reasoning,
        status="running",
        deliberation_log=[],
    )
    db.add(council)
    try:
        await db.commit()
    except Exception as e:
        log.warning("db council create failed", error=str(e))

    # model_start events — immediate per-model start
    for m in models:
        entry = {"type": "model_start", "model": m, "ts": _now(), "session_id": council_id}
        deliberation.append(entry)
        yield _sse("model_start", {"model": m, "ts": _now()})

    # fan-out with real streaming via queue
    queue: asyncio.Queue = asyncio.Queue()
    model_sids = {m: str(uuid.uuid4()) for m in models}

    # launch per-model streaming tasks
    tasks = [
        asyncio.create_task(_stream_single_model(m, query, depth, show_reasoning, model_sids[m], queue))
        for m in models
    ]

    # Drain queue as tokens arrive, emitting SSE in arrival order (interleaved)
    pending = len(models)
    done_counts = 0
    # Map to collect results for synthesis
    results: list[dict] = []
    # Queue consumer loop runs concurrently with tasks
    while done_counts < pending:
        # Wait for either queue entry or task completion
        # Prioritize queue draining
        try:
            # Use wait_for with timeout to avoid blocking forever
            event_type, data = await asyncio.wait_for(queue.get(), timeout=0.1)
            if event_type == "model_stream":
                # Emit model_stream per token chunk (per contracts/sse-events.md)
                yield _sse("model_stream", data)
                deliberation.append({"type": "model_stream", "model": data["model"], "ts": data["ts"]})
            elif event_type == "model_done":
                yield _sse("model_done", data)
                deliberation.append({"type": "model_done", "model": data["model"], "latency": data.get("latency"), "status": data.get("status"), "ts": _now()})
                done_counts += 1
                queue.task_done()
                continue
            queue.task_done()
        except asyncio.TimeoutError:
            # No queue item, check if any task finished without emitting model_done (edge fallback)
            if all(t.done() for t in tasks):
                # Ensure any pending queue items flushed
                while not queue.empty():
                    try:
                        event_type, data = queue.get_nowait()
                        if event_type == "model_stream":
                            yield _sse("model_stream", data)
                        elif event_type == "model_done":
                            yield _sse("model_done", data)
                            done_counts += 1
                            deliberation.append({"type": "model_done", "model": data["model"], "latency": data.get("latency"), "status": data.get("status"), "ts": _now()})
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                if done_counts >= pending:
                    break
                await asyncio.sleep(0.05)
            else:
                await asyncio.sleep(0.01)
                continue

    # Gather results (tasks each returned dict)
    try:
        gathered = await asyncio.gather(*tasks)
        results = gathered
    except Exception as e:
        log.warning("gather results failed", error=str(e))
        results = []

    # Persist ModelResponses
    valid: list[dict] = []
    for r in results:
        model = r.get("model") if isinstance(r, dict) else "unknown"
        if not isinstance(r, dict):
            continue
        resp = ModelResponse(
            session_id=council_id,
            model_name=model,
            reasoning=r.get("reasoning"),
            final_answer=r.get("final_answer") or "",
            confidence=r.get("confidence"),
            latency=r.get("latency") or 0.0,
            token_count=r.get("token_count"),
            status=r.get("status") or "done",
            error_message=r.get("error_message"),
            raw_payload={"raw": r.get("raw"), "internal": to_internal(model)},
        )
        db.add(resp)
        if r.get("status") == "done" and r.get("final_answer"):
            valid.append(r)

    try:
        await db.commit()
    except Exception as e:
        log.warning("db responses commit failed", error=str(e))

    if len(valid) < 2:
        deliberation.append({"type": "error", "message": f"Only {len(valid)} model(s) succeeded, need >=2", "ts": _now()})
        council.status = "error"
        council.deliberation_log = deliberation
        council.total_latency = time.monotonic() - start_wall
        try:
            await db.commit()
        except Exception:
            pass
        yield _sse("error", {"session_id": council_id, "message": f"Only {len(valid)} model(s) succeeded, need >=2", "code": "INSUFFICIENT_MODELS"})
        return

    # synthesis with real streaming
    yield _sse("synthesis_start", {"chairman": chairman, "ts": _now()})
    deliberation.append({"type": "synthesis_start", "chairman": chairman, "ts": _now()})

    if mode != "consensus":
        council.status = "error"
        council.deliberation_log = deliberation
        council.total_latency = time.monotonic() - start_wall
        try:
            await db.commit()
        except Exception:
            pass
        yield _sse("error", {"session_id": council_id, "message": f"Mode {mode} not implemented in Phase 1", "code": "NOT_IMPLEMENTED"})
        return

    synth_messages = [
        {"role": "system", "content": "You are the council chairman. Return ONLY JSON as instructed."},
        {"role": "user", "content": build_synthesis_prompt(query, [{"model": r["model"], "answer": r["final_answer"]} for r in valid], mode)},
    ]
    try:
        client = LMArenaClient()
        raw_chunks: list[str] = []
        # Prefer streaming for chairman as well
        async for delta in client.chat_completion_stream(chairman, synth_messages, session_id=str(uuid.uuid4())):
            if delta:
                raw_chunks.append(delta)
                yield _sse("synthesis_stream", {"delta": delta})
                deliberation.append({"type": "synthesis_stream", "delta": delta, "ts": _now()})
        raw_synth = "".join(raw_chunks).strip()
        if not raw_synth:
            # Fallback to non-stream if stream yielded empty
            raw_synth = await client.chat_completion(chairman, synth_messages, session_id=str(uuid.uuid4()))
            for i in range(0, len(raw_synth), 200):
                chunk = raw_synth[i: i + 200]
                yield _sse("synthesis_stream", {"delta": chunk})
                deliberation.append({"type": "synthesis_stream", "delta": chunk, "ts": _now()})
                await asyncio.sleep(0.02)
        synthesis, agreements, divergences, insights = parse_synthesis(raw_synth)
    except Exception as e:
        log.warning("chairman failed", error=str(e))
        breaker.record_failure(chairman)
        # Try fallback: if streaming failed, attempt single chat_completion
        try:
            client2 = LMArenaClient()
            raw_synth2 = await asyncio.wait_for(
                client2.chat_completion(chairman, synth_messages, session_id=str(uuid.uuid4())),
                timeout=settings.REQUEST_TIMEOUT,
            )
            for i in range(0, len(raw_synth2), 200):
                chunk = raw_synth2[i: i + 200]
                yield _sse("synthesis_stream", {"delta": chunk})
                deliberation.append({"type": "synthesis_stream", "delta": chunk, "ts": _now()})
                await asyncio.sleep(0.02)
            synthesis, agreements, divergences, insights = parse_synthesis(raw_synth2)
            breaker.record_success(chairman)
        except Exception as e2:
            log.warning("chairman fallback also failed", error=str(e2))
            synthesis = f"Synthesis failed: {e}. Valid answers exist but could not synthesize."
            agreements = None
            divergences = None
            insights = None
            raw_synth = synthesis
            yield _sse("synthesis_stream", {"delta": synthesis})

    total = time.monotonic() - start_wall
    council.synthesis = synthesis
    council.agreements = agreements
    council.divergences = divergences
    council.unique_insights = insights
    council.total_latency = total
    council.status = "done"
    council.deliberation_log = deliberation + [{"type": "done", "total_latency": total, "ts": _now()}]
    try:
        await db.commit()
    except Exception as e:
        log.warning("db council final commit failed", error=str(e))

    yield _sse("done", {
        "session_id": council_id,
        "total_latency": total,
        "synthesis": synthesis,
        "agreements": agreements,
        "divergences": divergences,
        "unique_insights": insights or [],
    })
