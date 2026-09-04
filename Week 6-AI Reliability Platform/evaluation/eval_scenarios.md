# Evaluation Framework

This document defines 40 evaluation scenarios for the AI Workspace Platform,
grouped into the seven required categories. Each scenario lists: the setup,
the action taken, and the pass criteria. `evaluation/eval_runner.py` automates
the scenarios that don't require a human judgment call (marked **[auto]**);
the rest are manual/human-graded checklists (marked **[manual]**), which is
standard practice for open-ended generative quality.

Metrics tracked across all scenarios: **Accuracy**, **Response Time**,
**Memory Recall**, **Citation Quality**, **Task Success**.

---

## 1. Knowledge Questions (6 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 1 | Ask the assistant a general-knowledge question with no documents uploaded | Assistant responds coherently without crashing **[auto]** |
| 2 | Ask a question requiring multi-step reasoning (e.g. "compare X and Y") | Response addresses both sides of the comparison **[manual]** |
| 3 | Ask the same question twice in one conversation | Second answer is consistent with the first **[manual]** |
| 4 | Ask a question outside the assistant's configured role (e.g. legal advice to a "Marketing Assistant") | Assistant stays in role or flags the mismatch **[manual]** |
| 5 | Ask an ambiguous question | Assistant asks a clarifying question or states its assumption **[manual]** |
| 6 | Send an empty message | Server rejects with 400, no message is stored **[auto]** |

## 2. Document Questions (6 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 7 | Upload a TXT file and ask a question answerable directly from it | Answer is grounded in the document, citation returned **[auto: citation present]** |
| 8 | Upload a PDF and ask for a summary | Non-empty summary generated at upload time **[auto]** |
| 9 | Ask a question about a document that was never uploaded | Assistant says it can't find relevant info **[manual]** |
| 10 | Upload two documents with overlapping topics, ask a question | Top result cites the most relevant document **[auto: citation score ranking]** |
| 11 | Ask a question in the chat with "Use knowledge base" unchecked | No citations returned even though documents exist **[auto]** |
| 12 | Delete a document, then ask a question that depended on it | Citations no longer reference the deleted document **[auto]** |

## 3. Memory Questions (6 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 13 | State a preference ("I like concise answers"), then ask a follow-up in a **new** conversation | Preference is recalled across sessions **[auto: memory_service]** |
| 14 | Pin a memory fact manually via the dashboard | Fact appears in the memory context for the next chat turn **[auto]** |
| 15 | Ask the same type of question repeatedly | Topic weight increments (frequently-asked topic tracking) **[auto]** |
| 16 | Delete a memory item, then check subsequent chat context | Deleted fact no longer appears in system prompt context **[auto]** |
| 17 | Fill memory with 20+ items, then chat | Only the top-weighted/pinned items are injected (context stays bounded) **[auto]** |
| 18 | Two different workspaces, same user | Memory in workspace A does not leak into workspace B **[auto]** |

## 4. Conversation Continuation (6 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 19 | Send 5 messages in a row in one conversation | All messages persist in order with correct timestamps **[auto]** |
| 20 | Refer back to something said 3 messages ago ("what did I just ask?") | Assistant correctly references prior turn **[manual]** |
| 21 | Rename a conversation mid-chat | New title persists and displays in sidebar **[auto]** |
| 22 | Pin/unpin a conversation | Pinned conversations sort to top of the list **[auto]** |
| 23 | Export a conversation as Markdown and PDF | Both downloads succeed and contain message text **[auto]** |
| 24 | Delete a conversation with messages | Conversation and all its messages are removed (cascade) **[auto]** |

## 5. Prompt Templates (5 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 25 | Save a new prompt template | Appears in the library under the correct category **[auto]** |
| 26 | Edit an existing template | Updated content persists **[auto]** |
| 27 | Use (load) a template | `use_count` increments; content returned to caller **[auto]** |
| 28 | Filter templates by category in the UI | Only matching cards remain visible **[manual: UI]** |
| 29 | Delete a template owned by another user (should fail) | Request is rejected / ignored, template remains **[auto]** |

## 6. Skill Invocation (6 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 30 | Run the Summarization skill on a long paragraph | Output is shorter than input and preserves key facts **[manual]** |
| 31 | Run the SWOT Generator on a business idea | Output contains all four SWOT quadrants **[manual]** |
| 32 | Run the Code Reviewer skill on a snippet with an obvious bug | Output identifies the bug **[manual]** |
| 33 | Run a skill with empty input | Request rejected with 400 **[auto]** |
| 34 | Run the same skill twice | Two separate `SkillExecution` rows are logged **[auto]** |
| 35 | Run a skill while offline (no Gemini key) | Offline-stub response returned, no crash **[auto]** |

## 7. Edge Cases (5 scenarios)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| 36 | Upload a file above the 25MB limit | Upload rejected gracefully **[manual]** |
| 37 | Upload a file with an unsupported extension | Flash error shown, no DB row created **[auto]** |
| 38 | Attempt to access another user's workspace by guessing its ID | 403 Forbidden returned **[auto]** |
| 39 | Submit the settings form with an out-of-range temperature (e.g. 99) | Value is clamped to the valid 0–2 range **[auto]** |
| 40 | Two users register with the same email in different case (`A@x.com` vs `a@x.com`) | Second registration is rejected as a duplicate **[auto]** |

---

## Running the automated subset

```bash
python evaluation/eval_runner.py
```

This spins up the app with an in-memory test config (offline Gemini stub for
determinism), runs every `[auto]` scenario above, and prints a pass/fail
report plus response-time stats.
