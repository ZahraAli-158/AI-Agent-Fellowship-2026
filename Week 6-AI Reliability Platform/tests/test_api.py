from tests.conftest import register, create_workspace


def test_unauthenticated_requests_redirect_to_login(client, db):
    resp = client.get("/workspaces/", follow_redirects=True)
    assert b"Log in" in resp.data or resp.request.path == "/login"


def test_dashboard_returns_expected_stats_keys(client, db):
    register(client)
    create_workspace(client, name="API WS")
    from app.models.models import Workspace
    ws = Workspace.query.filter_by(name="API WS").first()

    resp = client.get(f"/workspaces/{ws.id}/dashboard/")
    assert resp.status_code == 200
    assert b"Conversations" in resp.data
    assert b"Estimated cost" in resp.data


def test_cross_user_access_forbidden(client, db):
    register(client, username="user1", email="u1@example.com")
    create_workspace(client, name="Private WS")
    from app.models.models import Workspace
    ws = Workspace.query.filter_by(name="Private WS").first()
    client.get("/logout")

    register(client, username="user2", email="u2@example.com")
    resp = client.post(f"/workspaces/{ws.id}/dashboard/memory/add", data={"content": "hack attempt"})
    assert resp.status_code == 403
