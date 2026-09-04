import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base, get_db


@pytest.mark.asyncio
async def test_council_query_sse_wire():
    # patch orchestrator to avoid real bridge
    fake_sse = [
        'event: model_start\ndata: {"model":"claude","ts":"2026-09-04T00:00:00Z"}\n\n',
        'event: model_done\ndata: {"model":"claude","status":"done","latency":0.5,"final_answer":"hi","confidence":0.9}\n\n',
        'event: done\ndata: {"session_id":"00000000-0000-0000-0000-000000000000","total_latency":1.0,"synthesis":"done"}\n\n',
    ]

    async def fake_run(*a, **kw):
        for chunk in fake_sse:
            yield chunk

    with patch("app.routers.council.run_council_sse", fake_run):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/council/query", json={"query": "hi?", "models": ["claude", "chatgpt"]})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.text
        assert "event: model_start" in body
        assert "event: done" in body


@pytest.mark.asyncio
async def test_council_session_crud():
    # Use in-memory DB override via get_db dependency
    TEST_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db

    # create via POST then GET
    fake_sse = [
        'event: model_start\ndata: {"model":"claude","ts":"2026-09-04T00:00:00Z"}\n\n',
        'event: model_start\ndata: {"model":"chatgpt","ts":"2026-09-04T00:00:00Z"}\n\n',
        'event: model_done\ndata: {"model":"claude","status":"done","latency":0.1,"final_answer":"a"}\n\n',
        'event: model_done\ndata: {"model":"chatgpt","status":"done","latency":0.1,"final_answer":"b"}\n\n',
        'event: synthesis_start\ndata: {"chairman":"claude","ts":"2026-09-04T00:00:00Z"}\n\n',
        'event: synthesis_stream\ndata: {"delta":"synthesis"}\n\n',
        'event: done\ndata: {"session_id":"11111111-1111-1111-1111-111111111111","total_latency":0.2,"synthesis":"synthesis","agreements":null,"divergences":null,"unique_insights":[]}\n\n',
    ]

    async def fake_run2(*a, **kw):
        # Also insert a row so GET works — simulate orchestrator persisting
        from app.models.council_session import CouncilSession
        from app.models.model_response import ModelResponse
        async with Session() as db:
            sess = CouncilSession(
                id="11111111-1111-1111-1111-111111111111",
                user_query="hi?",
                selected_models=["claude", "chatgpt"],
                chairman_model="claude",
                mode="consensus",
                depth="detailed",
                synthesis="synthesis",
                status="done",
                total_latency=0.2,
            )
            db.add(sess)
            await db.commit()
        for c in fake_sse:
            yield c

    with patch("app.routers.council.run_council_sse", fake_run2):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/council/query", json={"query": "hi?", "models": ["claude", "chatgpt"]})
            assert r.status_code == 200
            # now GET
            r2 = await ac.get("/council/session/11111111-1111-1111-1111-111111111111")
            assert r2.status_code == 200
            assert r2.json()["id"] == "11111111-1111-1111-1111-111111111111"
            # list
            r3 = await ac.get("/council/sessions")
            assert r3.status_code == 200
            assert "total" in r3.json()

    app.dependency_overrides.clear()
    await engine.dispose()
