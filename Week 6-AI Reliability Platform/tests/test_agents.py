from tests.conftest import register


def _register_and_login(client, username="agentuser", email="agent@example.com"):
    register(client, username=username, email=email)


def test_agents_gallery_lists_meeting_agent(client, db):
    _register_and_login(client)
    resp = client.get("/agents/")
    assert resp.status_code == 200
    assert b"Meeting Agent" in resp.data


def test_agent_detail_page_loads(client, db):
    _register_and_login(client)
    resp = client.get("/agents/meeting")
    assert resp.status_code == 200


def test_unknown_agent_key_404s(client, db):
    _register_and_login(client)
    resp = client.get("/agents/nonexistent")
    assert resp.status_code == 404


def test_create_agent_conversation(client, db):
    _register_and_login(client)
    resp = client.post("/agents/meeting/conversations/new", follow_redirects=False)
    assert resp.status_code == 302

    from app.models.models import AgentConversation
    assert AgentConversation.query.count() == 1


def test_send_message_offline_mode_gives_honest_answer(client, db):
    """With no GEMINI_API_KEY configured (the test config), the agent must
    say tool-calling isn't available rather than pretending to work."""
    _register_and_login(client)
    convo_resp = client.post("/agents/meeting/conversations/new", follow_redirects=False)
    convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]

    resp = client.post(f"/agents/meeting/conversations/{convo_id}/send", data={"message": "hello"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert "Gemini API key" in payload["assistant_message"]["content"]
    assert payload["assistant_message"]["tool_calls"] == []


def test_create_task_manually(client, db):
    _register_and_login(client)
    resp = client.post("/agents/meeting/tasks/create", data={"title": "Email the client", "due_date": "2026-09-01"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["task"]["title"] == "Email the client"
    assert payload["task"]["due_date"] == "2026-09-01"
    assert payload["task"]["status"] == "pending"


def test_create_task_requires_title(client, db):
    _register_and_login(client)
    resp = client.post("/agents/meeting/tasks/create", data={"title": ""})
    assert resp.status_code == 400


def test_complete_task_toggle(client, db):
    _register_and_login(client)
    client.post("/agents/meeting/tasks/create", data={"title": "Toggle me"})
    from app.models.models import AgentTask
    task = AgentTask.query.first()

    resp = client.post(f"/agents/meeting/tasks/{task.id}/complete")
    assert resp.get_json()["task"]["status"] == "completed"

    resp2 = client.post(f"/agents/meeting/tasks/{task.id}/complete")
    assert resp2.get_json()["task"]["status"] == "pending"


def test_delete_task(client, db):
    _register_and_login(client)
    client.post("/agents/meeting/tasks/create", data={"title": "Delete me"})
    from app.models.models import AgentTask
    task = AgentTask.query.first()
    task_id = task.id

    client.post(f"/agents/meeting/tasks/{task_id}/delete")
    assert AgentTask.query.get(task_id) is None


def test_tasks_json_endpoint(client, db):
    _register_and_login(client)
    client.post("/agents/meeting/tasks/create", data={"title": "Task A"})
    client.post("/agents/meeting/tasks/create", data={"title": "Task B"})

    resp = client.get("/agents/meeting/tasks.json")
    payload = resp.get_json()
    assert len(payload["tasks"]) == 2


def test_tasks_are_isolated_per_user(client, db, app):
    _register_and_login(client, username="alice_agent", email="alice_agent@example.com")
    client.post("/agents/meeting/tasks/create", data={"title": "Alice's task"})
    client.get("/logout")

    _register_and_login(client, username="bob_agent", email="bob_agent@example.com")
    resp = client.get("/agents/meeting/tasks.json")
    payload = resp.get_json()
    assert len(payload["tasks"]) == 0  # Bob shouldn't see Alice's task


def test_cannot_complete_another_users_task(client, db):
    _register_and_login(client, username="owner_agent", email="owner_agent@example.com")
    client.post("/agents/meeting/tasks/create", data={"title": "Owner's task"})
    from app.models.models import AgentTask
    task = AgentTask.query.first()
    task_id = task.id

    client.get("/logout")
    _register_and_login(client, username="intruder_agent", email="intruder_agent@example.com")
    resp = client.post(f"/agents/meeting/tasks/{task_id}/complete")
    assert resp.status_code == 404


def test_meeting_agent_tools_directly(client, db, app):
    """Unit-level test of the tool functions themselves (create/list/update/
    complete/delete), independent of any live Gemini call. delete_task and
    send_email_summary are L4/L3 risk tools (Week 6 permissions gate) so
    approved_tools must include them here to exercise the "approved" path;
    see tests/test_week6_agent_permissions.py for the unapproved-refusal
    behavior."""
    _register_and_login(client, username="tooluser", email="tooluser@example.com")

    with app.app_context():
        from app.services.agent_service import build_meeting_tools
        from app.models.models import User

        user = User.query.filter_by(username="tooluser").first()
        create_task, list_tasks, update_task, complete_task, delete_task, extract_notes, send_email = (
            build_meeting_tools(user.id, user.email, "meeting", approved_tools={"delete_task", "email_task_summary"})
        )

        result = create_task("Draft report", due_date="2026-09-01")
        assert "Created task" in result

        listing = list_tasks("all")
        assert "Draft report" in listing

        from app.models.models import AgentTask
        task = AgentTask.query.filter_by(user_id=user.id).first()

        update_result = update_task(task.id, status="in_progress")
        assert "Updated" in update_result
        assert AgentTask.query.get(task.id).status == "in_progress"

        complete_result = complete_task(task.id)
        assert "completed" in complete_result

        delete_result = delete_task(task.id)
        assert "Deleted" in delete_result
        assert AgentTask.query.get(task.id) is None

        # Graceful handling when email isn't configured
        email_result = send_email("Subject", "Body")
        assert "isn't configured" in email_result or "Failed" in email_result
