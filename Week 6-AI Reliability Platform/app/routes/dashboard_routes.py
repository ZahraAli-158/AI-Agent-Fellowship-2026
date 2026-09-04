from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user

from app.models.models import db, Conversation, Message, Document, MemoryItem, PromptTemplate, Log
from app.routes.workspace_routes import get_accessible_workspace_or_404

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/workspaces/<int:workspace_id>/dashboard")


@dashboard_bp.route("/")
@login_required
def view_dashboard(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)

    total_conversations = Conversation.query.filter_by(workspace_id=ws.id).count()
    total_documents = Document.query.filter_by(workspace_id=ws.id).count()
    total_memory_items = MemoryItem.query.filter_by(workspace_id=ws.id).count()
    total_prompts = PromptTemplate.query.filter_by(user_id=current_user.id).count()

    logs = Log.query.filter_by(workspace_id=ws.id).order_by(Log.created_at.desc()).all()
    total_input_tokens = sum(l.input_tokens for l in logs)
    total_output_tokens = sum(l.output_tokens for l in logs)
    estimated_cost = sum(l.estimated_cost(current_app.config) for l in logs)
    avg_latency = round(sum(l.latency_ms for l in logs) / len(logs), 1) if logs else 0

    recent_activity = logs[:15]

    memory_items = (
        MemoryItem.query.filter_by(workspace_id=ws.id)
        .order_by(MemoryItem.is_pinned.desc(), MemoryItem.weight.desc())
        .limit(30).all()
    )

    stats = {
        "total_conversations": total_conversations,
        "total_documents": total_documents,
        "total_memory_items": total_memory_items,
        "total_prompts": total_prompts,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost": round(estimated_cost, 4),
        "avg_latency": avg_latency,
        "total_events": len(logs),
    }

    return render_template(
        "dashboard.html", ws=ws, stats=stats, recent_activity=recent_activity, memory_items=memory_items
    )


@dashboard_bp.route("/memory/<int:memory_id>/pin", methods=["POST"])
@login_required
def pin_memory(workspace_id, memory_id):
    get_accessible_workspace_or_404(workspace_id)
    item = MemoryItem.query.get_or_404(memory_id)
    item.is_pinned = not item.is_pinned
    db.session.commit()
    return jsonify({"is_pinned": item.is_pinned})


@dashboard_bp.route("/memory/<int:memory_id>/delete", methods=["POST"])
@login_required
def delete_memory(workspace_id, memory_id):
    get_accessible_workspace_or_404(workspace_id)
    item = MemoryItem.query.get_or_404(memory_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": True})


@dashboard_bp.route("/memory/add", methods=["POST"])
@login_required
def add_memory(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    content = (request.form.get("content") or "").strip()
    category = request.form.get("category", "pinned")
    if content:
        item = MemoryItem(workspace_id=ws.id, content=content, category=category, is_pinned=True)
        db.session.add(item)
        db.session.commit()
    return jsonify({"added": bool(content)})
