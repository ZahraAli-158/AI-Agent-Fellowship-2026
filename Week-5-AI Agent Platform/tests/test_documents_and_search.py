def test_upload_txt_document_and_autoembed(client, auth_headers, workspace_id):
    files = {"file": ("notes.txt", b"AI workspaces use embeddings for semantic search.", "text/plain")}
    r = client.post(f"/api/workspaces/{workspace_id}/documents", files=files, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["status"] == "embedded"
    assert r.json()["num_chunks"] >= 1


def test_upload_rejects_unsupported_type(client, auth_headers, workspace_id):
    files = {"file": ("virus.exe", b"binary", "application/octet-stream")}
    r = client.post(f"/api/workspaces/{workspace_id}/documents", files=files, headers=auth_headers)
    assert r.status_code == 400


def test_semantic_search_returns_relevant_chunk(client, auth_headers, workspace_id):
    files = {"file": ("doc.txt", b"The quarterly revenue grew by twenty percent this year.", "text/plain")}
    client.post(f"/api/workspaces/{workspace_id}/documents", files=files, headers=auth_headers)
    r = client.get(f"/api/workspaces/{workspace_id}/documents/search/query",
                    params={"q": "revenue growth"}, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["score"] > 0


def test_ask_documents_grounded_qa_with_citations(client, auth_headers, workspace_id):
    files = {"file": ("policy.txt", b"Refunds are processed within 14 business days of request.", "text/plain")}
    client.post(f"/api/workspaces/{workspace_id}/documents", files=files, headers=auth_headers)
    r = client.post(f"/api/workspaces/{workspace_id}/documents/ask",
                     json={"question": "How long do refunds take?"}, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["sources"]) >= 1
    assert r.json()["sources"][0]["filename"] == "policy.txt"


def test_ask_with_no_documents_returns_graceful_message(client, auth_headers):
    from app.core.config import get_settings
    r = client.post("/api/workspaces", json={"name": "Empty WS"}, headers=auth_headers)
    ws_id = r.json()["id"]
    r2 = client.post(f"/api/workspaces/{ws_id}/documents/ask", json={"question": "Anything?"}, headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["sources"] == []
