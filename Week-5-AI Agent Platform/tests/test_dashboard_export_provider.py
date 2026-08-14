def test_dashboard_reflects_active_model_and_usage(client, auth_headers, workspace_id, conversation_id):
    client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                json={"message": "Hi"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/dashboard", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["conversations"] == 1
    assert body["active_model"] == "gemini-2.5-flash"
    assert body["total_input_tokens"] > 0


def test_dashboard_requires_ownership(client, auth_headers, workspace_id):
    client.post("/api/auth/register", json={"email": "intruder@x.com", "password": "password123"})
    login = client.post("/api/auth/login", json={"email": "intruder@x.com", "password": "password123"})
    intruder_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client.get(f"/api/workspaces/{workspace_id}/dashboard", headers=intruder_headers)
    assert r.status_code == 404  # cannot access another user's workspace


def test_export_markdown_contains_messages(client, auth_headers, workspace_id, conversation_id):
    client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                json={"message": "Export me"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/export/markdown",
                    headers=auth_headers)
    assert r.status_code == 200
    assert "Export me" in r.text


def test_export_pdf_returns_pdf_bytes(client, auth_headers, workspace_id, conversation_id):
    client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                json={"message": "PDF please"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/export/pdf",
                    headers=auth_headers)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_provider_factory_resolves_gemini_when_key_present():
    from app.core.config import Settings
    from app.services.llm.factory import get_provider
    s = Settings(DEFAULT_MODEL="gemini-2.5-flash", GEMINI_API_KEY="fake-key")
    provider = get_provider(settings=s)
    assert provider.name == "gemini"
    assert provider.model == "gemini-2.5-flash"


def test_provider_factory_falls_back_to_mock_without_key():
    from app.core.config import Settings
    from app.services.llm.factory import get_provider
    s = Settings(DEFAULT_MODEL="gemini-2.5-flash", GEMINI_API_KEY=None)
    provider = get_provider(settings=s)
    assert provider.name == "mock"


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
