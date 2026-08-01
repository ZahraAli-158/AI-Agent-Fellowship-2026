"""
CLI entry point — runs the full multi-agent workflow end-to-end for a
given request, using the interactive human-checkpoint callback by default.

Usage:
    python -m app.main "Research the current open-source agent frameworks
    and recommend one for a small engineering team."

    python -m app.main --auto "..."     # non-interactive (auto-approves checkpoints)
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid

from app.config import settings
from app.graph import human
from app.graph.workflow import run_workflow
from app.observability.logging_config import configure_logging
from app.observability.tracer import summarize_run


def main() -> None:
    configure_logging()  # wires the LOG_LEVEL env var into Python's logging module

    parser = argparse.ArgumentParser(description="Multi-Agent Research and Decision Intelligence Platform")
    parser.add_argument("request", type=str, help="The research/decision request")
    parser.add_argument("--auto", action="store_true", help="Auto-approve all human checkpoints")
    parser.add_argument("--max-revisions", type=int, default=settings.max_revisions)
    args = parser.parse_args()

    callback = human.auto_approve_callback if (args.auto or settings.auto_approve_checkpoints) else human.cli_callback
    run_id = f"RUN-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"

    print(f"LLM mode: {settings.resolved_llm_mode()}")
    print(f"Run ID: {run_id}\n")

    final_state = run_workflow(
        user_request=args.request, run_id=run_id, max_revisions=args.max_revisions, callback=callback
    )

    print("\n================= WORKFLOW STATUS =================")
    print(f"Status: {final_state.get('workflow_status')}")
    print(f"Revisions used: {final_state.get('revision_count')} / {final_state.get('max_revisions')}")
    print(f"Evidence collected: {len(final_state.get('evidence', []))}")
    print(f"Errors: {len(final_state.get('errors', []))}")

    summary = summarize_run(run_id, final_state.get("trace", []))
    print("\n================= EXECUTION SUMMARY =================")
    for k, v in summary.items():
        print(f"{k}: {v}")

    report = final_state.get("final_report")
    if report:
        print("\n================= FINAL REPORT (Markdown) =================\n")
        print(report.to_markdown())
    else:
        print("\nNo final report was produced. See errors above.", file=sys.stderr)


if __name__ == "__main__":
    main()
