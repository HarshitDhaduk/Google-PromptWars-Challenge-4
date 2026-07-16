"""Seat availability: determinism, sales pressure, status buckets, tool + API."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.seats import LIMITED_THRESHOLD, SeatSimulator, seat_status
from app.main import create_app

from .conftest import TEST_SEED


@pytest.fixture
def seats(repo) -> SeatSimulator:
    return SeatSimulator(repo, seed=TEST_SEED)


def test_same_seed_identical_snapshots(repo):
    first = SeatSimulator(repo, seed=TEST_SEED)
    second = SeatSimulator(repo, seed=TEST_SEED)

    assert first.snapshot(-60.0) == second.snapshot(-60.0)


def test_covers_every_section_of_every_stand(seats, repo):
    sections = {
        section for zone in repo.zones if zone.sections for section in zone.sections
    }
    assert set(seats.snapshot(0.0)) == sections
    assert len(sections) == 56


def test_availability_never_increases_toward_kickoff(seats):
    checkpoints = [-240.0, -120.0, -60.0, -30.0, 0.0, 30.0]
    for section in seats.sections:
        series = [seats.info(section, minute).available for minute in checkpoints]
        assert series == sorted(series, reverse=True), f"section {section}: {series}"


def test_availability_within_capacity_bounds(seats):
    for minute in (-200.0, -45.0, 15.0):
        for info in seats.snapshot(minute).values():
            assert 0 <= info.available <= info.capacity


def test_some_sections_remain_available_pre_match(seats):
    snapshot = seats.snapshot(-45.0)
    statuses = {info.status for info in snapshot.values()}
    assert "available" in statuses or "limited" in statuses
    assert any(info.status == "sold_out" for info in snapshot.values())


def test_status_buckets():
    assert seat_status(0) == "sold_out"
    assert seat_status(LIMITED_THRESHOLD) == "limited"
    assert seat_status(LIMITED_THRESHOLD + 1) == "available"


def test_find_available_seats_tool_sorted_and_highlighted(repo):
    from app.llm.tools import build_tool_registry

    from .test_tools import PRE_MATCH_MINUTE  # reuse the shared constant

    registry = build_tool_registry()

    # Build a runtime directly to keep this test self-contained.
    from app.core.context import ContextService
    from app.core.crowd import CrowdSimulator
    from app.core.routing import Router
    from app.core.stadium import load_match_fixture
    from app.llm.tools import ToolRuntime

    match, ticket = load_match_fixture()
    context = ContextService(repo, match, ticket)
    crowd = CrowdSimulator(repo, seed=TEST_SEED)
    runtime = ToolRuntime(
        repo=repo,
        crowd=crowd,
        seats=SeatSimulator(repo, seed=TEST_SEED),
        router=Router(repo, crowd),
        fan=context.state(PRE_MATCH_MINUTE),
    )

    data, ui_action, ok = registry.execute(runtime, "find_available_seats", {"limit": 3})

    assert ok is True
    counts = [entry["available"] for entry in data["sections"]]
    assert counts == sorted(counts, reverse=True)
    assert len(counts) <= 3
    assert all(count > 0 for count in counts)
    assert ui_action is not None
    assert ui_action.zone_id == data["sections"][0]["zone_id"]


def test_seats_endpoint_and_mock_chat_intent(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        seats_response = client.get("/api/seats")
        assert seats_response.status_code == 200
        body = seats_response.json()
        assert len(body["sections"]) == 56
        assert body["sections"]["324"]["zone_id"] == "sec_320_326"

        crowd_response = client.get("/api/crowd")
        assert crowd_response.status_code == 200
        crowd_body = crowd_response.json()
        assert crowd_body["fan_zone_id"] in crowd_body["zones"]

        chat_response = client.post(
            "/api/chat",
            json={
                "session_id": "9f1c2f4e-4b7a-4f7e-9c2d-1a2b3c4d5e6f",
                "message": "Are there any seats available to buy?",
                "locale": "en",
            },
        )
        assert chat_response.status_code == 200
        chat_body = chat_response.json()
        assert [call["name"] for call in chat_body["tool_calls"]] == ["find_available_seats"]
        assert "Section" in chat_body["reply"]
    get_settings.cache_clear()
