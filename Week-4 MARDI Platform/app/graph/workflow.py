"""
Workflow Assembly — Requirement 7 / Section 7 architecture, wired with
LangGraph (Requirement 8, Section 8).

Graph shape (matches the assignment's suggested architecture, Section 7):

  analyze_request -> (clarify?) -> create_plan -> checkpoint_1
    -> [researcher A, researcher B, researcher C ...] (parallel, Send)
    -> analyst -> critic -> decide_after_critic
         -> (revision needed?) -> analyst   [loop, capped]
         -> (approved) -> writer -> checkpoint_2
              -> (approved) -> finalize -> END
              -> (request changes) -> analyst [loop, capped]

Why LangGraph: this project needs explicit workflow control (a real cycle
for the revision loop, a real fan-out/fan-in for parallel research, and a
single shared typed state) — exactly what LangGraph's StateGraph primitive
is built for, rather than a purely linear chain.

How agents communicate: exclusively through reads/writes to specific
WorkflowState fields (see app/graph/state.py), never raw message history.

How handoffs occur: each agent function returns a partial state update;
LangGraph merges it into the shared state via the reducers declared in
WorkflowState, and the graph's edges determine which agent runs next.

How loops are controlled: the `analyst -> critic -> decide_after_critic`
cycle is bounded by `revision_count` vs `max_revisions` in routing.py.

How failures are handled: agent functions catch tool/model errors and
return them into `state["errors"]` instead of raising; guard routing
functions (`route_after_analysis`, `route_after_writer`) short-circuit to
END if a prior step could not produce usable output, so a failure never
leaves the graph in a stuck or crashed state.
"""
from __future__ import annotations

from functools import partial
from typing import Optional

from langgraph.graph import END, StateGraph

from app.agents import analyst, critic, researcher, supervisor, writer
from app.graph import human, routing
from app.graph.state import WorkflowState


def build_workflow(callback: human.HumanCallback = human.auto_approve_callback):
    graph = StateGraph(WorkflowState)

    graph.add_node("analyze_request", supervisor.analyze_request)
    graph.add_node("clarify", partial(human.request_clarification, callback=callback))
    graph.add_node("create_plan", supervisor.create_plan)
    graph.add_node("checkpoint_1", partial(human.checkpoint_plan_approval, callback=callback))
    graph.add_node("researcher", researcher.research_task)
    graph.add_node("analyst", analyst.analyze)
    graph.add_node("critic", critic.review)
    graph.add_node("decide_after_critic", supervisor.decide_after_critic)
    graph.add_node("writer", writer.generate_report)
    graph.add_node("checkpoint_2", partial(human.checkpoint_final_review, callback=callback))
    graph.add_node("finalize", supervisor.finalize)

    graph.set_entry_point("analyze_request")

    graph.add_conditional_edges(
        "analyze_request", routing.route_after_request_analysis, ["clarify", "create_plan", END]
    )
    graph.add_edge("clarify", "create_plan")
    graph.add_edge("create_plan", "checkpoint_1")
    graph.add_conditional_edges("checkpoint_1", routing.dispatch_research, ["researcher", "analyst", END])
    graph.add_edge("researcher", "analyst")
    graph.add_conditional_edges("analyst", routing.route_after_analysis, ["critic", END])
    graph.add_conditional_edges("critic", routing.route_after_critic, ["decide_after_critic", END])
    graph.add_conditional_edges(
        "decide_after_critic", routing.route_after_critic_decision, ["analyst", "writer"]
    )
    graph.add_conditional_edges("writer", routing.route_after_writer, ["checkpoint_2", END])
    graph.add_conditional_edges(
        "checkpoint_2", routing.route_after_final_checkpoint, ["finalize", "analyst"]
    )
    graph.add_edge("finalize", END)

    return graph.compile()


def run_workflow(
    user_request: str,
    run_id: str,
    max_revisions: int = 2,
    callback: Optional[human.HumanCallback] = None,
):
    """Convenience entry point used by app/main.py and tests."""
    from app.graph.state import new_state

    app = build_workflow(callback or human.auto_approve_callback)
    initial_state = new_state(run_id=run_id, user_request=user_request, max_revisions=max_revisions)
    return app.invoke(initial_state, config={"recursion_limit": 60})
