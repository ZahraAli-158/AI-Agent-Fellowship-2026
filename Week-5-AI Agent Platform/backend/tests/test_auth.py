def test_register_success(client):
    r = client.post("/api/auth/register", json={"email": "a@x.com", "password": "password123"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@x.com"


def test_register_duplicate_email_fails(client):
    client.post("/api/auth/register", json={"email": "dup@x.com", "password": "password123"})
    r = client.post("/api/auth/register", json={"email": "dup@x.com", "password": "password123"})
    assert r.status_code == 400


def test_login_success(client):
    client.post("/api/auth/register", json={"email": "b@x.com", "password": "password123"})
    r = client.post("/api/auth/login", json={"email": "b@x.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_fails(client):
    client.post("/api/auth/register", json={"email": "c@x.com", "password": "password123"})
    r = client.post("/api/auth/login", json={"email": "c@x.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client, auth_headers):
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"
