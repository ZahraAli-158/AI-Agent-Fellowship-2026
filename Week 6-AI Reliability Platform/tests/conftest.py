import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models.models import db as _db
from config import Config


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tempfile.gettempdir(), "ai_platform_test.db")
    GEMINI_API_KEY = ""  # force offline-stub mode -> deterministic tests


@pytest.fixture()
def app():
    db_path = os.path.join(tempfile.gettempdir(), "ai_platform_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    application = create_app(TestConfig)
    yield application
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db


def register(client, username="alice", email="alice@example.com", password="password123"):
    return client.post("/register", data={
        "username": username, "email": email,
        "password": password, "confirm_password": password,
    }, follow_redirects=True)


def login(client, identifier="alice", password="password123"):
    return client.post("/login", data={"identifier": identifier, "password": password}, follow_redirects=True)


def create_workspace(client, name="Test Workspace", category="Custom"):
    return client.post("/workspaces/create", data={"name": name, "category": category}, follow_redirects=True)
