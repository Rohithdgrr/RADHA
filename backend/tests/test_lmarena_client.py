import json
import pytest
import httpx
from unittest.mock import patch
from app.services.lmarena_client import LMArenaClient
from app.core.config_maps import to_internal


def test_internal_mapping():
    assert to_internal("claude") == "claude-sonnet-4-20250514"
    assert to_internal("chatgpt") == "gpt-5.5-instant"
    assert to_internal("gemini") == "gemini-3-pro"
    assert to_internal("unknown-model") == "unknown-model"


@pytest.mark.asyncio
async def test_chat_completion_stream_mocked():
    # mock httpx.AsyncClient.stream to yield SSE chunks
    sse_payloads = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
        'data: {"choices":[{"delta":{"content":" world"}}]}\n',
        'data: [DONE]\n',
    ]

    class MockStream:
        def __init__(self, *a, **kw):
            self.status_code = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def aiter_lines(self):
            for p in sse_payloads:
                yield p
        async def aread(self):
            return b""

    class MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, *a, **kw):
            # verify payload internal mapping
            assert kw["json"]["model"] == "claude-3-5-sonnet-20241022"
            assert "session_id" in kw["json"]
            return MockStream()

    with patch("app.services.lmarena_client.httpx.AsyncClient", MockClient):
        client = LMArenaClient(base_url="http://mock", token="tok")
        collected = []
        async for d in client.chat_completion_stream("claude", [{"role":"user","content":"hi"}], session_id="test-sid"):
            collected.append(d)
        assert collected == ["Hello", " world"]


@pytest.mark.asyncio
async def test_session_id_unique():
    gen_ids = set()

    class MockStreamUnique:
        def __init__(self, *a, **kw):
            self.status_code = 200
            self._kw = kw
            gen_ids.add(kw["json"]["session_id"])
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def aiter_lines(self):
            yield 'data: [DONE]\n'
        async def aread(self): return b""

    class MockClientU:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, *a, **kw): return MockStreamUnique(*a, **kw)

    with patch("app.services.lmarena_client.httpx.AsyncClient", MockClientU):
        client = LMArenaClient(base_url="http://mock", token="tok")
        # two calls without explicit session_id should generate different uuids
        async for _ in client.chat_completion_stream("claude", [{"role":"user","content":"a"}]):
            pass
        async for _ in client.chat_completion_stream("claude", [{"role":"user","content":"b"}]):
            pass
        assert len(gen_ids) == 2
