import re

MODEL_CANONICAL = ["claude", "chatgpt", "gemini", "deepseek", "qwen", "kimi", "kimi-k2.5", "kimi-k3", "grok", "llama"]


def reasoning_system_prompt(model: str, depth: str = "detailed", show_reasoning: bool = True) -> str:
    depth_instr = {
        "brief": "Keep <answer> to 80-120 words.",
        "standard": "Keep <answer> to 150-250 words.",
        "detailed": "Keep <answer> to 300-500 words, with bullet points and structure where helpful.",
    }.get(depth, "")

    if show_reasoning:
        return (
            f"You are Council member {model}. Think step by step but output EXACTLY:\n"
            "<reasoning>your private chain-of-thought, brief but thorough</reasoning>\n"
            "<answer>final answer for user</answer>\n"
            'At the very end add a line: "Confidence: XX%" where XX is 0-100 self-assessed confidence.\n'
            f"{depth_instr}\n"
            "Do not deviate from <reasoning>/<answer> tags."
        )
    else:
        return (
            f"You are {model}. Answer concisely. {depth_instr} "
            'At the very end add a line: "Confidence: XX%" where XX is 0-100.'
        )


def build_synthesis_prompt(query: str, responses: list[dict], mode: str = "consensus") -> str:
    # responses: [{"model": "claude", "answer": "..."}]
    joined = "\n\n".join([f"[{r['model']}]: {r.get('answer','')}" for r in responses])
    return (
        "You are the chair of an AI council. Here are responses from council members regarding:\n"
        f'User Query: "{query}"\n\n'
        f"Responses:\n{joined}\n\n"
        "Synthesize a unified final answer. Return JSON with keys:\n"
        '{"synthesis": "unified answer markdown", '
        '"agreements": "bulleted where all models agree", '
        '"divergences": "where they diverge and why", '
        '"unique_insights": ["point only one model made", ...]}\n'
        "Return ONLY JSON, no extra text. If you cannot, fallback to markdown with headings ## Synthesis etc."
    )


def parse_reasoning_answer(raw: str) -> tuple[str | None, str, float | None]:
    reasoning = None
    confidence = None
    m = re.search(r"<reasoning>(.*?)</reasoning>", raw, flags=re.DOTALL | re.IGNORECASE)
    if m:
        reasoning = m.group(1).strip() or None
    # answer
    m2 = re.search(r"<answer>(.*?)</answer>", raw, flags=re.DOTALL | re.IGNORECASE)
    if m2:
        answer = m2.group(1).strip()
    else:
        # fallback: strip reasoning block if present
        answer = re.sub(r"<reasoning>.*?</reasoning>", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()
    # confidence
    cm = re.search(r"Confidence:\s*(\d{1,3})\s*%", answer, flags=re.IGNORECASE)
    if cm:
        try:
            v = int(cm.group(1))
            v = max(0, min(100, v))
            confidence = v / 100.0
        except Exception:
            confidence = None
        # keep line? leave in answer for transparency
    return reasoning, answer, confidence
