# Week 6 §12 — LLM Judge vs Human Score

Data source: `evaluation/human_eval.py` (`python -m evaluation.human_eval`),
scored against `reports/baseline_v1.json`. Full per-criterion breakdown in
`reports/human_vs_judge_comparison.json`.

**Honest scoping note:** the "human" scores here were assigned by the
developer (Hooria), not independent third-party evaluators — see
`docs/WEEK6_REPORT.md` §5 for why, and what the recommended next step is.
What *is* real: the comparison ran against the actual `baseline_v1`
responses (not synthetic data), scored on the same 5-criterion 1–5 rubric
the LLM judge uses, and the disagreement pattern below is a genuine finding
about this project's offline heuristic judge — not a fabricated result.

## Results (11 cases, exceeding the 10-case minimum)

| Test ID | Category | Human avg | Judge avg | Delta | Judge mode |
|---|---|---|---|---|---|
| A03 | A_normal | 3.40 | 3.00 | +0.40 | heuristic_fallback |
| A14 | A_normal | 4.80 | 3.00 | +1.80 | heuristic_fallback |
| B04 | B_difficult | 2.20 | 3.00 | −0.80 | heuristic_fallback |
| B07 | B_difficult | 1.80 | 3.00 | −1.20 | heuristic_fallback |
| C01 | C_ambiguous | 4.80 | 5.00 | −0.20 | heuristic_fallback |
| D03 | D_tool_use | 4.80 | 3.00 | +1.80 | heuristic_fallback |
| D09 | D_tool_use | 4.80 | 3.00 | +1.80 | heuristic_fallback |
| E01 | E_knowledge_rag | 4.80 | 3.00 | +1.80 | heuristic_fallback |
| E06 | E_knowledge_rag | 4.80 | 3.00 | +1.80 | heuristic_fallback |
| F01 | F_adversarial | 4.60 | 3.00 | +1.60 | heuristic_fallback |
| F07 | F_adversarial | 4.60 | 3.00 | +1.60 | heuristic_fallback |

**Summary statistics:**
- Mean absolute disagreement: **1.35** points (on a 1–5 scale — substantial)
- Human scored higher than the judge in 8/11 cases
- Judge scored higher than the human in 2/11 cases
- Close agreement (±0.25) in only 1/11 cases (C01)

## Discussion of disagreements

**The dominant pattern:** the offline heuristic judge (`evaluation/judge.py
_heuristic_score`, used because no live `GEMINI_API_KEY` was configured for
this submission) returns a **flat score of 3 for almost every criterion on
almost every case**, only deviating when a response contains an
uncertainty/clarification keyword (which pushes it to 5, as seen on C01) or
is unusually short/long (which shifts the `length_ok` base score). It is
explicitly *not* reading the response for actual correctness or
groundedness — it is a placeholder, and this comparison proves why that
matters:

- **On genuinely good, grounded answers (A14, D03, D09, E01, E06, F01,
  F07):** the human scorer rated these 4.6–4.8 (accurate, well-grounded,
  correctly refuses/complies as required), while the flat heuristic gave
  them all a 3.0. This is exactly the **verbosity/prompt-sensitivity
  blindness** predicted in §12 — a scoring method insensitive to content
  cannot distinguish a great answer from a mediocre one of similar length.
- **On genuinely broken responses (B04, B07):** the human scorer correctly
  penalized these (1.8–2.2 — B07 is a raw unhandled-fallback stub, B04
  answers the wrong question entirely), while the heuristic still gave them
  a flat 3.0, actually *overrating* broken output. This is the most
  concerning disagreement direction: **a judge that can't detect failure is
  worse than no judge**, because it would let real regressions through a
  regression-testing gate undetected.
- **Close agreement (C01):** the one case where both scored similarly is
  the one case where the heuristic's single actual quality signal (an
  uncertainty/clarification keyword match) happened to align with genuinely
  good behavior (asking for clarification on an ambiguous request). This is
  effectively luck, not evidence the heuristic works in general.

## Conclusion and required follow-up

This comparison is itself the clearest evidence in this project for why
§12's listed judge limitations matter in practice — specifically **model
bias** (a non-LLM heuristic has no real "judgement" at all) and **prompt/
content insensitivity**. It does **not** yet demonstrate the limitations a
*live* LLM judge would show (position bias, self-preference, real
inconsistent scoring across repeated calls) — those require
`evaluation/judge.py` to actually call Gemini (`--mode live` with a
configured `GEMINI_API_KEY`), which was not available for this submission.

**Recommended next step:** re-run `python -m evaluation.human_eval` after
running `python -m evaluation.runner --mode live` with a real API key, and
compare the *live* judge scores (not the heuristic fallback) against the
same human scores. The mechanism is already built and tested
(`test_human_vs_judge_comparison_covers_at_least_10_cases`) — only a funded
API key is needed to produce the live-mode numbers.
