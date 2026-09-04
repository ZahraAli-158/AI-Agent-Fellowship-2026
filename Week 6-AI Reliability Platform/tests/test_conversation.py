from tests.conftest import register, create_workspace


def _make_workspace(client):
    register(client)
    create_workspace(client, name="Chat WS")
    from app.models.models import Workspace
    return Workspace.query.filter_by(name="Chat WS").first()


def test_create_conversation(client, db):
    ws = _make_workspace(client)
    resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    assert resp.status_code == 302
    from app.models.models import Conversation
    assert Conversation.query.filter_by(workspace_id=ws.id).count() == 1


def test_send_message_offline_stub(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    resp = client.post(f"/workspaces/{ws.id}/chat/{convo_id}/send", data={"message": "Hello there"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["assistant_message"]["content"]
    assert payload["user_message"]["content"] == "Hello there"


def test_conversation_title_updates_from_first_message(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    client.post(f"/workspaces/{ws.id}/chat/{convo_id}/send", data={"message": "What is machine learning?"})
    from app.models.models import Conversation
    convo = Conversation.query.get(int(convo_id))
    assert convo.title.startswith("What is machine learning")


def test_rename_conversation(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    client.post(f"/workspaces/{ws.id}/chat/{convo_id}/rename", data={"title": "Renamed Chat"}, follow_redirects=True)
    from app.models.models import Conversation
    convo = Conversation.query.get(int(convo_id))
    assert convo.title == "Renamed Chat"


def test_pin_conversation_toggle(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    resp = client.post(f"/workspaces/{ws.id}/chat/{convo_id}/pin")
    assert resp.get_json()["is_pinned"] is True
    resp2 = client.post(f"/workspaces/{ws.id}/chat/{convo_id}/pin")
    assert resp2.get_json()["is_pinned"] is False


def test_delete_conversation(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    client.post(f"/workspaces/{ws.id}/chat/{convo_id}/delete", follow_redirects=True)
    from app.models.models import Conversation
    assert Conversation.query.get(int(convo_id)) is None


def test_export_conversation_markdown(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]
    client.post(f"/workspaces/{ws.id}/chat/{convo_id}/send", data={"message": "Export test"})

    resp = client.get(f"/workspaces/{ws.id}/chat/{convo_id}/export?format=markdown")
    assert resp.status_code == 200
    assert b"Export test" in resp.data
