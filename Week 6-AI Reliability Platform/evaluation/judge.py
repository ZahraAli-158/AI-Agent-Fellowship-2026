"""
LLM-as-a-Judge (Week 6, Requirement 11).

Scores subjective criteria (relevance, correctness, completeness, clarity,
groundedness) on a 1-5 scale via a structured-output prompt to Gemini. Falls
back to a small heuristic scorer when no API key is configured, so the
evaluation pipeline still runs end-to-end offline (see
app/services/gemini_service.py's offline-stub pattern, which this mirrors).

Documented judge prompt: JUDGE_PROMPT_TEMPLATE below IS the judge prompt
used, verbatim, in every judged call (Week 6 §11: "Document the judge
prompt.").
"""
import json
import re

from app.services import gemini_service

JUDGE_PROMPT_TEMPLATE = """You are an impartial evaluator scoring an AI assistant's response.

User request:
{user_input}

Expected behavior (from the evaluation dataset, for reference only — do not \
quote it back):
{expected_behavior}

Assistant's actual response:
{response_text}

Score the response on each criterion from 1 (very poor) to 5 (excellent):
- correctness: is the content factually correct given what is knowable here?
- relevance: does it actually address the user's request?
- completeness: does it cover what the request needed, without major gaps?
- clarity: is it well-organized and easy to understand?
- groundedness: if it relies on retrieved context, is it faithful to that \
context rather than inventing details?

Respond with ONLY a JSON object, no other text, in exactly this shape:
{{"correctness": <1-5>, "relevance": <1-5>, "completeness": <1-5>, "clarity": <1-5>, \
"groundedness": <1-5>, "rationale": "<one sentence>"}}
"""

CRITERIA = ["correctness", "relevance", "completeness", "clarity", "groundedness"]


def _heuristic_score(case, response_text):
    """Offline fallback used when Gemini isn't configured. Deliberately
    simple and clearly labelled as a stub — this is NOT a substitute for the
    real LLM judge, only a way to keep the pipeline runnable without an API
    key (mirrors gemini_service's offline-stub convention)."""
    text = response_text or ""
    length_ok = 10 < len(text) < 3000
    mentions_uncertainty = bool(re.search(r"\b(not sure|don't know|unclear|clarify)\b", text, re.IGNORECASE))
    base = 3 if length_ok else 2
    scores = {c: base for c in CRITERIA}
    if case.get("category") == "C_ambiguous" and mentions_uncertainty:
        for c in scores:
            scores[c] = 5
    return {**scores, "rationale": "offline heuristic fallback (no GEMINI_API_KEY configured)",
             "judge_mode": "heuristic_fallback"}


def judge_response(case, response_text, model="gemini-3.6-flash"):
    """Returns a dict with the 5 criteria scores (1-5), a rationale, and
    judge_mode ('llm' or 'heuristic_fallback')."""
    if not gemini_service.is_configured():
        return _heuristic_score(case, response_text)

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        user_input=case.get("user_input", ""), expected_behavior=case.get("expected_behavior", ""),
        response_text=response_text or "",
    )
    result = gemini_service.chat_completion(
        system_prompt="You are a strict, consistent evaluation judge that only outputs JSON.",
        history=[], user_message=prompt, model=model, temperature=0.0, max_tokens=300,
    )
    raw = result.get("text", "")
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        fallback = _heuristic_score(case, response_text)
        fallback["judge_mode"] = "heuristic_fallback_parse_error"
        return fallback
    try:
        parsed = json.loads(match.group(0))
        for c in CRITERIA:
            parsed[c] = max(1, min(5, int(parsed.get(c, 3))))
        parsed["judge_mode"] = "llm"
        return parsed
    except (json.JSONDecodeError, ValueError, TypeError):
        fallback = _heuristic_score(case, response_text)
        fallback["judge_mode"] = "heuristic_fallback_parse_error"
        return fallback


def average_score(judge_result: dict) -> float:
    vals = [judge_result.get(c, 3) for c in CRITERIA]
    return round(sum(vals) / len(vals), 2)


# ---------------------------------------------------------------------------
# Known LLM judge limitations (Week 6 §12) — documented here so the runner
# can attach this note to every generated report.
# ---------------------------------------------------------------------------
JUDGE_LIMITATIONS = """
LLM-as-a-Judge limitations considered in this evaluation:
1. Model bias — the judge may systematically favor answers phrased the way
   its own training data phrases things, independent of actual quality.
2. Position bias — when comparing two responses, judges tend to favor
   whichever is presented first/second depending on the model; this
   pipeline avoids pairwise comparison for that reason and scores each
   response independently against the case, not against another response.
3. Verbosity bias — longer answers are often scored higher even when they
   aren't more correct or complete; length is not itself a scoring criterion
   here, but the judge can still be swayed by it implicitly.
4. Self-preference — if the judge model and the model being evaluated are
   the same family (both Gemini here), the judge may rate its own family's
   phrasing more favorably than an independent judge would.
5. Inconsistent scoring — the same response can receive different scores on
   repeated judge calls; temperature is fixed to 0.0 here to reduce (not
   eliminate) this.
6. Prompt sensitivity — small wording changes to JUDGE_PROMPT_TEMPLATE can
   shift scores; the template is version-controlled and unchanged across a
   single evaluation run for that reason.
"""
