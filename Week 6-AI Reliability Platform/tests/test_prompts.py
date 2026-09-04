from tests.conftest import register, create_workspace


def _make_workspace(client):
    register(client)
    create_workspace(client, name="Prompt WS")
    from app.models.models import Workspace
    return Workspace.query.filter_by(name="Prompt WS").first()


def test_create_prompt_template(client, db):
    ws = _make_workspace(client)
    resp = client.post(f"/workspaces/{ws.id}/prompts/create", data={
        "title": "Blog outline", "category": "Writing", "content": "Write an outline for {topic}",
    }, follow_redirects=True)
    assert resp.status_code == 200

    from app.models.models import PromptTemplate
    tpl = PromptTemplate.query.filter_by(title="Blog outline").first()
    assert tpl is not None
    assert tpl.category == "Writing"


def test_edit_prompt_template(client, db):
    ws = _make_workspace(client)
    client.post(f"/workspaces/{ws.id}/prompts/create", data={
        "title": "Original", "category": "Custom", "content": "content v1",
    })
    from app.models.models import PromptTemplate
    tpl = PromptTemplate.query.filter_by(title="Original").first()

    client.post(f"/workspaces/{ws.id}/prompts/{tpl.id}/edit", data={
        "title": "Updated", "category": "Business", "content": "content v2",
    }, follow_redirects=True)

    updated = PromptTemplate.query.get(tpl.id)
    assert updated.title == "Updated"
    assert updated.content == "content v2"


def test_delete_prompt_template(client, db):
    ws = _make_workspace(client)
    client.post(f"/workspaces/{ws.id}/prompts/create", data={
        "title": "To delete", "category": "Custom", "content": "delete me",
    })
    from app.models.models import PromptTemplate
    tpl = PromptTemplate.query.filter_by(title="To delete").first()

    client.post(f"/workspaces/{ws.id}/prompts/{tpl.id}/delete", follow_redirects=True)
    assert PromptTemplate.query.get(tpl.id) is None


def test_use_prompt_increments_counter(client, db):
    ws = _make_workspace(client)
    client.post(f"/workspaces/{ws.id}/prompts/create", data={
        "title": "Reusable", "category": "Custom", "content": "reuse this",
    })
    from app.models.models import PromptTemplate
    tpl = PromptTemplate.query.filter_by(title="Reusable").first()
    assert tpl.use_count == 0

    resp = client.post(f"/workspaces/{ws.id}/prompts/{tpl.id}/use")
    assert resp.get_json()["content"] == "reuse this"

    updated = PromptTemplate.query.get(tpl.id)
    assert updated.use_count == 1
