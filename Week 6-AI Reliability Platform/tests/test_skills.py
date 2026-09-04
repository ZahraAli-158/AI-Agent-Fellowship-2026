from tests.conftest import register, create_workspace


def _make_workspace(client):
    register(client)
    create_workspace(client, name="Skill WS")
    from app.models.models import Workspace
    return Workspace.query.filter_by(name="Skill WS").first()


def test_default_skills_seeded(app):
    with app.app_context():
        from app.models.models import Skill
        skills = Skill.query.all()
        assert len(skills) >= 6
        keys = {s.key for s in skills}
        assert "summarization" in keys
        assert "code_reviewer" in keys


def test_run_summarization_skill(client, db):
    ws = _make_workspace(client)
    from app.models.models import Skill
    skill = Skill.query.filter_by(key="summarization").first()

    resp = client.post(f"/workspaces/{ws.id}/skills/{skill.id}/run", data={
        "input_text": "This is a long piece of text that needs summarizing for the test.",
    })
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["output"]


def test_skill_run_requires_input(client, db):
    ws = _make_workspace(client)
    from app.models.models import Skill
    skill = Skill.query.filter_by(key="research").first()

    resp = client.post(f"/workspaces/{ws.id}/skills/{skill.id}/run", data={"input_text": ""})
    assert resp.status_code == 400


def test_skill_execution_logged(client, db):
    ws = _make_workspace(client)
    from app.models.models import Skill, SkillExecution
    skill = Skill.query.filter_by(key="idea_generator").first()

    client.post(f"/workspaces/{ws.id}/skills/{skill.id}/run", data={"input_text": "eco-friendly packaging"})

    executions = SkillExecution.query.filter_by(workspace_id=ws.id, skill_id=skill.id).all()
    assert len(executions) == 1
    assert executions[0].input_text == "eco-friendly packaging"
