"""
Mock LMArena Bridge — real OpenAI-compatible streaming server for local dev
Serves GET /v1/models and POST /v1/chat/completions with token-by-token SSE
No LMArena token needed. Used when LMARENA_TOKEN is placeholder.
"""
import asyncio
import json
import time
import uuid
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Mock LMArena Bridge", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

MODELS = [
    {"id": "claude-sonnet-4-20250514", "object": "model", "created": 0, "owned_by": "anthropic"},
    {"id": "gpt-5-20250806", "object": "model", "created": 0, "owned_by": "openai"},
    {"id": "gemini-2.5-pro-20250617", "object": "model", "created": 0, "owned_by": "google"},
    {"id": "deepseek-v3.1-20250715", "object": "model", "created": 0, "owned_by": "deepseek"},
    {"id": "qwen3-72b-20250728", "object": "model", "created": 0, "owned_by": "alibaba"},
    {"id": "kimi-k2.5-20250720", "object": "model", "created": 0, "owned_by": "moonshot"},
    {"id": "kimi-k3-20250828", "object": "model", "created": 0, "owned_by": "moonshot"},
    {"id": "grok-2-20250701", "object": "model", "created": 0, "owned_by": "xai"},
    {"id": "llama-3.1-405b-20250715", "object": "model", "created": 0, "owned_by": "meta"},
]

INTERNAL_TO_CANON = {
    "claude-sonnet-4-20250514": "claude",
    "gpt-5-20250806": "chatgpt",
    "gemini-2.5-pro-20250617": "gemini",
    "deepseek-v3.1-20250715": "deepseek",
    "qwen3-72b-20250728": "qwen",
    "kimi-k2.5-20250720": "kimi",
    "kimi-k3-20250828": "kimi-k3",
    "grok-2-20250701": "grok",
    "llama-3.1-405b-20250715": "llama",
}

def chairman_synthesis(query: str, answers: list) -> dict:
    models = [a.get("model","claude") for a in answers]
    joined = ", ".join(models)
    q_lower = query.lower()
    if "plaster" in q_lower:
        core = "Plaster is a binder+aggregate coating for walls/ceilings; gypsum hydrates, lime carbonates."
        rec = "For interior use gypsum (fast, smooth), for exterior/heritage use lime (breathable)."
    elif "quantum" in q_lower:
        core = "Quantum computing uses qubits in superposition/entanglement to explore many states in parallel, unlike classical bits (0/1)."
        rec = "Think of classical as light switch, quantum as spinning coin; error correction and decoherence remain key hurdles."
    elif "photosynthesis" in q_lower:
        core = "Photosynthesis converts light + CO2 + water -> glucose + O2 via chlorophyll in chloroplasts (light-dependent reactions + Calvin cycle)."
        rec = "Light reactions split water and make ATP/NADPH; Calvin cycle fixes CO2 into sugar - basis of food chains."
    elif "poem" in q_lower or "monsoon" in q_lower:
        core = "Creative responses vary in style but converge on monsoon imagery: rain, clouds, renewal, earth scent (petrichor)."
        rec = "Choose Qwen/Kimi for lyrical, Claude for structured, ChatGPT for warm narrative - all capture monsoon's rhythm."
    elif "india" in q_lower:
        core = "India is a diverse democracy, 1.4B people, federal union, fast-growing economy blending ancient heritage with modern tech."
        rec = "Consensus highlights geography, culture, economy and challenges; each model emphasizes different lenses (history, policy, innovation)."
    else:
        core = f"All models address '{query[:80]}' with complementary perspectives, converging on the core question while adding nuance."
        rec = f"Synthesis distills the common answer to '{query[:60]}...' and highlights actionable takeaways."
    return {
        "synthesis": f"# Unified Synthesis\n\n**Query:** {query}\n\nAll {len(answers)} models converge while adding complementary nuance. {core}\n\n**Consensus view ({joined}):** {core}\n\n**Recommendation:** {rec}",
        "agreements": f"- All models ({joined}) agree on the core premise of '{query[:50]}...'\n- Shared facts and structure across answers\n- Complementary depth per model",
        "divergences": "- Claude emphasizes structure/brevity\n- ChatGPT stresses narrative/examples\n- Gemini adds tables/visuals\n- DeepSeek details technical depth\n- Qwen notes cross-cultural angle",
        "unique_insights": [f"{m}: unique angle on '{query[:30]}...' from {m} perspective" for m in models[:3]]
    }

def generate_mock_content(model_internal: str, messages: list) -> str:
    canon = INTERNAL_TO_CANON.get(model_internal, model_internal.split("-")[0])
    query = ""
    system = ""
    for m in messages:
        if m.get("role") == "user":
            c = m.get("content","")
            if isinstance(c, list):
                c = " ".join(p.get("text","") for p in c if isinstance(p, dict))
            query = c
        if m.get("role") == "system":
            system += str(m.get("content","")) + "\n"
    is_chairman = "You are the council chairman" in system or "You are the chair" in system or "synthesize" in query.lower()[:200] and "Responses:" in query
    if is_chairman or "You are the council chairman" in system:
        qm = re.search(r'User Query:\s*"([^"]+)"', query, re.DOTALL)
        q = qm.group(1) if qm else query[:120]
        answers = []
        for m in re.findall(r'\[(\w[\w\-\.]*)\]:', query):
            answers.append({"model": m})
        if not answers:
            answers = [{"model":"claude"},{"model":"chatgpt"}]
        synth = chairman_synthesis(q, answers)
        return json.dumps(synth, ensure_ascii=False)

    q = query[:400] if query else "Explain plaster"
    q_low = q.lower()
    conf_map = {"claude": 92, "chatgpt": 88, "gemini": 90, "deepseek": 85, "qwen": 87, "kimi": 86, "kimi-k3": 89, "grok": 84, "llama": 86}
    conf = conf_map.get(canon, 87)

    def generic_answer():
        if "quantum" in q_low:
            return f"### Quantum Computing ({canon})\n\n**Query:** {q}\n\nClassical bit = light switch (0/1), qubit = spinning coin (0,1,both).\n\nSuperposition, entanglement, interference make it powerful for certain problems.\n\nChallenges: decoherence, error correction.\n\nConfidence: {conf}%"
        if "photosynthesis" in q_low:
            return f"### Photosynthesis ({canon})\n\n6CO2 + 6H2O + light -> C6H12O6 + 6O2\n\nTwo stages: light-dependent reactions + Calvin cycle.\n\nConfidence: {conf}%"
        if "poem" in q_low or "monsoon" in q_low:
            return f"### Monsoon Poem ({canon})\n\nClouds gather, grey and low,\nFirst drops tap on mango leaves,\nEarth exhales petrichor,\nFields drink, rivers breathe.\n\nConfidence: {conf}%"
        if "india" in q_low:
            return f"### India ({canon})\n\n- Geography: 3.28M km2, Himalayas, Deccan, 7500km coastline\n- People: 1.4B+, 22 official languages\n- Economy: 5th largest GDP\n\nConfidence: {conf}%"
        return f"### Answer ({canon})\n\n**Query:** {q}\n\nStructured response addressing the query with clear definition, key points, and actionable takeaways.\n\nConfidence: {conf}%"

    if "plaster" not in q_low:
        answer = generic_answer()
    elif canon == "claude":
        answer = f"### Plaster - Structured Overview\n\n**What it is:** A workable paste of binder, aggregate and water that hardens into a durable surface.\n\n**Types:** Gypsum (interior, fast), Lime (heritage, breathable), Cement (exterior, strong).\n\n**How it works:** Mixed to consistency, applied in coats: scratch, brown, finish.\n\nConfidence: {conf}%"
    elif canon == "chatgpt":
        answer = f"Plaster is a **paste that turns into a hard skin** for walls.\n\nThink chicken soup: binder = protein, sand = veggies, water = broth.\n\n**3-coat trick:** Scratch -> Brown -> Finish. Keep damp while curing.\n\nConfidence: {conf}%"
    elif canon == "gemini":
        answer = f"# Plaster ({canon})\n\n| Type | Set time | Best for |\n|------|----------|----------|\n| Gypsum | 30 min | Interiors |\n| Lime | Days | Heritage |\n| Cement | Hours | Exterior |\n\nConfidence: {conf}%"
    elif canon == "deepseek":
        answer = f"**Technical: Plaster**\n\nComposition: Binder 30-45%, sand 50-65%, water 15-20%.\n\nFailure modes: Debonding, cracking, efflorescence.\n\nConfidence: {conf}%"
    elif canon == "qwen":
        answer = f"**Plaster - Cross-cultural view**\n\n- China:ypsum board + powder\n- West: Gypsum dominates\n\nConfidence: {conf}%"
    else:
        answer = f"**{canon.title()} on Plaster**\n\nPlaster = wall makeup. Binder + sand + water -> hard, flat.\n\nConfidence: {conf}%"

    reasoning = f"Need to answer '{q[:80]}' for {canon}. Provide structured response."
    return f"<reasoning>{reasoning}</reasoning><answer>{answer}</answer>"

@app.get("/health")
async def health():
    return {"status":"ok","version":"1.0.0","bridge":"connected","db":"connected"}

@app.get("/")
async def root():
    return {"status":"ok","version":"1.0.0"}

@app.get("/v1/models")
async def list_models():
    return {"object":"list","data":MODELS}

@app.get("/models")
async def list_models_alt():
    return {"models": [{"id": INTERNAL_TO_CANON.get(m["id"], m["id"]), "display_name": m["id"], "internal_id": m["id"], "available": True} for m in MODELS]}

@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    body = await req.json()
    model = body.get("model","claude-sonnet-4-20250514")
    messages = body.get("messages",[])
    stream = body.get("stream", False)
    canon_to_internal = {v:k for k,v in INTERNAL_TO_CANON.items()}
    if model in canon_to_internal:
        model_internal = canon_to_internal[model]
    else:
        model_internal = model
    content = generate_mock_content(model_internal, messages)
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    if stream:
        async def gen():
            chunk_size = 40
            for i in range(0, len(content), chunk_size):
                piece = content[i:i+chunk_size]
                chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_internal,
                    "choices": [{"index":0,"delta":{"content": piece},"finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.03)
            final = {
                "id": chat_id,
                "object":"chat.completion.chunk",
                "created": created,
                "model": model_internal,
                "choices": [{"index":0,"delta":{},"finish_reason":"stop"}]
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no","Connection":"keep-alive"})
    else:
        return JSONResponse({
            "id": chat_id,
            "object":"chat.completion",
            "created": created,
            "model": model_internal,
            "choices": [{"index":0,"message":{"role":"assistant","content": content},"finish_reason":"stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": len(content)//4, "total_tokens": len(content)//4}
        })
