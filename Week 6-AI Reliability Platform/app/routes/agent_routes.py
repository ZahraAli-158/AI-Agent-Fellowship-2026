import uuid
import json

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user

from app.agents import registry
from app.models.models import db, AgentConversation, AgentMessage, AgentTask
from app.services import agent_service
from app.services.log_service import log_event

agent_bp = Blueprint("agent", __name__, url_prefix="/agents")


def get_agent_def_or_404(agent_key):
    agent_def = registry.get_agent(agent_key)
    if not agent_def:
        abort(404)
    return agent_def


def _get_owned_conversation(agent_key, conversation_id):
    convo = AgentConversation.query.get_or_404(conversation_id)
    if convo.user_id != current_user.id or convo.agent_key != agent_key:
        abort(404)
    return convo


@agent_bp.route("/")
@login_required
def list_agents():
    agents = registry.list_agents()
    task_counts = {}
    for a in agents:
        pending = AgentTask.query.filter_by(
            user_id=current_user.id, agent_key=a["key"], status="pending"
        ).count()
        task_counts[a["key"]] = pending
    return render_template("agents.html", agents=agents, task_counts=task_counts)


@agent_bp.route("/<agent_key>")
@login_required
def agent_detail(agent_key):
    agent_def = get_agent_def_or_404(agent_key)
    conversations = (
        AgentConversation.query.filter_by(user_id=current_user.id, agent_key=agent_key)
        .order_by(AgentConversation.updated_at.desc()).all()
    )
    tasks = (
        AgentTask.query.filter_by(user_id=current_user.id, agent_key=agent_key)
        .order_by(AgentTask.status.asc(), AgentTask.created_at.desc()).all()
    )
    return render_template("agent_detail.html", agent=agent_def, conversations=conversations, tasks=tasks)


# ---------------- Conversations ----------------

@agent_bp.route("/<agent_key>/conversations/new", methods=["POST"])
@login_required
def new_conversation(agent_key):
    get_agent_def_or_404(agent_key)
    convo = AgentConversation(user_id=current_user.id, agent_key=agent_key, session_id=uuid.uuid4().hex)
    db.session.add(convo)
    db.session.commit()
    return redirect(url_for("agent.open_conversation", agent_key=agent_key, conversation_id=convo.id))


@agent_bp.route("/<agent_key>/conversations/<int:conversation_id>")
@login_required
def open_conversation(agent_key, conversation_id):
    agent_def = get_agent_def_or_404(agent_key)
    convo = _get_owned_conversation(agent_key, conversation_id)
    conversations = (
        AgentConversation.query.filter_by(user_id=current_user.id, agent_key=agent_key)
        .order_by(AgentConversation.updated_at.desc()).all()
    )
    tasks = (
        AgentTask.query.filter_by(user_id=current_user.id, agent_key=agent_key)
        .order_by(AgentTask.status.asc(), AgentTask.created_at.desc()).all()
    )
    return render_template(
        "agent_chat.html", agent=agent_def, convo=convo, conversations=conversations, tasks=tasks
    )


@agent_bp.route("/<agent_key>/conversations/<int:conversation_id>/send", methods=["POST"])
@login_required
def send_message(agent_key, conversation_id):
    get_agent_def_or_404(agent_key)
    convo = _get_owned_conversation(agent_key, conversation_id)
    user_text = (request.form.get("message") or "").strip()

    if not user_text:
        return jsonify({"error": "Empty message"}), 400

    user_msg = AgentMessage(conversation_id=convo.id, role="user", content=user_text)
    db.session.add(user_msg)

    if convo.title in (None, "New conversation"):
        convo.title = user_text[:60] + ("..." if len(user_text) > 60 else "")

    history = [{"role": m.role, "content": m.content} for m in convo.messages if m.role in ("user", "assistant")]

    # A tool is "approved" for this turn only if the user explicitly ticked
    # a confirmation checkbox in the UI before sending (e.g.
    # approved_tools=delete_task,email_task_summary) — the model calling a
    # high-risk tool is never itself sufficient authorization (Week 6 §28).
    approved_tools = set(filter(None, (request.form.get("approved_tools") or "").split(",")))

    result = agent_service.run_agent_turn(
        agent_key=agent_key,
        user_id=current_user.id,
        user_email=current_user.email,
        history=history[-20:],
        user_message=user_text,
        approved_tools=approved_tools,
        session_id=convo.session_id,
    )

    assistant_msg = AgentMessage(
        conversation_id=convo.id, role="assistant", content=result["text"],
        tool_calls=json.dumps(result.get("tool_calls", [])),
    )
    db.session.add(assistant_msg)
    db.session.commit()

    log_event(
        "agent", f"Message to {agent_key} agent (conversation {convo.id})",
        user_id=current_user.id, input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0), latency_ms=result.get("latency_ms", 0),
    )

    return jsonify({
        "assistant_message": {
            "content": result["text"],
            "tool_calls": result.get("tool_calls", []),
        },
        "conversation_title": convo.title,
    })


@agent_bp.route("/<agent_key>/conversations/<int:conversation_id>/rename", methods=["POST"])
@login_required
def rename_conversation(agent_key, conversation_id):
    convo = _get_owned_conversation(agent_key, conversation_id)
    new_title = (request.form.get("title") or "").strip()
    if new_title:
        convo.title = new_title[:200]
        db.session.commit()
    return redirect(url_for("agent.open_conversation", agent_key=agent_key, conversation_id=convo.id))


@agent_bp.route("/<agent_key>/conversations/<int:conversation_id>/delete", methods=["POST"])
@login_required
def delete_conversation(agent_key, conversation_id):
    convo = _get_owned_conversation(agent_key, conversation_id)
    db.session.delete(convo)
    db.session.commit()
    flash("Conversation deleted.", "info")
    return redirect(url_for("agent.agent_detail", agent_key=agent_key))


# ---------------- Tasks (manual management, in addition to agent tools) ----------------

@agent_bp.route("/<agent_key>/tasks.json")
@login_required
def tasks_json(agent_key):
    get_agent_def_or_404(agent_key)
    tasks = (
        AgentTask.query.filter_by(user_id=current_user.id, agent_key=agent_key)
        .order_by(AgentTask.status.asc(), AgentTask.created_at.desc()).all()
    )
    return jsonify({"tasks": [t.to_dict() for t in tasks]})


@agent_bp.route("/<agent_key>/tasks/create", methods=["POST"])
@login_required
def create_task(agent_key):
    get_agent_def_or_404(agent_key)
    title = (request.form.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    from app.services.agent_service import _parse_date
    task = AgentTask(
        user_id=current_user.id, agent_key=agent_key, title=title,
        description=(request.form.get("description") or "").strip(),
        due_date=_parse_date(request.form.get("due_date", "")),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"task": task.to_dict()})


@agent_bp.route("/<agent_key>/tasks/<int:task_id>/complete", methods=["POST"])
@login_required
def complete_task(agent_key, task_id):
    task = AgentTask.query.filter_by(id=task_id, user_id=current_user.id, agent_key=agent_key).first_or_404()
    task.status = "completed" if task.status != "completed" else "pending"
    db.session.commit()
    return jsonify({"task": task.to_dict()})


@agent_bp.route("/<agent_key>/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(agent_key, task_id):
    task = AgentTask.query.filter_by(id=task_id, user_id=current_user.id, agent_key=agent_key).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({"deleted": True})
