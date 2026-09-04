"""
Cost tracking (Week 6, Requirement 21).

Centralizes cost math so the dashboard, the evaluation runner, and tracing
all agree on one formula. Rates come from app.config so they stay in one
place (config.py) rather than being duplicated across modules.
"""

DEFAULT_INPUT_RATE = 0.000075   # USD per 1K input tokens
DEFAULT_OUTPUT_RATE = 0.0003    # USD per 1K output tokens


def estimate_cost(input_tokens, output_tokens, input_rate=DEFAULT_INPUT_RATE,
                   output_rate=DEFAULT_OUTPUT_RATE):
    return round((input_tokens / 1000.0) * input_rate + (output_tokens / 1000.0) * output_rate, 6)


def estimate_cost_breakdown(input_tokens, output_tokens, input_rate=DEFAULT_INPUT_RATE,
                              output_rate=DEFAULT_OUTPUT_RATE):
    """Per-request cost breakdown (Week 6 §34: "Record: ... Estimated input
    cost, Estimated output cost, Total estimated cost"). Input/output cost
    are deterministic from token counts and the configured rates, so they
    are computed here rather than persisted as separate DB columns —
    recomputing is cheap and keeps the two numbers always consistent with
    the rates currently in effect."""
    input_cost = round((input_tokens / 1000.0) * input_rate, 6)
    output_cost = round((output_tokens / 1000.0) * output_rate, 6)
    return {"input_cost": input_cost, "output_cost": output_cost,
             "total_cost": round(input_cost + output_cost, 6)}


def cost_per_successful_task(total_cost, successful_tasks):
    if successful_tasks <= 0:
        return None
    return round(total_cost / successful_tasks, 6)


def aggregate_cost(records):
    """`records` is an iterable of dicts/rows with input_tokens/output_tokens
    (or a precomputed estimated_cost). Returns a summary dict."""
    total_cost = 0.0
    total_input = 0
    total_output = 0
    n = 0
    for r in records:
        get = r.get if isinstance(r, dict) else (lambda k, d=None: getattr(r, k, d))
        cost = get("estimated_cost")
        if cost is None:
            cost = estimate_cost(get("input_tokens", 0) or 0, get("output_tokens", 0) or 0)
        total_cost += cost
        total_input += get("input_tokens", 0) or 0
        total_output += get("output_tokens", 0) or 0
        n += 1
    return {
        "requests": n,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_estimated_cost": round(total_cost, 6),
        "avg_cost_per_request": round(total_cost / n, 6) if n else 0.0,
    }


def _group_cost(records, key_fn):
    """Shared helper for cost-by-X breakdowns (Week 6 §34: "Aggregate: ...
    Cost by model, Cost by agent, Cost by feature")."""
    groups = {}
    for r in records:
        get = r.get if isinstance(r, dict) else (lambda k, d=None: getattr(r, k, d))
        key = key_fn(r) or "(none)"
        bucket = groups.setdefault(key, [])
        bucket.append(r)
    return {key: aggregate_cost(recs) for key, recs in groups.items()}


def cost_by_model(records):
    get = lambda r: r.get("model") if isinstance(r, dict) else getattr(r, "model", None)
    return _group_cost(records, get)


def cost_by_agent(records):
    """Only records with request_type == 'agent' have a meaningful
    agent_key; everything else is grouped under '(non-agent)'."""
    def key(r):
        get = r.get if isinstance(r, dict) else (lambda k, d=None: getattr(r, k, d))
        if get("request_type") != "agent":
            return "(non-agent)"
        return get("agent_key") or "(unspecified agent)"
    return _group_cost(records, key)


def cost_by_feature(records):
    """'Feature' = request_type (chat / agent / rag / eval) — the closest
    equivalent this platform has to distinct product features."""
    get = lambda r: r.get("request_type") if isinstance(r, dict) else getattr(r, "request_type", None)
    return _group_cost(records, get)
