"""
Functional bot suite fixtures (PR lane — mocked externals).

Image/receipt journeys are deferred past v1 (FR-017); do not add them here yet.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Must set before importing main (module initializes webhook clients at import).
os.environ.setdefault("LINE_CHANNEL_SECRET", "test_secret")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
os.environ.setdefault("GEMINI_API_KEY", "test_gemini_key")

from starlette.testclient import TestClient

import main
from tests.functional.bot.helpers.line_signature import sign_body


@pytest.fixture
def client():
    """FastAPI TestClient with lifespan (initializes LINE/Gemini clients)."""
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def reply_mock(monkeypatch):
    """Replace line_bot_api.reply_message with AsyncMock."""
    mock = AsyncMock(return_value=MagicMock())
    api = MagicMock()
    api.reply_message = mock
    api.get_profile = AsyncMock(return_value=MagicMock(language="en"))
    monkeypatch.setattr(main, "line_bot_api", api)
    return mock


def assert_callback_ok(response) -> None:
    assert response.status_code == 200
    # FastAPI may JSON-encode the plain "OK" string.
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
    assert body == "OK" or response.text.strip('"') == "OK"


def post_callback(client: TestClient, body: bytes, *, signature: str | None = None):
    headers = {}
    if signature is not None:
        headers["X-Line-Signature"] = signature
    return client.post("/callback", content=body, headers=headers)


def post_signed(client: TestClient, body: bytes, secret: str = "test_secret"):
    return post_callback(client, body, signature=sign_body(body, secret))
