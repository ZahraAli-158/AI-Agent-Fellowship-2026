from tests.conftest import register, create_workspace


def _make_workspace(client):
    register(client)
    create_workspace(client, name="Memory WS")
    from app.models.models import Workspace
    return Workspace.query.filter_by(name="Memory WS").first()


def test_memory_extracted_from_chat_message(client, db):
    ws = _make_workspace(client)
    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    client.post(f"/workspaces/{ws.id}/chat/{convo_id}/send", data={"message": "I like concise answers"})

    from app.models.models import MemoryItem
    items = MemoryItem.query.filter_by(workspace_id=ws.id, category="preference").all()
    assert len(items) >= 1


def test_pin_memory_manually(client, db):
    ws = _make_workspace(client)
    resp = client.post(f"/workspaces/{ws.id}/dashboard/memory/add", data={"content": "Always use bullet points"})
    assert resp.get_json()["added"] is True

    from app.models.models import MemoryItem
    item = MemoryItem.query.filter_by(workspace_id=ws.id).first()
    assert item.is_pinned is True


def test_memory_context_included_in_prompt(client, db, app):
    ws = _make_workspace(client)
    client.post(f"/workspaces/{ws.id}/dashboard/memory/add", data={"content": "User's favorite color is teal"})

    with app.app_context():
        from app.services.memory_service import get_relevant_memory_context
        context = get_relevant_memory_context(ws.id)
        assert "teal" in context


def test_delete_memory_item(client, db):
    ws = _make_workspace(client)
    client.post(f"/workspaces/{ws.id}/dashboard/memory/add", data={"content": "Temporary fact"})
    from app.models.models import MemoryItem
    item = MemoryItem.query.filter_by(workspace_id=ws.id).first()

    client.post(f"/workspaces/{ws.id}/dashboard/memory/{item.id}/delete")
    assert MemoryItem.query.get(item.id) is None
