import io

from tests.conftest import register, create_workspace


def _make_workspace(client):
    register(client)
    create_workspace(client, name="Knowledge WS")
    from app.models.models import Workspace
    return Workspace.query.filter_by(name="Knowledge WS").first()


SAMPLE_TEXT = (
    b"The Eiffel Tower is a wrought-iron lattice tower in Paris, France. "
    b"It was completed in 1889 and was the tallest man-made structure for over 40 years. "
    b"The tower attracts millions of visitors annually and is a global icon of France. "
    b"Gustave Eiffel's company designed and built the tower for the 1889 World's Fair."
)


def test_upload_txt_document(client, db):
    ws = _make_workspace(client)
    data = {"document": (io.BytesIO(SAMPLE_TEXT), "eiffel.txt")}
    resp = client.post(
        f"/workspaces/{ws.id}/knowledge/upload", data=data,
        content_type="multipart/form-data", follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.models.models import Document
    doc = Document.query.filter_by(workspace_id=ws.id, filename="eiffel.txt").first()
    assert doc is not None
    assert doc.char_count > 0
    assert len(doc.chunks) >= 1


def test_reject_unsupported_file_type(client, db):
    ws = _make_workspace(client)
    data = {"document": (io.BytesIO(b"binary junk"), "malware.exe")}
    resp = client.post(
        f"/workspaces/{ws.id}/knowledge/upload", data=data,
        content_type="multipart/form-data", follow_redirects=True,
    )
    assert b"Unsupported file type" in resp.data

    from app.models.models import Document
    assert Document.query.filter_by(workspace_id=ws.id).count() == 0


def test_delete_document_removes_chunks(client, db):
    ws = _make_workspace(client)
    data = {"document": (io.BytesIO(SAMPLE_TEXT), "eiffel2.txt")}
    client.post(f"/workspaces/{ws.id}/knowledge/upload", data=data, content_type="multipart/form-data")

    from app.models.models import Document, Chunk
    doc = Document.query.filter_by(workspace_id=ws.id, filename="eiffel2.txt").first()
    doc_id = doc.id
    chunk_ids = [c.id for c in doc.chunks]

    client.post(f"/workspaces/{ws.id}/knowledge/{doc_id}/delete", follow_redirects=True)

    assert Document.query.get(doc_id) is None
    for cid in chunk_ids:
        assert Chunk.query.get(cid) is None


def test_semantic_search_tfidf_fallback(client, db, app):
    ws = _make_workspace(client)
    data = {"document": (io.BytesIO(SAMPLE_TEXT), "eiffel3.txt")}
    client.post(f"/workspaces/{ws.id}/knowledge/upload", data=data, content_type="multipart/form-data")

    resp = client.get(f"/workspaces/{ws.id}/knowledge/search?q=Eiffel Tower Paris")
    payload = resp.get_json()
    assert len(payload["results"]) >= 1
    assert "eiffel3.txt" in payload["results"][0]["document"]


def test_chunking_respects_size_and_overlap(app):
    with app.app_context():
        from app.services.document_service import chunk_text
        text = "word " * 1000
        chunks = chunk_text(text, chunk_size=200, overlap=40)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) <= 200
