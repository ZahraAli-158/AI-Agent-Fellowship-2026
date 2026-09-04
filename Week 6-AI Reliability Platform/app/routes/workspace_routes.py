from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user

from app.models.models import db, Workspace, Conversation, WorkspaceShare, User
from app.services.log_service import log_event

workspace_bp = Blueprint("workspace", __name__, url_prefix="/workspaces")

WORKSPACE_CATEGORIES = ["Marketing", "Research", "Programming", "University", "Business", "Custom"]


def get_owned_workspace_or_404(workspace_id):
    """Strict check: only the workspace owner may proceed. Used for settings,
    deletion, and managing sharing itself."""
    ws = Workspace.query.get_or_404(workspace_id)
    if ws.user_id != current_user.id:
        abort(403)
    return ws


def get_accessible_workspace_or_404(workspace_id):
    """Owner OR a shared collaborator may proceed. Used for chat, knowledge
    base, prompts, skills, and the dashboard (Advanced feature: Workspace
    Sharing)."""
    ws = Workspace.query.get_or_404(workspace_id)
    if ws.user_id == current_user.id:
        return ws
    shared = WorkspaceShare.query.filter_by(workspace_id=ws.id, user_id=current_user.id).first()
    if shared:
        return ws
    abort(403)


@workspace_bp.route("/")
@login_required
def list_workspaces():
    owned = Workspace.query.filter_by(user_id=current_user.id).all()
    shared_links = WorkspaceShare.query.filter_by(user_id=current_user.id).all()
    shared = [link.workspace for link in shared_links]

    # Favorites first, then most recently created, for both groups.
    owned.sort(key=lambda w: (not w.is_favorite, w.created_at), reverse=False)
    owned.sort(key=lambda w: w.is_favorite, reverse=True)

    return render_template(
        "workspaces.html", workspaces=owned, shared_workspaces=shared, categories=WORKSPACE_CATEGORIES
    )


@workspace_bp.route("/create", methods=["POST"])
@login_required
def create_workspace():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Custom")

    if not name:
        flash("Workspace name is required.", "error")
        return redirect(url_for("workspace.list_workspaces"))

    ws = Workspace(
        user_id=current_user.id,
        name=name,
        category=category,
        assistant_name=f"{name} Assistant",
        assistant_role=f"A helpful assistant specialized in {category.lower()} tasks.",
    )
    db.session.add(ws)
    db.session.commit()
    log_event("workspace", f"Created workspace '{name}'", user_id=current_user.id, workspace_id=ws.id)
    flash(f"Workspace '{name}' created.", "success")
    return redirect(url_for("workspace.view_workspace", workspace_id=ws.id))


@workspace_bp.route("/<int:workspace_id>")
@login_required
def view_workspace(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    is_owner = ws.user_id == current_user.id
    conversations = (
        Conversation.query.filter_by(workspace_id=ws.id)
        .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
        .all()
    )
    return render_template("workspace_detail.html", ws=ws, conversations=conversations, is_owner=is_owner)


@workspace_bp.route("/<int:workspace_id>/settings", methods=["POST"])
@login_required
def update_settings(workspace_id):
    ws = get_owned_workspace_or_404(workspace_id)

    ws.assistant_name = request.form.get("assistant_name", ws.assistant_name).strip()
    ws.assistant_role = request.form.get("assistant_role", ws.assistant_role).strip()
    ws.system_prompt = request.form.get("system_prompt", ws.system_prompt).strip()
    ws.model = request.form.get("model", ws.model)
    ws.personality = request.form.get("personality", ws.personality).strip()
    ws.response_style = request.form.get("response_style", ws.response_style).strip()

    try:
        ws.temperature = max(0.0, min(2.0, float(request.form.get("temperature", ws.temperature))))
    except ValueError:
        pass
    try:
        ws.max_tokens = max(64, min(8192, int(request.form.get("max_tokens", ws.max_tokens))))
    except ValueError:
        pass

    db.session.commit()
    log_event("workspace", "Updated assistant configuration", user_id=current_user.id, workspace_id=ws.id)
    flash("Assistant settings saved.", "success")
    return redirect(url_for("workspace.view_workspace", workspace_id=ws.id, tab="settings"))


@workspace_bp.route("/<int:workspace_id>/delete", methods=["POST"])
@login_required
def delete_workspace(workspace_id):
    ws = get_owned_workspace_or_404(workspace_id)
    name = ws.name
    db.session.delete(ws)
    db.session.commit()
    log_event("workspace", f"Deleted workspace '{name}'", user_id=current_user.id)
    flash(f"Workspace '{name}' deleted.", "info")
    return redirect(url_for("workspace.list_workspaces"))


# ---------------- Advanced feature: Bookmarks / Favorites ----------------

@workspace_bp.route("/<int:workspace_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(workspace_id):
    ws = get_owned_workspace_or_404(workspace_id)
    ws.is_favorite = not ws.is_favorite
    db.session.commit()
    return jsonify({"is_favorite": ws.is_favorite})


# ---------------- Advanced feature: Workspace Sharing ----------------

@workspace_bp.route("/<int:workspace_id>/share", methods=["POST"])
@login_required
def share_workspace(workspace_id):
    ws = get_owned_workspace_or_404(workspace_id)
    identifier = (request.form.get("identifier") or "").strip()

    if not identifier:
        flash("Enter a username or email to share with.", "error")
        return redirect(url_for("workspace.view_workspace", workspace_id=ws.id, tab="sharing"))

    target = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not target:
        flash(f"No user found matching '{identifier}'.", "error")
    elif target.id == current_user.id:
        flash("You already own this workspace.", "error")
    elif WorkspaceShare.query.filter_by(workspace_id=ws.id, user_id=target.id).first():
        flash(f"'{target.username}' already has access.", "info")
    else:
        share = WorkspaceShare(workspace_id=ws.id, user_id=target.id, role="collaborator")
        db.session.add(share)
        db.session.commit()
        log_event("workspace", f"Shared workspace with '{target.username}'",
                   user_id=current_user.id, workspace_id=ws.id)
        flash(f"Workspace shared with '{target.username}'.", "success")

    return redirect(url_for("workspace.view_workspace", workspace_id=ws.id, tab="sharing"))


@workspace_bp.route("/<int:workspace_id>/share/<int:share_id>/revoke", methods=["POST"])
@login_required
def revoke_share(workspace_id, share_id):
    ws = get_owned_workspace_or_404(workspace_id)
    share = WorkspaceShare.query.get_or_404(share_id)
    if share.workspace_id != ws.id:
        abort(404)
    db.session.delete(share)
    db.session.commit()
    flash("Access revoked.", "info")
    return redirect(url_for("workspace.view_workspace", workspace_id=ws.id, tab="sharing"))
