import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Force an isolated test DB and mock-only LLM (no real keys) before any app import.
TEST_DB = "sqlite:///./test_ai_workspace.db"
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = TEST_DB
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["DEFAULT_MODEL"] = "gemini-2.5-flash"
os.environ["UPLOAD_DIR"] = "./test_uploads"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    db_file = Path("test_ai_workspace.db")
    if db_file.exists():
        db_file.unlink()
    yield
    if db_file.exists():
        db_file.unlink()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123", "full_name": "Test"})
    r = client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def workspace_id(client, auth_headers):
    r = client.post("/api/workspaces", json={"name": "Test WS"}, headers=auth_headers)
    return r.json()["id"]


@pytest.fixture()
def assistant_id(client, auth_headers, workspace_id):
    r = client.post(f"/api/workspaces/{workspace_id}/assistants", json={"name": "Bot"}, headers=auth_headers)
    return r.json()["id"]


@pytest.fixture()
def conversation_id(client, auth_headers, workspace_id, assistant_id):
    r = client.post(f"/api/workspaces/{workspace_id}/conversations",
                     json={"assistant_id": assistant_id}, headers=auth_headers)
    return r.json()["id"]
