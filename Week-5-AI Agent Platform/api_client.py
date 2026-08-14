"""Thin wrapper around the FastAPI backend so Streamlit pages stay simple."""
from __future__ import annotations

import os
from typing import Any, Optional

import requests
import streamlit as st

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def register(email: str, password: str, full_name: str = "") -> dict:
    r = requests.post(_url("/api/auth/register"), json={"email": email, "password": password, "full_name": full_name})
    r.raise_for_status()
    return r.json()


def login(email: str, password: str) -> str:
    r = requests.post(_url("/api/auth/login"), json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def get(path: str, params: Optional[dict] = None) -> Any:
    r = requests.get(_url(path), headers=_headers(), params=params or {})
    r.raise_for_status()
    return r.json()


def post(path: str, json: Optional[dict] = None, files: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    r = requests.post(_url(path), headers=_headers(), json=json, files=files, params=params or {})
    r.raise_for_status()
    return r.json()


def put(path: str, json: Optional[dict] = None) -> Any:
    r = requests.put(_url(path), headers=_headers(), json=json)
    r.raise_for_status()
    return r.json()


def patch(path: str, params: Optional[dict] = None, json: Optional[dict] = None) -> Any:
    r = requests.patch(_url(path), headers=_headers(), params=params or {}, json=json)
    r.raise_for_status()
    return r.json()


def delete(path: str) -> None:
    r = requests.delete(_url(path), headers=_headers())
    r.raise_for_status()


def get_raw(path: str) -> bytes:
    r = requests.get(_url(path), headers=_headers())
    r.raise_for_status()
    return r.content
