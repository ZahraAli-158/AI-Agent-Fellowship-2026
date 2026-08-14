def test_create_workspace(client, auth_headers):
    r = client.post("/api/workspaces", json={"name": "My WS"}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["name"] == "My WS"


def test_list_workspaces_isolated_per_user(client, auth_headers):
    client.post("/api/workspaces", json={"name": "WS1"}, headers=auth_headers)
    client.post("/api/auth/register", json={"email": "other@x.com", "password": "password123"})
    other_login = client.post("/api/auth/login", json={"email": "other@x.com", "password": "password123"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    r_owner = client.get("/api/workspaces", headers=auth_headers)
    r_other = client.get("/api/workspaces", headers=other_headers)
    assert len(r_owner.json()) >= 1
    assert len(r_other.json()) == 0  # conversation isolation between users


def test_get_workspace_not_found(client, auth_headers):
    r = client.get("/api/workspaces/nonexistent-id", headers=auth_headers)
    assert r.status_code == 404


def test_delete_workspace(client, auth_headers, workspace_id):
    r = client.delete(f"/api/workspaces/{workspace_id}", headers=auth_headers)
    assert r.status_code == 204
    r2 = client.get(f"/api/workspaces/{workspace_id}", headers=auth_headers)
    assert r2.status_code == 404
