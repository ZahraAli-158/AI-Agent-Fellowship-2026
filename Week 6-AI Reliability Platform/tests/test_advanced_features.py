from tests.conftest import register, create_workspace


def _make_workspace(client, name="Advanced WS"):
    register(client)
    create_workspace(client, name=name)
    from app.models.models import Workspace
    return Workspace.query.filter_by(name=name).first()


# ---------------- Bookmarks / Favorites ----------------

def test_toggle_workspace_favorite(client, db):
    ws = _make_workspace(client)
    resp = client.post(f"/workspaces/{ws.id}/favorite")
    assert resp.get_json()["is_favorite"] is True

    resp2 = client.post(f"/workspaces/{ws.id}/favorite")
    assert resp2.get_json()["is_favorite"] is False


def test_favorite_requires_ownership(client, db):
    ws = _make_workspace(client, name="Owner WS")
    client.get("/logout")
    register(client, username="intruder", email="intruder@example.com")

    resp = client.post(f"/workspaces/{ws.id}/favorite")
    assert resp.status_code == 403


# ---------------- Workspace Sharing ----------------

def test_share_workspace_with_existing_user(client, db, app):
    ws = _make_workspace(client, name="Shared WS")
    client.get("/logout")
    register(client, username="collaborator", email="collab@example.com")
    client.get("/logout")
    client.post("/login", data={"identifier": ws.owner.username, "password": "password123"})

    resp = client.post(f"/workspaces/{ws.id}/share", data={"identifier": "collaborator"}, follow_redirects=True)
    assert resp.status_code == 200

    from app.models.models import WorkspaceShare
    share = WorkspaceShare.query.filter_by(workspace_id=ws.id).first()
    assert share is not None
    assert share.role == "collaborator"


def test_shared_collaborator_can_access_workspace(client, db):
    ws = _make_workspace(client, name="Access WS")
    owner_username = ws.owner.username
    client.get("/logout")
    register(client, username="collaborator2", email="collab2@example.com")
    client.get("/logout")
    client.post("/login", data={"identifier": owner_username, "password": "password123"})
    client.post(f"/workspaces/{ws.id}/share", data={"identifier": "collaborator2"})

    client.get("/logout")
    client.post("/login", data={"identifier": "collaborator2", "password": "password123"})
    resp = client.get(f"/workspaces/{ws.id}")
    assert resp.status_code == 200

    # But settings/delete stay owner-only
    resp2 = client.post(f"/workspaces/{ws.id}/delete")
    assert resp2.status_code == 403


def test_non_collaborator_still_forbidden(client, db):
    ws = _make_workspace(client, name="Private WS")
    client.get("/logout")
    register(client, username="stranger", email="stranger@example.com")
    resp = client.get(f"/workspaces/{ws.id}")
    assert resp.status_code == 403


def test_revoke_share_removes_access(client, db):
    ws = _make_workspace(client, name="Revoke WS")
    owner_username = ws.owner.username
    client.get("/logout")
    register(client, username="collaborator3", email="collab3@example.com")
    client.get("/logout")
    client.post("/login", data={"identifier": owner_username, "password": "password123"})
    client.post(f"/workspaces/{ws.id}/share", data={"identifier": "collaborator3"})

    from app.models.models import WorkspaceShare
    share = WorkspaceShare.query.filter_by(workspace_id=ws.id).first()
    client.post(f"/workspaces/{ws.id}/share/{share.id}/revoke")

    client.get("/logout")
    client.post("/login", data={"identifier": "collaborator3", "password": "password123"})
    resp = client.get(f"/workspaces/{ws.id}")
    assert resp.status_code == 403


# ---------------- Tagging ----------------

def test_update_conversation_tags(client, db):
    ws = _make_workspace(client, name="Tag WS")
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    resp = client.post(f"/workspaces/{ws.id}/chat/{convo_id}/tags", data={"tags": "urgent, client-x, urgent"})
    payload = resp.get_json()
    assert payload["tags"] == "urgent, client-x"  # deduplicated


def test_tags_capped_at_eight(client, db):
    ws = _make_workspace(client, name="Tag Cap WS")
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    many_tags = ",".join(f"tag{i}" for i in range(12))
    resp = client.post(f"/workspaces/{ws.id}/chat/{convo_id}/tags", data={"tags": many_tags})
    payload = resp.get_json()
    assert len(payload["tags"].split(",")) == 8


# ---------------- Pinned Messages ----------------

def test_pin_individual_message(client, db):
    ws = _make_workspace(client, name="Pin Msg WS")
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]
    client.post(f"/workspaces/{ws.id}/chat/{convo_id}/send", data={"message": "Pin me"})

    from app.models.models import Message, Conversation
    convo = Conversation.query.get(int(convo_id))
    msg = convo.messages[0]

    resp = client.post(f"/workspaces/{ws.id}/chat/message/{msg.id}/pin")
    assert resp.get_json()["is_pinned"] is True

    resp2 = client.post(f"/workspaces/{ws.id}/chat/message/{msg.id}/pin")
    assert resp2.get_json()["is_pinned"] is False
