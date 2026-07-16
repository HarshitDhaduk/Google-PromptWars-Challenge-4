"""Chat API through the mock provider: grounding, language, sessions."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm.sessions import SessionStore
from app.main import create_app

SESSION_ID = "9f1c2f4e-4b7a-4f7e-9c2d-1a2b3c4d5e6f"


@pytest.fixture
def client(monkeypatch):
    """App forced into demo mode (mock provider), regardless of local .env."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    test_app = create_app()
    with TestClient(test_app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _chat(client: TestClient, message: str, locale: str = "en", session: str = SESSION_ID):
    response = client.post(
        "/api/chat", json={"session_id": session, "message": message, "locale": locale}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_seat_route_is_grounded_with_ui_action(client):
    body = _chat(client, "Take me to my seat")

    assert body["provider"] == "mock"
    assert [call["name"] for call in body["tool_calls"]] == ["get_route"]
    assert all(call["ok"] for call in body["tool_calls"])
    assert [action["type"] for action in body["ui_actions"]] == ["show_route"]
    assert body["ui_actions"][0]["route"]["to_zone"] == "sec_320_326"
    assert "Section 324" in body["reply"]


def test_spanish_message_gets_spanish_reply(client):
    body = _chat(client, "¿Dónde puedo comprar comida halal?")

    assert "Empire Halal Grill" in body["reply"]
    assert "cercanas" in body["reply"]  # Spanish template marker
    assert body["ui_actions"][0]["type"] == "highlight_amenities"


def test_accessible_route_avoids_stairs(client):
    body = _chat(client, "I need a wheelchair accessible route to my seat")

    route = body["ui_actions"][0]["route"]
    kinds = [step["edge_kind"] for step in route["steps"]]
    assert route["accessible"] is True
    assert "stairs" not in kinds
    assert "elevator" in kinds


def test_out_of_scope_returns_capabilities(client):
    body = _chat(client, "Tell me about quantum physics")

    assert body["tool_calls"] == []
    assert body["ui_actions"] == []
    assert "seat" in body["reply"].lower()


def test_arabic_message_still_grounds_route(client):
    body = _chat(client, "أين مقعدي؟", locale="ar")

    assert [call["name"] for call in body["tool_calls"]] == ["get_route"]
    assert body["ui_actions"][0]["type"] == "show_route"
    assert body["reply"]


def test_session_history_is_bounded():
    store = SessionStore(max_turns=20)
    for index in range(25):
        store.append(SESSION_ID, "user", f"message {index}")
        store.append(SESSION_ID, "assistant", f"reply {index}")

    assert store.turn_count(SESSION_ID) == 20
    history = store.history(SESSION_ID)
    assert history[-1].text == "reply 24"


def test_session_store_evicts_expired_and_over_cap():
    clock = {"now": 0.0}
    store = SessionStore(ttl_seconds=10, max_sessions=2, now_fn=lambda: clock["now"])

    store.append("a" * 36, "user", "hi")
    clock["now"] = 20.0  # session 'a' expires
    store.append("b" * 36, "user", "hi")
    assert store.turn_count("a" * 36) == 0

    store.append("c" * 36, "user", "hi")
    clock["now"] = 21.0
    store.append("d" * 36, "user", "hi")  # cap of 2 evicts the oldest
    assert store.turn_count("b" * 36) == 0
    assert store.turn_count("d" * 36) == 1
