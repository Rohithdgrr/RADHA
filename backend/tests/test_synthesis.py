import json
from app.services.synthesis import parse_synthesis


def test_parse_json():
    raw = json.dumps({"synthesis": "S", "agreements": "A", "divergences": "D", "unique_insights": ["U1"]})
    s, a, d, i = parse_synthesis(raw)
    assert s == "S"
    assert a == "A"
    assert d == "D"
    assert i == ["U1"]


def test_parse_fenced_json():
    raw = "```json\n" + json.dumps({"synthesis": "S2", "agreements": "", "divergences": "", "unique_insights": []}) + "\n```"
    s, _, _, _ = parse_synthesis(raw)
    assert s == "S2"


def test_parse_markdown_fallback():
    raw = "# Synthesis\nHello world\n## Agreements\nAgree A\n## Divergences\nDiverge D"
    s, a, d, i = parse_synthesis(raw)
    assert "Hello world" in s
    assert a is not None
