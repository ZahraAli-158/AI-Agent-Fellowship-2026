from tests.conftest import register, create_workspace


def test_create_workspace(client, db):
    register(client)
    resp = create_workspace(client, name="Marketing Hub", category="Marketing")
    assert resp.status_code == 200
    from app.models.models import Workspace
    ws = Workspace.query.filter_by(name="Marketing Hub").first()
    assert ws is not None
    assert ws.category == "Marketing"
    assert ws.assistant_name == "Marketing Hub Assistant"


def test_workspace_isolated_per_user(client, db, app):
    register(client, username="alice", email="alice@example.com")
    create_workspace(client, name="Alice WS")
    client.get("/logout")

    register(client, username="bob", email="bob@example.com")
    from app.models.models import Workspace
    with app.app_context():
        alice_ws = Workspace.query.filter_by(name="Alice WS").first()
    resp = client.get(f"/workspaces/{alice_ws.id}")
    assert resp.status_code == 403


def test_update_assistant_settings(client, db):
    register(client)
    create_workspace(client, name="Config Test")
    from app.models.models import Workspace
    ws = Workspace.query.filter_by(name="Config Test").first()

    resp = client.post(f"/workspaces/{ws.id}/settings", data={
        "assistant_name": "Custom Bot", "assistant_role": "Data helper",
        "system_prompt": "Be precise.", "model": "gemini-3.1-pro-preview",
        "personality": "Formal", "response_style": "Detailed",
        "temperature": "1.2", "max_tokens": "2048",
    }, follow_redirects=True)
    assert resp.status_code == 200

    updated = Workspace.query.get(ws.id)
    assert updated.assistant_name == "Custom Bot"
    assert updated.temperature == 1.2
    assert updated.max_tokens == 2048


def test_delete_workspace(client, db):
    register(client)
    create_workspace(client, name="Temp WS")
    from app.models.models import Workspace
    ws = Workspace.query.filter_by(name="Temp WS").first()
    ws_id = ws.id

    client.post(f"/workspaces/{ws_id}/delete", follow_redirects=True)
    assert Workspace.query.get(ws_id) is None
