import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.db.base import Base
from app.models import User, CouncilSession, ModelResponse

# use in-memory sqlite for CI — no PG needed
TEST_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s


@pytest.mark.asyncio
async def test_create_user_session_response_flow(session):
    u = User(email="a@b.com", password_hash="hash", display_name="A")
    session.add(u)
    await session.flush()
    cs = CouncilSession(
        user_id=u.id,
        user_query="hello?",
        selected_models=["claude", "chatgpt"],
        chairman_model="claude",
        mode="consensus",
        depth="detailed",
        status="running",
    )
    session.add(cs)
    await session.flush()
    mr = ModelResponse(
        session_id=cs.id,
        model_name="claude",
        final_answer="ans",
        latency=0.5,
        status="done",
    )
    session.add(mr)
    await session.commit()

    # reload
    q = await session.execute(select(CouncilSession).where(CouncilSession.id == cs.id))
    loaded = q.scalars().first()
    assert loaded.user_query == "hello?"
    assert len(loaded.responses) == 1
    assert loaded.responses[0].model_name == "claude"

    # cascade: delete session → responses gone
    await session.delete(loaded)
    await session.commit()
    q2 = await session.execute(select(ModelResponse).where(ModelResponse.session_id == cs.id))
    assert q2.scalars().first() is None


@pytest.mark.asyncio
async def test_anon_session(session):
    cs = CouncilSession(
        user_id=None,
        user_query="anon q",
        selected_models=["claude", "chatgpt"],
        chairman_model="claude",
        status="done",
    )
    session.add(cs)
    await session.commit()
    assert cs.user_id is None


@pytest.mark.asyncio
async def test_unique_session_model(session):
    cs = CouncilSession(
        user_query="q",
        selected_models=["claude", "chatgpt"],
        chairman_model="claude",
        status="done",
    )
    session.add(cs)
    await session.flush()
    mr1 = ModelResponse(session_id=cs.id, model_name="claude", final_answer="a", latency=0.1)
    mr2 = ModelResponse(session_id=cs.id, model_name="claude", final_answer="b", latency=0.2)
    session.add_all([mr1, mr2])
    with pytest.raises(Exception):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_user_email_unique(session):
    u1 = User(email="dup@ex.com", password_hash="h1")
    u2 = User(email="dup@ex.com", password_hash="h2")
    session.add(u1)
    await session.flush()
    session.add(u2)
    with pytest.raises(Exception):
        await session.commit()
    await session.rollback()
