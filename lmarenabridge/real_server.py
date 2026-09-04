"""
Real LMArena Bridge — direct arena.ai API proxy using LMARENA_TOKEN
No Chrome extension required. Uses access_token for authorization + cookies from token.
"""
import asyncio
import base64
import json
import logging
import os
import time
import uuid
import secrets

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse, JSONResponse

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("real-bridge")

PORT = int(os.environ.get("PORT", "8001"))
RAW_LMARENA_TOKEN = os.environ.get("LMARENA_TOKEN", "").strip()

ARENA_BASE = "https://arena.ai"
ARENA_CREATE_EVAL = f"{ARENA_BASE}/nextjs-api/stream/create-evaluation"

MODEL_MAP = {
    "claude": "Claude Sonnet 4 (20250514)",
    "chatgpt": "ChatGPT-5 (20250806)",
    "gemini": "Gemini 2.5 Pro (20250617)",
    "deepseek": "DeepSeek V3.1 (20250715)",
    "qwen": "Qwen3 72B (20250728)",
    "kimi": "Kimi K2.5 (20250720)",
    "kimi-k3": "Kimi K3 (20250828) Preview",
    "grok": "Grok-2 (20250701)",
    "llama": "Llama-3.1-405B (20250715)",
}

INTERNAL_MODEL_MAP = {
    "claude": "claude-sonnet-4-20250514",
    "chatgpt": "gpt-5-20250806",
    "gemini": "gemini-2.5-pro-20250617",
    "deepseek": "deepseek-v3.1-20250715",
    "qwen": "qwen3-72b-20250728",
    "kimi": "kimi-k2.5-20250720",
    "kimi-k3": "kimi-k3-20250828",
    "grok": "grok-2-20250701",
    "llama": "llama-3.1-405b-20250715",
}

REVERSE_INTERNAL = {v: k for k, v in INTERNAL_MODEL_MAP.items()}


def uuid7() -> str:
    ts = int(time.time() * 1000)
    ra = secrets.randbits(12)
    rb = secrets.randbits(62)
    u = ts << 80 | (0x7000 | ra) << 64 | (0x8000000000000000 | rb)
    h = f"{u:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def parse_token(raw_token: str) -> dict:
    """Parse the LMARENA_TOKEN base64-encoded JSON to extract access_token, user_id, cookies."""
    result = {"access_token": "", "user_id": "", "email": "", "expires_at": 0, "cookies": {}}
    if not raw_token:
        return result

    try:
        padded = raw_token + "=" * (4 - len(raw_token) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        data = json.loads(decoded)
        result["access_token"] = data.get("access_token", "")
        result["expires_at"] = data.get("expires_at", 0)
        user = data.get("user", {})
        result["user_id"] = user.get("id", "")
        result["email"] = user.get("email", "")
        log.info(f"Token parsed: email={result['email']}, user_id={result['user_id'][:12]}..., expires_at={result['expires_at']}")
        now = int(time.time())
        if result["expires_at"] and result["expires_at"] < now:
            log.warning(f"Token EXPIRED {now - result['expires_at']}s ago!")
        else:
            log.info(f"Token valid, expires in {result['expires_at'] - now}s")
    except Exception as e:
        log.error(f"Failed to parse token: {e}")
        result["access_token"] = raw_token

    return result


token_data = parse_token(RAW_LMARENA_TOKEN)
access_token = token_data["access_token"]
user_id = token_data["user_id"]

log.info(f"access_token length: {len(access_token)}")
log.info(f"user_id: {user_id}")


app = FastAPI(title="Real LMArena Bridge", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "bridge": "real",
        "has_token": bool(access_token),
        "has_user_id": bool(user_id),
    }


@app.get("/v1/models")
async def list_models():
    data = [
        {"id": name, "object": "model", "created": 0, "owned_by": "arena.ai"}
        for name in MODEL_MAP.keys()
    ]
    return {"object": "list", "data": data}


@app.get("/models")
async def list_models_alt():
    models = []
    for canonical, public_name in MODEL_MAP.items():
        internal = INTERNAL_MODEL_MAP.get(canonical, canonical)
        models.append({
            "id": canonical,
            "display_name": public_name,
            "internal_id": internal,
            "available": True,
        })
    return {"models": models}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    model_name = body.get("model", "")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    if not messages:
        raise HTTPException(400, "messages is required")

    public_name = MODEL_MAP.get(model_name)
    internal_id = INTERNAL_MODEL_MAP.get(model_name)
    if not public_name and not internal_id:
        canonical = REVERSE_INTERNAL.get(model_name)
        if canonical:
            public_name = MODEL_MAP.get(canonical)
            internal_id = INTERNAL_MODEL_MAP.get(canonical)
    if not public_name:
        for canon, pname in MODEL_MAP.items():
            if model_name.lower() in canon.lower() or canon.lower() in model_name.lower():
                public_name = pname
                internal_id = INTERNAL_MODEL_MAP.get(canon)
                model_name = canon
                break
    if not public_name:
        available = list(MODEL_MAP.keys())
        raise HTTPException(404, f"Model '{model_name}' not found. Available: {available}")

    prompt = ""
    system_parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            prompt = content

    if system_parts:
        prompt = "\n".join(system_parts) + "\n\n" + prompt

    if not prompt:
        prompt = messages[-1].get("content", "") if messages else "Hello"

    eval_id = uuid7()
    user_msg_id = uuid7()
    model_a_msg_id = uuid7()

    arena_payload = {
        "id": eval_id,
        "mode": "direct",
        "modelAId": public_name,
        "userMessageId": user_msg_id,
        "modelAMessageId": model_a_msg_id,
        "userMessage": {
            "content": prompt,
            "experimental_attachments": [],
            "metadata": {},
        },
        "modality": "chat",
    }

    if user_id:
        arena_payload["userId"] = user_id

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": ARENA_BASE,
        "referer": f"{ARENA_BASE}/?mode=direct",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    cookie_parts = []
    if user_id:
        cookie_parts.append(f"arena-user-id={user_id}")
    if cookie_parts:
        headers["cookie"] = "; ".join(cookie_parts)

    if access_token:
        headers["authorization"] = f"Bearer {access_token}"

    chat_id = f"chatcmpl-{eval_id}"
    created = int(time.time())

    log.info(f"Sending to arena.ai: model={public_name}, eval_id={eval_id}, user_id={user_id[:12]}...")

    if stream:
        return StreamingResponse(
            stream_response(headers, arena_payload, model_name, chat_id, created),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return await non_stream_response(headers, arena_payload, model_name, chat_id, created)


async def stream_response(headers, payload, model_name, chat_id, created):
    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            async with client.stream("POST", ARENA_CREATE_EVAL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    log.error(f"Arena API error: {resp.status_code} {body[:500]}")
                    error_chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": f"[Error: Arena API returned {resp.status_code}: {body[:200]}]"},
                            "finish_reason": "stop",
                        }],
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue

                    content = None
                    reasoning = None
                    finish = None

                    if line.startswith("a0:"):
                        try:
                            content = json.loads(line[3:])
                            if content == "hasArenaError":
                                content = "[Arena Error]"
                                finish = "stop"
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("ag:"):
                        try:
                            reasoning = json.loads(line[3:])
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("ad:"):
                        finish = "stop"
                        try:
                            data = json.loads(line[3:])
                            if data.get("finishReason"):
                                finish = data["finishReason"]
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("a2:"):
                        if "heartbeat" in line:
                            continue
                        try:
                            data = json.loads(line[3:])
                            images = [img.get("image") for img in data if img.get("image")]
                            if images:
                                content = "\n".join(f"![image]({url})" for url in images)
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("a3:"):
                        try:
                            content = f"[Error: {json.loads(line[3:])}]"
                        except Exception:
                            content = f"[Error: {line[3:]}]"
                        finish = "stop"
                    else:
                        continue

                    if content is not None:
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model_name,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None,
                            }],
                        }
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                    if reasoning is not None:
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model_name,
                            "choices": [{
                                "index": 0,
                                "delta": {"reasoning_content": reasoning},
                                "finish_reason": None,
                            }],
                        }
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                    if finish:
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model_name,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": finish if finish != "stop" else "stop",
                            }],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        return

    except Exception as e:
        log.error(f"Stream error: {e}")
        error_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {"content": f"[Stream Error: {e}]"},
                "finish_reason": "stop",
            }],
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


async def non_stream_response(headers, payload, model_name, chat_id, created):
    content_parts = []
    reasoning_parts = []
    finish_reason = "stop"
    usage = {}

    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            async with client.stream("POST", ARENA_CREATE_EVAL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    log.error(f"Arena API error: {resp.status_code} {body[:500]}")
                    raise HTTPException(resp.status_code, f"Arena API error: {body[:200]}")

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    if line.startswith("a0:"):
                        try:
                            text = json.loads(line[3:])
                            if isinstance(text, str) and text != "hasArenaError":
                                content_parts.append(text)
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("ag:"):
                        try:
                            text = json.loads(line[3:])
                            if isinstance(text, str):
                                reasoning_parts.append(text)
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("ad:"):
                        try:
                            data = json.loads(line[3:])
                            if data.get("finishReason"):
                                finish_reason = data["finishReason"]
                            if data.get("usage"):
                                usage = data["usage"]
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("a2:"):
                        if "heartbeat" in line:
                            continue
                        try:
                            data = json.loads(line[3:])
                            images = [img.get("image") for img in data if img.get("image")]
                            for img_url in images:
                                content_parts.append(f"![image]({img_url})")
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("a3:"):
                        try:
                            content_parts.append(f"[Error: {json.loads(line[3:])}]")
                        except Exception:
                            content_parts.append(f"[Error: {line[3:]}]")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Non-stream error: {e}")
        raise HTTPException(500, str(e))

    full_content = "".join(content_parts)
    full_reasoning = "".join(reasoning_parts)

    message = {"role": "assistant", "content": full_content}
    if full_reasoning:
        message["reasoning_content"] = full_reasoning

    return {
        "id": chat_id,
        "object": "chat.completion",
        "created": created,
        "model": model_name,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": finish_reason,
        }],
        "usage": usage or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


if __name__ == "__main__":
    log.info(f"Starting Real LMArena Bridge on port {PORT}")
    log.info(f"Has access token: {bool(access_token)}, user_id: {user_id[:12] if user_id else 'none'}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
