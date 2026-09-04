import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base, get_db
from app.main import app

TEST_URL = "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_register_login_me_flow():
    engine = create_async_engine(TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # register
        r = await ac.post("/auth/register", json={"email": "alice@example.com", "password": "secret123", "display_name": "Alice"})
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        assert token
        # me
        r2 = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.json()["email"] == "alice@example.com"
        # login
        r3 = await ac.post("/auth/login", json={"email": "alice@example.com", "password": "secret123"})
        assert r3.status_code == 200
        # bad password
        r4 = await ac.post("/auth/login", json={"email": "alice@example.com", "password": "wrongpass"})
        assert r4.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_duplicate_409():
    engine = create_async_engine(TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.post("/auth/register", json={"email": "dup@example.com", "password": "secret123"})
        assert r1.status_code == 201
        r2 = await ac.post("/auth/register", json={"email": "dup@example.com", "password": "secret123"})
        assert r2.status_code == 409
        r3 = await ac.post("/auth/register", json={"email": "DUP@example.com", "password": "secret123"})
        assert r3.status_code == 409
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_me_no_token_401():
    engine = create_async_engine(TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/auth/me")
        assert r.status_code == 401
        r2 = await ac.get("/auth/me", headers={"Authorization": "Bearer badtoken123"})
        assert r2.status_code == 401
    app.dependency_overrides.clear()
    await engine.dispose()
