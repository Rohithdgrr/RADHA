"""
arena2api - Arena.ai to OpenAI API Proxy
=========================================

极简设计：Chrome 扩展提供 reCAPTCHA token 和 cookies，
本服务器负责 OpenAI 格式转换和 arena.ai API 调用。

使用方式：
  1. pip install -r requirements.txt
  2. python server.py
  3. 安装 Chrome 扩展，打开 arena.ai
  4. 在 OpenAI 客户端中配置 http://localhost:9090/v1
"""

import asyncio
import json
import logging
import os
import re
import secrets
import time
import uuid
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse, JSONResponse

# ============================================================
# 日志
# ============================================================
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("arena2api")

# ============================================================
# 配置
# ============================================================
PORT = int(os.environ.get("PORT", "9090"))
API_KEY = os.environ.get("API_KEY", "").strip()
ARENA_BASE = "https://arena.ai"
ARENA_CREATE_EVAL = f"{ARENA_BASE}/nextjs-api/stream/create-evaluation"
ARENA_POST_EVAL = f"{ARENA_BASE}/nextjs-api/stream/post-to-evaluation"  # + /{id}

# reCAPTCHA
RECAPTCHA_V3_SITEKEY = "6LeTGMcsAAAAALuIlkVwIxaAuZA8VledA6d3Nnb0"

# Fallback models (real arena.ai UUIDs scraped from page)
FALLBACK_MODELS = [
    {"id": "019b24bb-5caf-71c3-b854-37d0c7086f21", "publicName": "Max", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019c2fac-13de-7550-a751-f5f593c77c72", "publicName": "Claude Opus 4.6", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019d9806-5d91-76b3-b353-826cb3193b43", "publicName": "Claude Opus 4.7", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019cc544-4848-771d-947a-1121fad1acb4", "publicName": "Gemini 3.1 Pro", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019cc5aa-2338-72fd-97dd-853736085a83", "publicName": "GPT-5.4", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019e71ea-1e1d-740f-9c2d-dab5869ff108", "publicName": "GPT-5.5 Instant", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019f8b06-4fa3-7bbe-9292-691f9feadc3c", "publicName": "Gemini 3.6 Flash", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "01a00134-44ac-7f9c-b4a7-b720acebaa97", "publicName": "GLM-5.3", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019c2f86-74db-7cc3-baa5-6891bebb5999", "publicName": "Claude Opus 4.6 Thinking", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
    {"id": "019d9808-2b2f-7272-b7ea-0634461e5316", "publicName": "Claude Opus 4.7 Thinking", "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]}},
]

# ============================================================
# UUIDv7
# ============================================================
def uuid7() -> str:
    ts = int(time.time() * 1000)
    ra = secrets.randbits(12)
    rb = secrets.randbits(62)
    u = ts << 80 | (0x7000 | ra) << 64 | (0x8000000000000000 | rb)
    h = f"{u:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


# ============================================================
# Fetch models from arena.ai page (HTML scraping)
# ============================================================
import re as _re

async def fetch_arena_models():
    """Scrape initialModels from arena.ai page HTML."""
    global FALLBACK_MODELS
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(f"{ARENA_BASE}/text/direct?model_a=max")
            if resp.status_code != 200:
                log.warning(f"Failed to fetch arena.ai page: {resp.status_code}")
                return
            html = resp.text
            if "initialModels" not in html:
                log.warning("initialModels not found in arena.ai page")
                return
            # Extract model JSON - HTML has escaped quotes (\")
            # Find the initialModels array using escaped quote patterns
            idx = html.find("initialModels")
            if idx < 0:
                return
            snippet = html[idx:idx+50000]
            # Match id and publicName with escaped quotes
            ids = _re.findall(r'\\"id\\":\\"([^\\]+)\\"', snippet)
            names = _re.findall(r'\\"publicName\\":\\"([^\\]+)\\"', snippet)
            orgs = _re.findall(r'\\"organization\\":\\"([^\\]+)\\"', snippet)
            # Also check for text capability
            text_caps = _re.findall(r'\\"outputCapabilities\\":\{[^}]*\\"text\\":true', snippet)
            
            models = []
            for i in range(min(len(ids), len(names))):
                models.append({
                    "id": ids[i],
                    "publicName": names[i],
                    "organization": orgs[i] if i < len(orgs) else "",
                    "capabilities": {"outputCapabilities": ["text"], "inputCapabilities": ["text"]},
                })
            
            FALLBACK_MODELS = models
            log.info(f"Fetched {len(models)} text models from arena.ai")
            for m in models[:10]:
                log.info(f"  {m['publicName']}: {m['id']}")
            if len(models) > 10:
                log.info(f"  ... and {len(models)-10} more")
    except Exception as e:
        log.error(f"Error fetching arena models: {e}")


# ============================================================
# Token / Cookie Store（从扩展接收）
# ============================================================
class Store:
    def __init__(self):
        self.cookies: dict = {}
        self.auth_token: str = ""
        self.cf_clearance: str = ""
        self.v3_tokens: list = []  # [{token, action, ts}]
        self.v2_token: Optional[dict] = None
        self.last_push: float = 0
        self.models: list = []
        self.text_models: dict = {}  # publicName -> id
        self.image_models: dict = {}
        self.vision_models: list = []
        self.next_actions: dict = {}  # action name -> hash

    @property
    def active(self) -> bool:
        # Active if extension pushed recently, OR if we have cookies manually set
        return (self.last_push > 0 and (time.time() - self.last_push < 120)) or bool(self.cookies)

    def push(self, data: dict):
        self.last_push = time.time()
        if data.get("cookies"):
            self.cookies = data["cookies"]
        if data.get("auth_token"):
            self.auth_token = data["auth_token"]
        if data.get("cf_clearance"):
            self.cf_clearance = data["cf_clearance"]
        # V3 tokens
        if data.get("v3_tokens"):
            for t in data["v3_tokens"]:
                tok = t.get("token", "")
                if not tok or len(tok) < 20:
                    continue
                age = t.get("age_ms", 0)
                if age > 120000:
                    continue
                if any(x["token"] == tok for x in self.v3_tokens):
                    continue
                self.v3_tokens.append({
                    "token": tok,
                    "action": t.get("action", "chat_submit"),
                    "ts": time.time() - age / 1000,
                })
            while len(self.v3_tokens) > 10:
                self.v3_tokens.pop(0)
        # V2 token
        if data.get("v2_token"):
            v2 = data["v2_token"]
            if v2.get("token") and v2.get("age_ms", 0) < 120000:
                self.v2_token = {
                    "token": v2["token"],
                    "ts": time.time() - v2.get("age_ms", 0) / 1000,
                }
        # Models
        if data.get("models"):
            self._update_models(data["models"])
        # Next actions
        if data.get("next_actions"):
            self.next_actions.update(data["next_actions"])

    def _update_models(self, models: list):
        self.models = models
        self.text_models = {}
        self.image_models = {}
        self.vision_models = []
        for m in models:
            name = m.get("publicName", "")
            mid = m.get("id", "")
            caps = m.get("capabilities", {})
            out_caps = caps.get("outputCapabilities", [])
            in_caps = caps.get("inputCapabilities", [])
            if "text" in out_caps:
                self.text_models[name] = mid
            if "image" in out_caps:
                self.image_models[name] = mid
            if "image" in in_caps:
                self.vision_models.append(name)

    def pop_v3_token(self) -> Optional[str]:
        now = time.time()
        self.v3_tokens = [t for t in self.v3_tokens if now - t["ts"] < 120]
        if not self.v3_tokens:
            return None
        return self.v3_tokens.pop(0)["token"]

    def pop_v2_token(self) -> Optional[str]:
        if not self.v2_token:
            return None
        if time.time() - self.v2_token["ts"] > 120:
            self.v2_token = None
            return None
        tok = self.v2_token["token"]
        self.v2_token = None
        return tok

    def build_cookie_header(self) -> str:
        parts = []
        for k, v in self.cookies.items():
            parts.append(f"{k}={v}")
        return "; ".join(parts)

    def status(self) -> dict:
        now = time.time()
        valid_v3 = [t for t in self.v3_tokens if now - t["ts"] < 120]
        # Use fallback models if none pushed by extension
        effective_text = self.text_models if self.text_models else {m["publicName"]: m["id"] for m in FALLBACK_MODELS}
        effective_image = self.image_models
        return {
            "active": self.active,
            "last_push_ago": round(now - self.last_push, 1) if self.last_push else None,
            "v3_tokens": len(valid_v3),
            "has_v2": bool(self.v2_token and now - self.v2_token["ts"] < 120),
            "has_auth": bool(self.auth_token),
            "has_cf": bool(self.cf_clearance),
            "text_models": len(effective_text),
            "image_models": len(effective_image),
            "next_actions": list(self.next_actions.keys()),
            "cookies": list(self.cookies.keys()),
        }


store = Store()

# ============================================================
# FastAPI
# ============================================================
app = FastAPI(title="arena2api", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(request: Request):
    """Optional API key auth for OpenAI endpoints.

    If API_KEY is set, require: Authorization: Bearer <API_KEY>
    """
    if not API_KEY:
        return

    auth_header = request.headers.get("authorization", "")
    expected = f"Bearer {API_KEY}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ============================================================
# 扩展端点
# ============================================================
@app.post("/v1/extension/push")
async def extension_push(request: Request):
    """接收扩展推送的 token、cookies、models"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    store.push(data)
    need = len([t for t in store.v3_tokens if time.time() - t["ts"] < 120]) < 3
    return {
        "status": "ok",
        "need_tokens": need,
        "v3_count": len(store.v3_tokens),
    }


@app.get("/v1/extension/status")
async def extension_status():
    return store.status()


@app.post("/api/cookies")
async def ingest_cookies(request: Request):
    """Accept cookies directly (no Chrome extension needed).

    POST /api/cookies
    {
        "cookies": {
            "arena-auth-prod-v1.0": "base64-...",
            "arena-auth-prod-v1.1": "mll...",
            "cf_clearance": "...",
            "arena_visit_id": "..."
        }
    }

    Split cookies are auto-combined.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    cookies = data.get("cookies", {})
    if not cookies:
        raise HTTPException(400, "Provide 'cookies' dict")

    # Combine split cookies: arena-auth-prod-v1.0 + .1 -> arena-auth-prod-v1
    split_keys = sorted([k for k in cookies if k.startswith("arena-auth-prod-v1.")])
    if split_keys:
        combined = "".join(cookies.pop(k) for k in split_keys)
        cookies["arena-auth-prod-v1"] = combined
        log.info(f"Combined {len(split_keys)} split cookies into arena-auth-prod-v1 ({len(combined)} chars)")

    # Extract auth token from cookie if present
    auth_cookie = cookies.get("arena-auth-prod-v1", "")
    if auth_cookie:
        store.auth_token = auth_cookie
        log.info(f"Set auth_token from cookie ({len(auth_cookie)} chars)")

    # Update cookies
    store.cookies.update(cookies)
    store.last_push = time.time()

    return {
        "status": "ok",
        "cookies_count": len(store.cookies),
        "has_auth": bool(store.auth_token),
        "auth_len": len(store.auth_token),
    }


# ============================================================
# OpenAI 兼容端点
# ============================================================
@app.get("/v1/models")
async def list_models(request: Request):
    """列出可用模型"""
    verify_api_key(request)
    all_models = {}
    all_models.update(store.text_models)
    all_models.update(store.image_models)
    # Use fallback if no extension models
    if not all_models:
        all_models = {m["publicName"]: m["id"] for m in FALLBACK_MODELS}
    data = []
    for name in sorted(all_models.keys()):
        data.append({
            "id": name,
            "object": "model",
            "created": 0,
            "owned_by": "arena.ai",
        })
    return {"object": "list", "data": data}


def detect_client(request: Request) -> str:
    """检测客户端类型"""
    ua = request.headers.get("user-agent", "").lower()
    if "claude" in ua or "anthropic" in ua:
        return "claude"
    if "gemini" in ua or "google" in ua:
        return "gemini"
    if "codex" in ua:
        return "codex"
    if "opencode" in ua:
        return "opencode"
    # NewAPI/OneAPI 通常使用标准 OpenAI 格式
    return "openai"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI 兼容的聊天补全"""
    verify_api_key(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    client_type = detect_client(request)
    model_name = body.get("model", "")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    if not messages:
        raise HTTPException(400, "messages is required")

    # 检查扩展是否连接
    if not store.active and not store.cookies:
        raise HTTPException(503, "Extension not connected. Please open arena.ai in Chrome with the extension installed.")

    # 解析模型
    model_id = store.text_models.get(model_name) or store.image_models.get(model_name)
    if not model_id:
        # Try fallback models
        fallback_map = {m["publicName"]: m["id"] for m in FALLBACK_MODELS}
        model_id = fallback_map.get(model_name)
    if not model_id:
        # 尝试模糊匹配
        all_models = {**store.text_models, **store.image_models}
        if not all_models:
            all_models = {m["publicName"]: m["id"] for m in FALLBACK_MODELS}
        for name, mid in all_models.items():
            if model_name.lower() in name.lower() or name.lower() in model_name.lower():
                model_id = mid
                model_name = name
                break
    if not model_id:
        available = list(store.text_models.keys()) + list(store.image_models.keys())
        if not available:
            available = [m["publicName"] for m in FALLBACK_MODELS]
        raise HTTPException(404, f"Model '{model_name}' not found. Available: {available[:20]}")

    # 构建 prompt（取最后一条 user 消息）
    prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                # 多模态消息
                text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                prompt = "\n".join(text_parts)
            else:
                prompt = content
            break
    if not prompt:
        prompt = messages[-1].get("content", "")

    # 如果有 system message，拼接到 prompt 前面
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    if system_parts:
        prompt = "\n".join(system_parts) + "\n\n" + prompt

    # 如果有多轮对话，拼接历史
    if len(messages) > 1:
        history_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = "\n".join(p.get("text", "") for p in content if p.get("type") == "text")
            if role == "system":
                continue  # 已经处理
            history_parts.append(f"<|{role}|>\n{content}")
        prompt = "\n".join(history_parts)

    # 获取 reCAPTCHA token
    v3_token = store.pop_v3_token()
    v2_token = store.pop_v2_token() if not v3_token else None

    is_image = model_name in store.image_models
    modality = "image" if is_image else "chat"

    # 构建 arena.ai 请求
    eval_id = uuid7()
    user_msg_id = uuid7()
    model_a_msg_id = uuid7()

    # 从 cookies 中提取 userId
    user_id = store.cookies.get("arena-user-id", "")
    if not user_id:
        # 尝试从其他 cookie 中提取
        for key, value in store.cookies.items():
            if "user" in key.lower() and len(value) > 20:
                user_id = value
                break

    arena_payload = {
        "id": eval_id,
        "mode": "direct-battle",
        "modelAId": model_id,
        "userMessageId": user_msg_id,
        "modelAMessageId": model_a_msg_id,
        "userMessage": {
            "content": prompt,
            "experimental_attachments": [],
            "metadata": {},
        },
        "modality": modality,
    }

    # 添加 userId（如果有）
    if user_id:
        arena_payload["userId"] = user_id

    if v2_token:
        arena_payload["recaptchaV2Token"] = v2_token
        arena_payload["recaptchaV3Token"] = None
    elif v3_token:
        arena_payload["recaptchaV3Token"] = v3_token
    else:
        log.warning("No reCAPTCHA token available, sending without token")

    # 构建 headers
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": ARENA_BASE,
        "referer": f"{ARENA_BASE}/?mode=direct",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "cookie": store.build_cookie_header(),
    }

    # 添加认证 header（如果有 auth_token）
    if store.auth_token:
        headers["authorization"] = f"Bearer {store.auth_token}"

    url = ARENA_CREATE_EVAL
    log.info(f"Sending to arena.ai: model={model_name} (id={model_id}), eval_id={eval_id}, has_v3={bool(v3_token)}, has_v2={bool(v2_token)}")
    log.info(f"Arena payload: {json.dumps(arena_payload, default=str)[:500]}")

    if stream:
        return StreamingResponse(
            stream_response(url, arena_payload, headers, model_name, eval_id, client_type),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return await non_stream_response(url, arena_payload, headers, model_name, eval_id, client_type)


async def stream_response(url, payload, headers, model_name, eval_id, client_type="openai"):
    """流式响应生成器"""
    chat_id = f"chatcmpl-{eval_id}"
    created = int(time.time())

    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    log.error(f"Arena API error: {resp.status_code} {body[:1000]}")
                    log.error(f"Request headers: {dict(resp.headers)}")
                    error_chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": f"[Error: Arena API returned {resp.status_code}: {body[:200].decode('utf-8', errors='replace')}]"},
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
                        # 文本内容
                        try:
                            content = json.loads(line[3:])
                            if content == "hasArenaError":
                                content = "[Arena Error]"
                                finish = "stop"
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("ag:"):
                        # 推理内容
                        try:
                            reasoning = json.loads(line[3:])
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("ad:"):
                        # 完成
                        finish = "stop"
                        try:
                            data = json.loads(line[3:])
                            if data.get("finishReason"):
                                finish = data["finishReason"]
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("a2:"):
                        # heartbeat 或图片
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
                        # 错误
                        try:
                            content = f"[Error: {json.loads(line[3:])}]"
                        except:
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
                        # Claude/Anthropic 格式兼容
                        if client_type == "claude":
                            chunk["type"] = "content_block_delta"
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                    if reasoning is not None:
                        # 将推理内容作为普通内容输出（或可以用 reasoning_content）
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


async def non_stream_response(url, payload, headers, model_name, eval_id, client_type="openai"):
    """非流式响应"""
    content_parts = []
    reasoning_parts = []
    finish_reason = "stop"
    usage = {}

    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
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
                        except:
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

    response = {
        "id": f"chatcmpl-{eval_id}",
        "object": "chat.completion",
        "created": int(time.time()),
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

    # Claude 格式兼容
    if client_type == "claude":
        response["type"] = "message"
        response["role"] = "assistant"
        response["content"] = [{"type": "text", "text": full_content}]

    return response


# ============================================================
# 健康检查
# ============================================================
@app.get("/health")
@app.get("/")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "extension": store.status(),
    }


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    log.info(f"Starting arena2api on port {PORT}")
    log.info(f"OpenAI API: http://localhost:{PORT}/v1")
    log.info("Waiting for Chrome extension to connect...")
    # Fetch models from arena.ai on startup
    import asyncio as _asyncio
    _asyncio.get_event_loop().run_until_complete(fetch_arena_models())
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
