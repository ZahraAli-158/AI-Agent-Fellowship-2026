# Tool Permission Boundaries

Per Requirement 5 (Section 13).

| Agent | Search | Database (state) | Calculator | Report Export |
|---|:---:|:---:|:---:|:---:|
| Supervisor | No | Yes | No | No |
| Researcher | Yes | Yes | No | No |
| Analyst | No | Yes | Yes | No |
| Critic | No | Yes | No | No |
| Writer | No | Yes | No | Yes |

## Why each permission was granted or withheld

- **Supervisor — no Search**: it must never do research itself (explicit
  requirement in Section 5); giving it Search would let it silently
  shortcut the Researcher agents.
- **Researcher — Search + Database, no Calculator/Export**: its whole job
  is retrieval; it has no reason to compute scores or format a report.
- **Analyst — Calculator, no Search**: it must work only from evidence the
  Researchers already gathered (never independently pull in new sources
  the Critic hasn't seen), but legitimately needs to compute weighted
  comparison scores.
- **Critic — nothing but Database (read)**: it evaluates the Analyst's
  reasoning and evidence coverage; it has no legitimate reason to search
  or calculate anything itself, and giving it Search would blur "review
  the work done" with "redo the work."
- **Writer — Report Export, no Search**: per Requirement 4's explicit
  example ("the Report Writer Agent should not have unrestricted web
  search access"), it must only synthesize already-validated state.

"Database" here means read/write access to the shared `WorkflowState` via
normal LangGraph node returns — not a literal external database in this
version (see `app/tools/evidence.py` docstring for how this would be
swapped for a real store).
