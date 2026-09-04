from tests.conftest import register, create_workspace


def test_user_password_hashing(db):
    from app.models.models import User
    user = User(username="hashtest", email="hash@example.com")
    user.set_password("mysecret")
    db.session.add(user)
    db.session.commit()

    assert user.password_hash != "mysecret"
    assert user.check_password("mysecret") is True
    assert user.check_password("wrong") is False


def test_workspace_cascade_delete_removes_conversations(client, db):
    register(client)
    create_workspace(client, name="Cascade WS")
    from app.models.models import Workspace, Conversation
    ws = Workspace.query.filter_by(name="Cascade WS").first()

    convo_resp = client.post(f"/workspaces/{ws.id}/chat/new", follow_redirects=False)
    convo_id = int(convo_resp.headers["Location"].rstrip("/").split("/")[-1])
    assert Conversation.query.get(convo_id) is not None

    client.post(f"/workspaces/{ws.id}/delete")
    assert Conversation.query.get(convo_id) is None


def test_log_estimated_cost_calculation(app):
    with app.app_context():
        from app.models.models import Log
        log = Log(event_type="chat", input_tokens=1000, output_tokens=1000)
        cost = log.estimated_cost(app.config)
        expected = round(1 * app.config["COST_PER_1K_INPUT_TOKENS"] + 1 * app.config["COST_PER_1K_OUTPUT_TOKENS"], 6)
        assert cost == expected
