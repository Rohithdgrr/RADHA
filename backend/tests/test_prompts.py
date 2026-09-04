from app.services.prompts import reasoning_system_prompt, build_synthesis_prompt, parse_reasoning_answer


def test_prompts_have_tags():
    p = reasoning_system_prompt("claude", depth="detailed", show_reasoning=True)
    assert "<reasoning>" in p and "<answer>" in p
    assert "Confidence:" in p
    p2 = reasoning_system_prompt("claude", depth="brief", show_reasoning=False)
    assert "<reasoning>" not in p2


def test_parse_reasoning_answer():
    raw = "<reasoning>think</reasoning>\n<answer>Hello world\nConfidence: 85%</answer>"
    reasoning, answer, conf = parse_reasoning_answer(raw)
    assert reasoning == "think"
    assert "Hello world" in answer
    assert conf == 0.85


def test_build_synthesis_contains_query():
    prompt = build_synthesis_prompt("What is AI?", [{"model": "claude", "answer": "AI is ..."}])
    assert "What is AI?" in prompt
    assert "claude" in prompt
