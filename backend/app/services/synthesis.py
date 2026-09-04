import json
import re
import structlog

log = structlog.get_logger()


def parse_synthesis(raw: str) -> tuple[str, str | None, str | None, list[str] | None]:
    # Try JSON first
    raw_stripped = raw.strip()
    # handle ```json ... ``` fences
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_stripped, flags=re.DOTALL | re.IGNORECASE)
    if m:
        raw_stripped = m.group(1)
    try:
        data = json.loads(raw_stripped)
        if isinstance(data, dict) and "synthesis" in data:
            synthesis = str(data.get("synthesis", "")).strip()
            agreements = str(data.get("agreements", "")).strip() or None
            divergences = str(data.get("divergences", "")).strip() or None
            insights = data.get("unique_insights")
            if isinstance(insights, list):
                insights = [str(x) for x in insights]
            else:
                insights = None
            if synthesis:
                return synthesis, agreements, divergences, insights
    except Exception as e:
        log.info("synthesis json parse failed, fallback to regex", error=str(e))

    # Fallback markdown heuristics
    synthesis = raw.strip()
    agreements = None
    divergences = None
    insights = None

    # try to extract headings
    m_agree = re.search(r"#{1,3}\s*Agreements?[:\s]*\n(.*?)(?=\n#{1,3}|\Z)", raw, flags=re.DOTALL | re.IGNORECASE)
    if m_agree:
        agreements = m_agree.group(1).strip()
    m_div = re.search(r"#{1,3}\s*Divergences?[:\s]*\n(.*?)(?=\n#{1,3}|\Z)", raw, flags=re.DOTALL | re.IGNORECASE)
    if m_div:
        divergences = m_div.group(1).strip()
    # insights: bullet list under Unique Insights
    m_ins = re.search(r"#{1,3}\s*Unique[ _-]*Insights?[:\s]*\n(.*?)(?=\n#{1,3}|\Z)", raw, flags=re.DOTALL | re.IGNORECASE)
    if m_ins:
        block = m_ins.group(1).strip()
        insights = [line.strip("-•* ").strip() for line in block.splitlines() if line.strip().startswith(("-", "•", "*")) or line.strip()]
        insights = [x for x in insights if x]
        if not insights:
            insights = [block] if block else None

    return synthesis, agreements, divergences, insights
