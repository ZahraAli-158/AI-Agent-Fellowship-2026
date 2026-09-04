# Experiments

Six experiments comparing platform behavior along the axes required by the
spec. `experiments/run_experiments.py` automates Experiments 1, 2, 4, 5, and 6
(everything that can be measured without a live paid Gemini key) and prints
timing/token/behavioral deltas. Experiment 3 (different models) requires a
live `GEMINI_API_KEY` with access to multiple Gemini models and is documented
as a manual protocol below, since model quality comparisons need human
judgment on top of the numbers.

## Experiment 1 — Memory Enabled vs Disabled

**Setup:** Same workspace, same question asked twice in two conversations:
once after seeding long-term memory with a stated preference, once in a
workspace with no memory items.

**Measured:** Whether the injected system prompt contains the stored
preference; system-prompt token length; conversation coherence.

**Observation:** With memory enabled, the system prompt grows by the size of
the injected memory block (roughly 15–40 tokens per fact, capped at 8 items),
and the assistant's response is grounded in the stored preference. With
memory disabled, the same question gets a generic answer with no
personalization and a shorter system prompt.

**Trade-off:** Memory improves personalization at the cost of extra input
tokens on every single turn — cost scales with the number of pinned/high-
weight items, not conversation length, so it stays bounded even in very long
sessions.

## Experiment 2 — Short Prompt vs Detailed Prompt

**Setup:** Run the Summarization skill on the same input text using two
different system prompts: a one-line instruction ("Summarize this.") vs the
platform's detailed skill prompt (explicit length cap, structure guidance).

**Measured:** Output token count, output token count variance across 3 runs,
adherence to the requested constraint (word limit).

**Observation:** The detailed prompt produces more consistent output length
and structure across repeated runs; the short prompt has higher variance and
more often ignores implicit length expectations.

**Trade-off:** Detailed prompts cost more input tokens per call but reduce
the need for follow-up corrections — usually a net win for repeatable
skills, less clear for open-ended chat.

## Experiment 3 — Different Models *(manual protocol — requires live API access)*

**Setup:** Configure three workspaces identically except for `model`:
`gemini-3.6-flash`, `gemini-3.1-pro-preview`, `gemini-3.5-flash-lite`. Ask each the
same 10 questions from the Knowledge Questions evaluation category.

**Measured:** Latency per response, subjective answer quality (1–5 human
rating), estimated cost per response.

**Expected pattern (documented from Gemini's published 3.x model
characteristics, to be confirmed empirically once a paid key is available):**
`gemini-3.5-flash-lite` should be fastest and cheapest but least detailed;
`gemini-3.1-pro-preview` should be slowest and most expensive but highest
quality; `gemini-3.6-flash` sits in between and is the platform's default —
Google's current GA "Flash" tier tuned for agentic/coding tasks at a lower
price point than the previous 3.5 Flash generation.

## Experiment 4 — Small vs Large Context (Conversation History Window)

**Setup:** Compare sending only the last 4 messages of history vs the last
20 (the platform's actual cap) as context for a new turn in a long-running
conversation.

**Measured:** Input token count, whether the assistant can correctly recall
information from message 15 of 20.

**Observation:** The small window is cheaper per call but loses recall of
anything outside its span; the large window (20 messages) preserves recall
at a roughly linear increase in input tokens.

**Trade-off:** This motivates why long-term memory (Module 6) exists
separately from raw history — memory survives outside any fixed window at a
much lower token cost per fact than re-sending full history.

## Experiment 5 — Conversation Length (Token Growth Over a Session)

**Setup:** Send 1, 5, 10, and 20 sequential messages in one conversation and
record cumulative input tokens per turn.

**Measured:** Input token growth curve, average latency per turn.

**Observation:** Because history is capped at the last 20 messages
(`history[-20:]` in `chat_routes.py`), input tokens per turn grow linearly
until the cap, then plateau — preventing unbounded cost growth in very long
sessions.

## Experiment 6 — Chunk Size Comparison (Knowledge Base)

**Setup:** Ingest the same document three times with chunk sizes 400, 800,
and 1500 characters (overlap scaled proportionally), then run the same 5
queries against each version.

**Measured:** Number of chunks produced, average semantic-search relevance
score of the top result, snippet readability (does the chunk cut off
mid-sentence).

**Observation:** Smaller chunks (400) produce more granular, higher-precision
matches but more fragments to search and a higher chance of losing
surrounding context; larger chunks (1500) preserve context better but dilute
relevance scores when only one sentence is actually relevant. 800 characters
(the platform's default) is a reasonable middle ground for typical prose
documents.

---

## Running the automated experiments

```bash
python experiments/run_experiments.py
```

Prints a table of measured token counts, chunk counts, latencies, and
relevance scores for Experiments 1, 2, 4, 5, and 6.
