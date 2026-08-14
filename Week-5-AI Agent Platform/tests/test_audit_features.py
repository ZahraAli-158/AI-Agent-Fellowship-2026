def test_edit_workspace(client, auth_headers, workspace_id):
    r = client.patch(f"/api/workspaces/{workspace_id}",
                      json={"name": "Renamed WS", "description": "new desc", "workspace_prompt": ""},
                      headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed WS"


def test_archive_and_unarchive_workspace(client, auth_headers, workspace_id):
    r = client.patch(f"/api/workspaces/{workspace_id}/archive", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["archived"] is True

    # Archived workspace should be excluded from default listing
    r2 = client.get("/api/workspaces", headers=auth_headers)
    assert workspace_id not in [w["id"] for w in r2.json()]

    r3 = client.get("/api/workspaces", params={"include_archived": True}, headers=auth_headers)
    assert workspace_id in [w["id"] for w in r3.json()]

    # Unarchive
    client.patch(f"/api/workspaces/{workspace_id}/archive", headers=auth_headers)


def test_clone_workspace_copies_assistants_and_prompts(client, auth_headers, workspace_id, assistant_id):
    client.post(f"/api/workspaces/{workspace_id}/prompts",
                json={"title": "T", "category": "custom", "content": "C"}, headers=auth_headers)
    r = client.post(f"/api/workspaces/{workspace_id}/clone", headers=auth_headers)
    assert r.status_code == 201
    clone_id = r.json()["id"]
    assert "(Copy)" in r.json()["name"]

    assistants = client.get(f"/api/workspaces/{clone_id}/assistants", headers=auth_headers).json()
    prompts = client.get(f"/api/workspaces/{clone_id}/prompts", headers=auth_headers).json()
    assert len(assistants) == 1
    assert len(prompts) == 1


def test_workspace_sharing_join_flow(client, auth_headers, workspace_id):
    share_resp = client.post(f"/api/workspaces/{workspace_id}/share", headers=auth_headers)
    assert share_resp.status_code == 200
    token = share_resp.json()["share_token"]

    client.post("/api/auth/register", json={"email": "joiner@x.com", "password": "password123"})
    login = client.post("/api/auth/login", json={"email": "joiner@x.com", "password": "password123"})
    joiner_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    join_resp = client.post(f"/api/workspaces/join/{token}", headers=joiner_headers)
    assert join_resp.status_code == 200
    assert join_resp.json()["id"] == workspace_id

    # Joined member can now access the shared workspace
    get_resp = client.get(f"/api/workspaces/{workspace_id}", headers=joiner_headers)
    assert get_resp.status_code == 200


def test_workspace_stats(client, auth_headers, workspace_id, assistant_id, conversation_id):
    client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                json={"message": "hi"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/stats", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["conversations"] == 1
    assert r.json()["messages"] == 2


def test_memory_is_recalled_in_chat_system_prompt(client, auth_headers, workspace_id, assistant_id, conversation_id, monkeypatch):
    client.post(f"/api/workspaces/{workspace_id}/memory",
                json={"category": "preference", "content": "UNIQUE_MEMORY_MARKER_XYZ", "pinned": True},
                headers=auth_headers)

    captured = {}
    from app.services.llm.mock_provider import MockLLMProvider
    original_generate = MockLLMProvider.generate

    def spy_generate(self, messages, temperature=0.7, max_tokens=1024, system_prompt=None):
        captured["system_prompt"] = system_prompt
        return original_generate(self, messages, temperature, max_tokens, system_prompt)

    monkeypatch.setattr(MockLLMProvider, "generate", spy_generate)

    client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                json={"message": "test"}, headers=auth_headers)

    assert "UNIQUE_MEMORY_MARKER_XYZ" in captured["system_prompt"]


def test_edit_memory(client, auth_headers, workspace_id):
    created = client.post(f"/api/workspaces/{workspace_id}/memory",
                           json={"category": "general", "content": "old"}, headers=auth_headers).json()
    r = client.put(f"/api/workspaces/{workspace_id}/memory/{created['id']}",
                    json={"category": "preference", "content": "new", "pinned": True}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["content"] == "new"
    assert r.json()["pinned"] is True


def test_duplicate_prompt(client, auth_headers, workspace_id):
    created = client.post(f"/api/workspaces/{workspace_id}/prompts",
                           json={"title": "Original", "content": "X"}, headers=auth_headers).json()
    r = client.post(f"/api/workspaces/{workspace_id}/prompts/{created['id']}/duplicate", headers=auth_headers)
    assert r.status_code == 201
    assert "(Copy)" in r.json()["title"]

    all_prompts = client.get(f"/api/workspaces/{workspace_id}/prompts", headers=auth_headers).json()
    assert len(all_prompts) == 2


def test_favorite_prompt_and_filter(client, auth_headers, workspace_id):
    created = client.post(f"/api/workspaces/{workspace_id}/prompts",
                           json={"title": "FavMe", "content": "X"}, headers=auth_headers).json()
    r = client.patch(f"/api/workspaces/{workspace_id}/prompts/{created['id']}/favorite", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["favorite"] is True

    filtered = client.get(f"/api/workspaces/{workspace_id}/prompts",
                           params={"favorites_only": True}, headers=auth_headers).json()
    assert len(filtered) == 1
    assert filtered[0]["id"] == created["id"]


def test_document_summary_generation_and_caching(client, auth_headers, workspace_id):
    files = {"file": ("summ.txt", b"This is a test document about AI platforms and workspace tools.", "text/plain")}
    doc = client.post(f"/api/workspaces/{workspace_id}/documents", files=files, headers=auth_headers).json()

    r = client.post(f"/api/workspaces/{workspace_id}/documents/{doc['id']}/summary", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["summary"] is not None

    # Second call should return the cached summary (not error, not None)
    r2 = client.post(f"/api/workspaces/{workspace_id}/documents/{doc['id']}/summary", headers=auth_headers)
    assert r2.json()["summary"] == r.json()["summary"]


def test_pin_message_and_list_pinned(client, auth_headers, workspace_id, conversation_id):
    chat_resp = client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                             json={"message": "pin me"}, headers=auth_headers)
    assistant_msg_id = chat_resp.json()["assistant_message"]["id"]

    r = client.patch(
        f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/messages/{assistant_msg_id}/pin",
        headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["pinned"] is True

    pinned_list = client.get(f"/api/workspaces/{workspace_id}/conversations/messages/pinned", headers=auth_headers)
    assert pinned_list.status_code == 200
    assert len(pinned_list.json()) == 1


def test_response_time_recorded_on_message(client, auth_headers, workspace_id, conversation_id):
    r = client.post(f"/api/workspaces/{workspace_id}/conversations/{conversation_id}/chat",
                     json={"message": "time me"}, headers=auth_headers)
    assert r.json()["assistant_message"]["response_time_ms"] >= 0


def test_ten_ai_skills_available(client, auth_headers, workspace_id):
    r = client.get(f"/api/workspaces/{workspace_id}/skills", headers=auth_headers)
    skills = r.json()["skills"]
    assert len(skills) == 10
    for expected in ["business_canvas", "code_review", "idea_generator"]:
        assert expected in skills


def test_voice_transcribe_without_key_returns_clear_error(client, auth_headers, workspace_id):
    files = {"file": ("audio.wav", b"fake-audio-bytes", "audio/wav")}
    r = client.post(f"/api/workspaces/{workspace_id}/voice/transcribe", files=files, headers=auth_headers)
    assert r.status_code == 400
    assert "OPENAI_API_KEY" in r.json()["detail"]
