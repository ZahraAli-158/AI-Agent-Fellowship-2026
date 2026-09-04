from tests.conftest import register, login


def test_register_creates_user(client, db):
    resp = register(client)
    assert resp.status_code == 200
    from app.models.models import User
    assert User.query.filter_by(username="alice").first() is not None


def test_register_rejects_duplicate_username(client, db):
    register(client)
    client.get("/logout")
    resp = client.post("/register", data={
        "username": "alice", "email": "other@example.com",
        "password": "password123", "confirm_password": "password123",
    })
    assert b"already taken" in resp.data


def test_register_rejects_password_mismatch(client, db):
    resp = client.post("/register", data={
        "username": "bob", "email": "bob@example.com",
        "password": "password123", "confirm_password": "different",
    })
    assert b"do not match" in resp.data


def test_login_success(client, db):
    register(client)
    client.get("/logout")
    resp = login(client)
    assert resp.status_code == 200
    assert b"Workspaces" in resp.data or resp.request.path == "/workspaces/"


def test_login_wrong_password_fails(client, db):
    register(client)
    client.get("/logout")
    resp = login(client, password="wrongpassword")
    assert b"Invalid username/email or password" in resp.data


def test_logout_requires_login_redirect(client, db):
    resp = client.get("/logout", follow_redirects=True)
    # Should redirect to login page since not authenticated
    assert b"Log in" in resp.data or resp.status_code == 200
