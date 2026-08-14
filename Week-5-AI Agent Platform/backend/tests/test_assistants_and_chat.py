def test_create_assistant_inherits_default_model(client, auth_headers, workspace_id):
    r = client.post(f"/api/workspaces/{workspace_id}/assistants", json={"name": "Bot"}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["model"] == "gemini-2.5-flash"  # DEFAULT_MODEL, never hardcoded "mock-gpt"


def test_create_assistant_explicit_model_override(client, auth_headers, workspace_id):
    r = client.post(f"/api/workspaces/{workspace_id}/assistants",
                     json={"name": "Bot2", "model": "gpt-4o-mini"}, headers=auth_headers)
    assert r.json()["model"] == "gpt-4o-mini"


def test_create_conversation(client, auth_headers, workspace_id, assistant_id):
    r = client.post(f"/api/workspaces/{workspace_id}/conversations",
                     json={"assistant_id": assistant_id}, headers=auth_headers)
    assert r.status_code == 201


def test_chat_persists_messages_and_falls_back_to_mock_without_key(client, auth_headers, workspace_id, conversation_id):
    r = client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                     json={"message": "Hello there"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user_message"]["content"] == "Hello there"
    # No API key configured in test env -> provider factory must fall back cleanly
    assert body["assistant_message"]["provider_used"] == "mock"


def test_conversation_history_persisted(client, auth_headers, workspace_id, conversation_id):
    client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                json={"message": "First"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/messages", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2  # user + assistant


def test_rename_conversation(client, auth_headers, workspace_id, conversation_id):
    r = client.patch(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/rename",
                      params={"title": "Renamed"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"


def test_search_conversations(client, auth_headers, workspace_id, conversation_id):
    client.patch(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/rename",
                 params={"title": "Budget Planning"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/conversations", params={"search": "budget"}, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_delete_conversation(client, auth_headers, workspace_id, conversation_id):
    r = client.delete(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}", headers=auth_headers)
    assert r.status_code == 204
