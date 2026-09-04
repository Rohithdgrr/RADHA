import json
import uuid
import structlog
import httpx
from typing import AsyncGenerator

from app.config import settings
from app.core.config_maps import to_internal

log = structlog.get_logger()


class BridgeError(Exception):
    def __init__(self, message: str, code: str = "BRIDGE_ERROR"):
        super().__init__(message)
        self.code = code


class BridgeTimeout(BridgeError):
    def __init__(self, message="LMArenaBridge timeout after 120s"):
        super().__init__(message, code="BRIDGE_TIMEOUT")


class BridgeAuthError(BridgeError):
    def __init__(self, message="LMArena auth failed (token expired?)"):
        super().__init__(message, code="BRIDGE_AUTH")


class LMArenaClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or settings.LMARENA_BRIDGE_URL).rstrip("/")
        self.token = token if token is not None else settings.LMARENA_TOKEN
        self.timeout = float(settings.REQUEST_TIMEOUT)

    async def chat_completion_stream(
        self,
        model: str,
        messages: list[dict],
        session_id: str | None = None,
        timeout: float | None = None,
    ) -> AsyncGenerator[str, None]:
        sid = session_id or str(uuid.uuid4())
        internal = to_internal(model)
        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {
            "model": internal,
            "messages": messages,
            "stream": True,
            "session_id": sid,
        }
        timeout_val = timeout if timeout is not None else self.timeout
        # httpx timeout
        http_timeout = httpx.Timeout(timeout_val, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=http_timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code == 401:
                        raise BridgeAuthError(f"Bridge 401 at {url} — token expired")
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        raise BridgeError(f"Bridge {resp.status_code}: {body[:500]}", code="BRIDGE_HTTP")
                    # stream SSE lines
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        line = line.strip()
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            if not data_str:
                                continue
                            try:
                                data = json.loads(data_str)
                            except Exception:
                                # some bridges send plain delta string
                                yield data_str
                                continue
                            # OpenAI shape
                            if isinstance(data, dict) and "choices" in data:
                                choices = data["choices"]
                                if choices and isinstance(choices, list):
                                    delta = choices[0].get("delta", {}) or choices[0].get("message", {})
                                    content = delta.get("content")
                                    if content:
                                        yield content
                                    # also handle finish_reason? ignore
                                continue
                            # custom shapes
                            for key in ("delta", "content", "text", "answer"):
                                if isinstance(data, dict) and key in data and isinstance(data[key], str):
                                    yield str(data[key])
                                    break
                            else:
                                # unknown, try to yield choices[0].text
                                if isinstance(data, dict):
                                    # fallback to stringify? ignore
                                    pass
                        # also handle non-SSE JSON streaming (one JSON per line)
                        elif line.startswith("{"):
                            try:
                                data = json.loads(line)
                                for key in ("delta", "content", "text"):
                                    if key in data:
                                        yield str(data[key])
                                        break
                            except Exception:
                                continue
        except httpx.TimeoutException as e:
            raise
        except BridgeError as e:
            raise
        except Exception as e:
            raise BridgeError(str(e)) from e

    async def chat_completion(
        self,
        model: str,
        messages: list[dict],
        session_id: str | None = None,
        timeout: float | None = None,
    ) -> str:
        chunks: list[str] = []
        async for delta in self.chat_completion_stream(model, messages, session_id=session_id, timeout=timeout):
            chunks.append(delta)
        return "".join(chunks)
