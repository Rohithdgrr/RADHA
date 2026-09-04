import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from app.main import app
from app.services import lmarena_models


@pytest.mark.asyncio
async def test_models_fallback_when_bridge_down():
    # patch fetch to return None → fallback to static models
    with patch("app.routers.models.fetch_models_from_bridge", return_value=None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert len(data["models"]) >= 6
        ids = [m["id"] for m in data["models"]]
        assert "claude" in ids


@pytest.mark.asyncio
async def test_models_bridge_success():
    mock_models = [{"id": "claude", "display_name": "Claude", "internal_id": "claude-3-5-sonnet", "available": True}]
    with patch("app.routers.models.fetch_models_from_bridge", return_value=mock_models):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/models")
        assert r.status_code == 200
        assert r.json()["models"][0]["id"] == "claude"
