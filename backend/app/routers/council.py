from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.schemas.council import CouncilQueryRequest
from app.models.council_session import CouncilSession
from app.models.model_response import ModelResponse
from app.services.orchestrator import run_council_sse

router = APIRouter()


def _optional_auth(request: Request) -> str | None:
    # Phase 1: try Bearer JWT, but if absent/invalid → None (anon). Real auth in Module 6.
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        # minimal decode without verify? For Phase 1 just parse via python-jose if available else treat as user_id placeholder
        # We expose hook for Module 6 to override dependency.
        # Return token as placeholder user_id if looks like jwt (has two dots) else None
        # Proper verify will be added in auth router.
        try:
            from app.auth.security import decode_token_optional
            payload = decode_token_optional(token)
            if payload and "sub" in payload:
                # sub is email, need to lookup user id
                return payload.get("uid") or payload.get("sub")
        except Exception:
            pass
        # fallback: if token is raw user id (tests)
        if len(token) > 5 and "." not in token:
            return None
    return None


@router.post("/query")
async def council_query(
    body: CouncilQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # validate chairman in allow-list (pydantic already) — extra check: if not in models list, still allow if valid ModelId? Blueprint says must be in models or allow-list — we allow any ModelId.
    # rate limit placeholder: skip for Phase 1 (slowapi added in main if needed)
    user_id = _optional_auth(request)

    # Mode check early: if not consensus, orchestrator will emit error event, but we could 501 here.
    # Keep SSE style: let orchestrator emit error.

    async def gen():
        async for chunk in run_council_sse(
            query=body.query,
            models=body.models,
            chairman=body.chairman,
            mode=body.mode,
            depth=body.depth,
            show_reasoning=body.show_reasoning,
            user_id=user_id,
            db=db,
        ):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(CouncilSession).options(selectinload(CouncilSession.responses)).where(CouncilSession.id == session_id)
    )
    sess = q.scalars().first()
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    # map to schema shape
    return {
        "id": sess.id,
        "user_id": sess.user_id,
        "user_query": sess.user_query,
        "selected_models": sess.selected_models,
        "chairman_model": sess.chairman_model,
        "mode": sess.mode,
        "depth": sess.depth,
        "show_reasoning": sess.show_reasoning,
        "synthesis": sess.synthesis,
        "agreements": sess.agreements,
        "divergences": sess.divergences,
        "unique_insights": sess.unique_insights,
        "deliberation_log": sess.deliberation_log,
        "total_latency": sess.total_latency,
        "status": sess.status,
        "created_at": sess.created_at.isoformat() if sess.created_at else None,
        "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
        "responses": [
            {
                "id": r.id,
                "session_id": r.session_id,
                "model_name": r.model_name,
                "reasoning": r.reasoning,
                "final_answer": r.final_answer,
                "confidence": r.confidence,
                "latency": r.latency,
                "token_count": r.token_count,
                "status": r.status,
                "error_message": r.error_message,
                "critique": r.critique,
                "critique_score": r.critique_score,
                "raw_payload": r.raw_payload,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in sess.responses
        ],
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(CouncilSession).where(CouncilSession.id == session_id))
    sess = q.scalars().first()
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    # auth check: if sess.user_id not None, require owner
    user_id = _optional_auth(request)
    if sess.user_id is not None and sess.user_id != user_id:
        # allow if anon delete? For auth-owned, require match
        # Phase 1: if Authorization missing and session owned → 403
        raise HTTPException(status_code=403, detail="not owner")
    await db.delete(sess)
    await db.commit()
    return {"deleted": session_id}


@router.get("/sessions")
async def list_sessions(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(50, limit))
    # privacy: if user_id filter provided, only return if caller matches or anon none? For Phase 1 simple filter
    caller_id = _optional_auth(request)
    # Build query
    base_q = select(CouncilSession).options(selectinload(CouncilSession.responses)).order_by(CouncilSession.created_at.desc())
    if user_id:
        # if filter specifies user_id, enforce caller matches that id else 403
        if caller_id and caller_id != user_id:
            raise HTTPException(status_code=403, detail="cannot list other user's sessions")
        if not caller_id and user_id:
            # anon cannot list someone else's
            raise HTTPException(status_code=403, detail="auth required")
        base_q = base_q.where(CouncilSession.user_id == user_id)
    else:
        # no filter: if authed, show own; if anon, show anon sessions (user_id NULL) limit? For privacy, anon without filter gets anon sessions (recent)
        if caller_id:
            base_q = base_q.where(CouncilSession.user_id == caller_id)
        else:
            base_q = base_q.where(CouncilSession.user_id.is_(None))

    # total
    count_q = select(func.count()).select_from(base_q.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    paged = base_q.limit(limit).offset(offset)
    res = await db.execute(paged)
    items = res.scalars().all()

    def to_dict(sess):
        return {
            "id": sess.id,
            "user_id": sess.user_id,
            "user_query": sess.user_query,
            "selected_models": sess.selected_models,
            "chairman_model": sess.chairman_model,
            "mode": sess.mode,
            "depth": sess.depth,
            "show_reasoning": sess.show_reasoning,
            "synthesis": sess.synthesis,
            "agreements": sess.agreements,
            "divergences": sess.divergences,
            "unique_insights": sess.unique_insights,
            "deliberation_log": sess.deliberation_log,
            "total_latency": sess.total_latency,
            "status": sess.status,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
            "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
            "responses": [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "model_name": r.model_name,
                    "reasoning": r.reasoning,
                    "final_answer": r.final_answer,
                    "confidence": r.confidence,
                    "latency": r.latency,
                    "token_count": r.token_count,
                    "status": r.status,
                    "error_message": r.error_message,
                    "critique": r.critique,
                    "critique_score": r.critique_score,
                    "raw_payload": r.raw_payload,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in sess.responses
            ],
        }

    return {"total": total, "items": [to_dict(s) for s in items]}
