import time
import uuid

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from app.models.models import db, Skill, SkillExecution, Conversation, Message
from app.services import gemini_service, skill_service
from app.services.log_service import log_event
from app.routes.workspace_routes import get_accessible_workspace_or_404

skill_bp = Blueprint("skill", __name__, url_prefix="/workspaces/<int:workspace_id>/skills")


@skill_bp.route("/")
@login_required
def list_skills(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    skills = Skill.query.order_by(Skill.name).all()
    recent = (
        SkillExecution.query.filter_by(workspace_id=ws.id)
        .order_by(SkillExecution.created_at.desc()).limit(10).all()
    )
    return render_template("skills.html", ws=ws, skills=skills, recent=recent)


@skill_bp.route("/<int:skill_id>/run", methods=["POST"])
@login_required
def run_skill(workspace_id, skill_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    skill = Skill.query.get_or_404(skill_id)
    input_text = (request.form.get("input_text") or "").strip()

    if not input_text:
        return jsonify({"error": "Input text is required"}), 400

    start = time.time()
    prompt = skill_service.build_skill_prompt(skill, input_text)
    # Skills often produce longer structured output (canvases, reports, SWOT
    # grids) than a normal chat reply, so give them extra headroom beyond
    # the workspace's configured max_tokens rather than letting a low
    # chat-tuned setting silently truncate the result.
    skill_max_tokens = max(ws.max_tokens, 2048)
    result = gemini_service.chat_completion(
        system_prompt=f"You are executing the '{skill.name}' skill precisely and helpfully.",
        history=[], user_message=prompt, model=ws.model, temperature=ws.temperature,
        max_tokens=skill_max_tokens,
    )
    duration_ms = int((time.time() - start) * 1000)

    execution = SkillExecution(
        skill_id=skill.id, workspace_id=ws.id, input_text=input_text,
        output_text=result["text"], duration_ms=duration_ms,
    )
    db.session.add(execution)
    db.session.commit()

    log_event("skill", f"Ran skill '{skill.name}'", user_id=current_user.id, workspace_id=ws.id,
              input_tokens=result["input_tokens"], output_tokens=result["output_tokens"],
              latency_ms=duration_ms)

    return jsonify({"output": result["text"], "duration_ms": duration_ms})


@skill_bp.route("/execution/<int:execution_id>")
@login_required
def get_execution(workspace_id, execution_id):
    """Fetch a past skill run's full (untruncated) input/output — powers the
    'reopen a recent run' modal."""
    ws = get_accessible_workspace_or_404(workspace_id)
    execution = SkillExecution.query.get_or_404(execution_id)
    if execution.workspace_id != ws.id:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": execution.id,
        "skill_id": execution.skill_id,
        "skill_name": execution.skill.name if execution.skill else "Skill",
        "skill_icon": execution.skill.icon if execution.skill else "🧩",
        "input_text": execution.input_text,
        "output_text": execution.output_text,
        "created_at": execution.created_at.strftime("%b %d, %Y %H:%M"),
        "duration_ms": execution.duration_ms,
    })


@skill_bp.route("/execution/<int:execution_id>/continue-chat", methods=["POST"])
@login_required
def continue_in_chat(workspace_id, execution_id):
    """Turns a past skill run into the opening exchange of a new conversation
    so the user can keep talking about that output with the full chat
    interface (memory, knowledge base, follow-up questions, etc.)."""
    ws = get_accessible_workspace_or_404(workspace_id)
    execution = SkillExecution.query.get_or_404(execution_id)
    if execution.workspace_id != ws.id:
        return jsonify({"error": "not found"}), 404

    skill_name = execution.skill.name if execution.skill else "Skill"
    title = f"{skill_name}: {execution.input_text[:40]}"
    if len(execution.input_text) > 40:
        title += "..."

    convo = Conversation(workspace_id=ws.id, title=title[:200], session_id=uuid.uuid4().hex)
    db.session.add(convo)
    db.session.flush()

    user_msg = Message(
        conversation_id=convo.id, role="user",
        content=f"(Continuing from the **{skill_name}** skill)\n\n{execution.input_text}",
    )
    assistant_msg = Message(conversation_id=convo.id, role="assistant", content=execution.output_text)
    db.session.add_all([user_msg, assistant_msg])
    db.session.commit()

    return jsonify({"redirect": url_for("chat.open_conversation", workspace_id=ws.id, conversation_id=convo.id)})
