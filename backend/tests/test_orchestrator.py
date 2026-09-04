import json
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.services.orchestrator import run_council_sse, _sse


TEST_URL = "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_orchestrator_two_success():
    engine = create_async_engine(TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_chat(model, messages, session_id=None, timeout=None):
        # model call → reasoning+answer
        if "chair" in str(messages).lower() or "chairman" in str(messages).lower() or "synthesis" in str(messages).lower() or "chair" in str(messages):
            # synthesis prompt contains synthesis key
            pass
        # detect synthesis prompt by checking if query synthesis
        # For simplicity, if messages contain "You are the chair" → synthesis
        txt = json.dumps(messages)
        if "You are the chair" in txt or "You are the council chairman" in txt:
            return json.dumps({
                "synthesis": "Unified answer",
                "agreements": "A1",
                "divergences": "D1",
                "unique_insights": ["U1"]
            })
        return f"<reasoning>think {model}</reasoning><answer>Answer {model}\nConfidence: 90%</answer>"

    # patch the client's chat_completion used inside orchestrator
    with patch("app.services.orchestrator.LMArenaClient") as MockClient:
        mock_inst = MockClient.return_value
        mock_inst.chat_completion = AsyncMock(side_effect=mock_chat)

        async with Session() as db:
            chunks = []
            async for chunk in run_council_sse(
                query="What is 2+2?",
                models=["claude", "chatgpt"],
                chairman="claude",
                mode="consensus",
                depth="detailed",
                show_reasoning=True,
                user_id=None,
                db=db,
            ):
                chunks.append(chunk)
            text = "".join(chunks)
            assert "event: model_start" in text
            assert "event: model_done" in text
            assert "event: synthesis_start" in text
            assert "event: done" in text
            # parse done payload
            # find last done event
            for line in text.splitlines():
                if line.startswith("data:") and "synthesis" in line and "session_id" in line:
                    data = json.loads(line[5:].strip())
                    if "synthesis" in data and "session_id" in data:
                        assert data["synthesis"] == "Unified answer"
                        assert data["agreements"] == "A1"
    await engine.dispose()


@pytest.mark.asyncio
async def test_orchestrator_insufficient_models():
    engine = create_async_engine(TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_one_success(model, messages, session_id=None, timeout=None):
        txt = json.dumps(messages)
        if "You are the chair" in txt or "You are the council chairman" in txt:
            return json.dumps({"synthesis": "x", "agreements": "a", "divergences": "d", "unique_insights": []})
        if model == "claude":
            return "<reasoning>r</reasoning><answer>ok\nConfidence: 80%</answer>"
        raise Exception("model fail")

    with patch("app.services.orchestrator.LMArenaClient") as MockClient:
        mock_inst = MockClient.return_value
        mock_inst.chat_completion = AsyncMock(side_effect=mock_one_success)
        async with Session() as db:
            chunks = []
            async for chunk in run_council_sse("q", ["claude", "chatgpt"], "claude", "consensus", "detailed", True, None, db):
                chunks.append(chunk)
            text = "".join(chunks)
            assert "event: error" in text
            assert "INSUFFICIENT_MODELS" in text
    await engine.dispose()
