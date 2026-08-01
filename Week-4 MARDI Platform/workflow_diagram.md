# Workflow Diagram

This matches the exact graph built in `app/graph/workflow.py` — every node
and edge here is a real node/edge in the code, not a simplified summary.

```mermaid
flowchart TD
    Start([User Request]) --> AR[analyze_request<br/>Supervisor]
    AR -->|needs_clarification| CL[clarify<br/>Human Checkpoint]
    AR -->|clear request| CP[create_plan<br/>Supervisor]
    AR -->|failed| End1([END - Failed])
    CL --> CP

    CP --> CK1[checkpoint_1<br/>Human: Plan Approval]
    CK1 -->|approved/edited| Dispatch{{dispatch_research<br/>Send fan-out}}
    CK1 -->|rejected| End2([END - Failed])

    Dispatch -->|parallel| R1[researcher<br/>Target A]
    Dispatch -->|parallel| R2[researcher<br/>Target B]
    Dispatch -->|parallel| R3[researcher<br/>Target C]

    R1 --> AN[analyst<br/>Analyst]
    R2 --> AN
    R3 --> AN

    AN -->|evidence found| CR[critic<br/>Critic]
    AN -->|no evidence| End3([END - Failed<br/>missing_evidence])

    CR --> DEC[decide_after_critic<br/>Supervisor]
    DEC -->|revision needed<br/>under cap| AN
    DEC -->|approved OR<br/>cap reached| WR[writer<br/>Writer]

    WR -->|report generated| CK2[checkpoint_2<br/>Human: Final Review]
    WR -->|failed| End4([END - Failed])

    CK2 -->|approved| FIN[finalize<br/>Supervisor]
    CK2 -->|request changes<br/>under cap| AN

    FIN --> End5([END - Completed])

    style Start fill:#6366f1,color:#fff
    style End1 fill:#f43f5e,color:#fff
    style End2 fill:#f43f5e,color:#fff
    style End3 fill:#f43f5e,color:#fff
    style End4 fill:#f43f5e,color:#fff
    style End5 fill:#14b8a6,color:#fff
    style Dispatch fill:#f59e0b,color:#fff
    style CK1 fill:#8b5cf6,color:#fff
    style CK2 fill:#8b5cf6,color:#fff
```

## Legend

- **Diamond (dispatch_research)** — conditional edge that returns a list of `Send` objects, one per ready research task, fanning out to parallel `researcher` invocations (Requirement 11).
- **Purple nodes (checkpoint_1, checkpoint_2)** — Human-in-the-Loop checkpoints (Requirement 12); these block the executing thread on a `threading.Event` until the frontend resolves them.
- **Red END nodes** — every terminal failure path is a *clean*, traceable termination (`workflow_status = failed` + a structured error in `state.errors`), never a crash (Requirement 14).
- **The Analyst ↔ Critic loop** — bounded by `max_revisions`; `decide_after_critic` is what actually enforces the cap via the `revision_forced_stop` flag (Requirement 10 — see `docs/experiment_5_revision_limits.md` for the off-by-one bug this fixed).

## Why this shape (vs. the assignment's suggested architecture)

The assignment's suggested architecture (Section 7) is:

```
User Request → Supervisor → Request Analysis → (Clarification? → User) → Research Plan
  → Research Task A / B → Evidence Store → Analyst → Critic
  → (Revision? → Research/Analyst | Approved → Writer) → Final Report → Execution Log
```

This implementation matches that shape almost exactly, with two additions:
a second human checkpoint after the Writer (Requirement 12 asks for *at
least two* checkpoints), and an explicit `decide_after_critic` node
separating "was a revision requested" from "is a revision still allowed"
so the cap enforcement is a single, testable function (see
`app/graph/routing.py::route_after_critic_decision`).
