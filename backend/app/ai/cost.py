import hashlib
from typing import List, Dict, Any, Optional


# Cost per 1k tokens in USD (estimates based on official pricing)
PRICING_PER_1K = {
    "gemini": {
        "input": 0.000125,
        "output": 0.000375,
    },
    "grok": {
        "input": 0.005,
        "output": 0.015,
    },
    "default": {
        "input": 0.001,
        "output": 0.002,
    }
}


def compute_input_hash(
    finding_id: str,
    title: str,
    source_rule_id: Optional[str],
    code_snippet: Optional[str],
    evidence_items: List[Dict[str, Any]],
    prompt_version: str = "v1.0"
) -> str:
    """
    Computes a deterministic SHA-256 hash representing the full analytical input of a finding.
    Used for caching and duplicate call suppression to minimize unnecessary LLM token spend.
    """
    hasher = hashlib.sha256()
    hasher.update(str(finding_id).encode("utf-8"))
    hasher.update((title or "").strip().encode("utf-8"))
    hasher.update((source_rule_id or "").strip().encode("utf-8"))
    hasher.update((code_snippet or "").strip().encode("utf-8"))
    hasher.update(prompt_version.encode("utf-8"))

    # Include evidence identifiers and content hashes
    for ev in sorted(evidence_items, key=lambda x: str(x.get("id", ""))):
        ev_id = str(ev.get("id", ""))
        ev_title = str(ev.get("title", ""))
        ev_content = str(ev.get("content", ""))
        hasher.update(ev_id.encode("utf-8"))
        hasher.update(ev_title.encode("utf-8"))
        hasher.update(ev_content[:500].encode("utf-8"))

    return hasher.hexdigest()


def truncate_context(text: Optional[str], max_chars: int = 12000) -> str:
    """
    Ensures input strings do not blow up token budgets or context limits.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        f"{text[:half]}\n\n"
        f"[... TRUNCATED {len(text) - max_chars} CHARACTERS FOR TOKEN BUDGET ...]\n\n"
        f"{text[-half:]}"
    )


def calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculates estimated USD cost for an AI run given provider and token counts.
    """
    rates = PRICING_PER_1K.get(provider.lower(), PRICING_PER_1K["default"])
    cost_in = (input_tokens / 1000.0) * rates["input"]
    cost_out = (output_tokens / 1000.0) * rates["output"]
    return round(cost_in + cost_out, 6)
