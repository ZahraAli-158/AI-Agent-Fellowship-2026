from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from app.models.models import db, PromptTemplate
from app.services.log_service import log_event

prompt_bp = Blueprint("prompt", __name__, url_prefix="/workspaces/<int:workspace_id>/prompts")

PROMPT_CATEGORIES = ["Writing", "Programming", "Research", "Business", "Education", "Custom"]


@prompt_bp.route("/")
@login_required
def list_prompts(workspace_id):
    from app.routes.workspace_routes import get_accessible_workspace_or_404
    ws = get_accessible_workspace_or_404(workspace_id)
    prompts = (
        PromptTemplate.query.filter_by(user_id=current_user.id)
        .order_by(PromptTemplate.updated_at.desc()).all()
    )
    return render_template("prompts.html", ws=ws, prompts=prompts, categories=PROMPT_CATEGORIES)


@prompt_bp.route("/create", methods=["POST"])
@login_required
def create_prompt(workspace_id):
    title = (request.form.get("title") or "").strip()
    category = request.form.get("category", "Custom")
    content = (request.form.get("content") or "").strip()

    if not title or not content:
        flash("Title and content are required.", "error")
        return redirect(url_for("prompt.list_prompts", workspace_id=workspace_id))

    template = PromptTemplate(
        user_id=current_user.id, workspace_id=workspace_id, title=title,
        category=category, content=content,
    )
    db.session.add(template)
    db.session.commit()
    log_event("prompt", f"Created prompt template '{title}'", user_id=current_user.id, workspace_id=workspace_id)
    flash("Prompt template saved.", "success")
    return redirect(url_for("prompt.list_prompts", workspace_id=workspace_id))


@prompt_bp.route("/<int:prompt_id>/edit", methods=["POST"])
@login_required
def edit_prompt(workspace_id, prompt_id):
    template = PromptTemplate.query.get_or_404(prompt_id)
    if template.user_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("prompt.list_prompts", workspace_id=workspace_id))

    template.title = (request.form.get("title") or template.title).strip()
    template.category = request.form.get("category", template.category)
    template.content = (request.form.get("content") or template.content).strip()
    db.session.commit()
    flash("Prompt template updated.", "success")
    return redirect(url_for("prompt.list_prompts", workspace_id=workspace_id))


@prompt_bp.route("/<int:prompt_id>/delete", methods=["POST"])
@login_required
def delete_prompt(workspace_id, prompt_id):
    template = PromptTemplate.query.get_or_404(prompt_id)
    if template.user_id == current_user.id:
        db.session.delete(template)
        db.session.commit()
        flash("Prompt template deleted.", "info")
    return redirect(url_for("prompt.list_prompts", workspace_id=workspace_id))


@prompt_bp.route("/<int:prompt_id>/use", methods=["POST"])
@login_required
def use_prompt(workspace_id, prompt_id):
    template = PromptTemplate.query.get_or_404(prompt_id)
    if template.user_id != current_user.id:
        return jsonify({"error": "not authorized"}), 403
    template.use_count += 1
    db.session.commit()
    return jsonify({"content": template.content})
