def test_create_and_list_memory(client, auth_headers, workspace_id):
    client.post(f"/api/workspaces/{workspace_id}/memory",
                json={"category": "preference", "content": "Likes concise answers"}, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/memory", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_pin_memory_item(client, auth_headers, workspace_id):
    created = client.post(f"/api/workspaces/{workspace_id}/memory",
                           json={"category": "pinned", "content": "Important fact"}, headers=auth_headers).json()
    r = client.patch(f"/api/workspaces/{workspace_id}/memory/{created['id']}/pin", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["pinned"] is True


def test_create_and_update_prompt_template(client, auth_headers, workspace_id):
    created = client.post(f"/api/workspaces/{workspace_id}/prompts",
                           json={"title": "Bug Report", "category": "programming", "content": "Describe: {x}"},
                           headers=auth_headers).json()
    r = client.put(f"/api/workspaces/{workspace_id}/prompts/{created['id']}",
                    json={"title": "Bug Report v2", "category": "programming", "content": "Describe: {y}"},
                    headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Bug Report v2"


def test_delete_prompt_template(client, auth_headers, workspace_id):
    created = client.post(f"/api/workspaces/{workspace_id}/prompts",
                           json={"title": "Temp", "content": "x"}, headers=auth_headers).json()
    r = client.delete(f"/api/workspaces/{workspace_id}/prompts/{created['id']}", headers=auth_headers)
    assert r.status_code == 204


def test_list_available_skills_at_least_six(client, auth_headers, workspace_id):
    r = client.get(f"/api/workspaces/{workspace_id}/skills", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["skills"]) >= 6


def test_run_summarization_skill(client, auth_headers, workspace_id):
    r = client.post(f"/api/workspaces/{workspace_id}/skills/summarization/run",
                     json={"input_text": "Some long text to summarize."}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["skill_name"] == "summarization"


def test_run_unknown_skill_returns_404(client, auth_headers, workspace_id):
    r = client.post(f"/api/workspaces/{workspace_id}/skills/not_a_real_skill/run",
                     json={"input_text": "x"}, headers=auth_headers)
    assert r.status_code == 404
