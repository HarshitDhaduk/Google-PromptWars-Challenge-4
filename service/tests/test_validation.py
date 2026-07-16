"""Input validation and rate limiting on the chat endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

SESSION_ID = "9f1c2f4e-4b7a-4f7e-9c2d-1a2b3c4d5e6f"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    test_app = create_app()
    with TestClient(test_app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _post(client: TestClient, payload: dict):
    return client.post("/api/chat", json=payload)


def _assert_validation_error(response):
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"]


def test_oversized_message_rejected(client):
    response = _post(
        client, {"session_id": SESSION_ID, "message": "x" * 501, "locale": "en"}
    )
    _assert_validation_error(response)


def test_whitespace_only_message_rejected(client):
    response = _post(
        client, {"session_id": SESSION_ID, "message": "   \n\t  ", "locale": "en"}
    )
    _assert_validation_error(response)


def test_invalid_session_id_rejected(client):
    response = _post(
        client, {"session_id": "not-a-uuid", "message": "hello", "locale": "en"}
    )
    _assert_validation_error(response)


def test_unknown_locale_rejected(client):
    response = _post(
        client, {"session_id": SESSION_ID, "message": "hello", "locale": "xx"}
    )
    _assert_validation_error(response)


def test_missing_message_rejected(client):
    response = _post(client, {"session_id": SESSION_ID, "locale": "en"})
    _assert_validation_error(response)


def test_control_characters_are_stripped(client):
    response = _post(
        client,
        {"session_id": SESSION_ID, "message": "where is\x00\x08 my seat", "locale": "en"},
    )
    assert response.status_code == 200
    assert response.json()["tool_calls"][0]["name"] == "get_route"


def test_per_session_rate_limit_returns_429(client):
    last = None
    for _ in range(11):
        last = _post(
            client, {"session_id": SESSION_ID, "message": "hello there", "locale": "en"}
        )
    assert last is not None
    assert last.status_code == 429
    assert last.json()["error"]["code"] == "rate_limited"
    assert int(last.headers["Retry-After"]) >= 1


def test_health_endpoint_reports_demo_provider(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "provider": "mock", "model": None}
