"""Tool layer: filters, location resolution, ui_actions, self-correcting errors."""

import pytest

from app.core.context import ContextService
from app.core.seats import SeatSimulator
from app.llm.tools import ToolRuntime, build_tool_registry
from app.models.entities import (
    HighlightAmenitiesAction,
    HighlightZoneAction,
    ShowRouteAction,
)

PRE_MATCH_MINUTE = -30.0
SECOND_HALF_MINUTE = 70.0
POST_MATCH_MINUTE = 130.0


@pytest.fixture(scope="module")
def registry():
    return build_tool_registry()


@pytest.fixture
def runtime_factory(repo, crowd, router, match_and_ticket):
    match, ticket = match_and_ticket
    context = ContextService(repo, match, ticket)
    seats = SeatSimulator(repo, seed=2026)

    def make(minute: float) -> ToolRuntime:
        return ToolRuntime(
            repo=repo, crowd=crowd, seats=seats, router=router, fan=context.state(minute)
        )

    return make


def test_find_amenities_halal_filter(registry, runtime_factory):
    data, ui_action, ok = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE),
        "find_amenities",
        {"category": "food", "dietary": "halal"},
    )

    assert ok is True
    assert data["results"], "expected at least one halal food option"
    assert all("halal" in item["tags"] for item in data["results"])
    assert isinstance(ui_action, HighlightAmenitiesAction)


def test_find_amenities_sorted_by_eta(registry, runtime_factory):
    data, _, ok = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE),
        "find_amenities",
        {"category": "restroom", "limit": 5},
    )

    assert ok is True
    etas = [item["eta_minutes"] for item in data["results"]]
    assert etas == sorted(etas)
    assert len(etas) <= 5


def test_get_route_emits_show_route_with_seat_details(registry, runtime_factory):
    data, ui_action, ok = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE), "get_route", {"to": "my_seat"}
    )

    assert ok is True
    assert isinstance(ui_action, ShowRouteAction)
    assert ui_action.route.to_zone == "sec_320_326"
    assert data["total_minutes"] >= 1
    assert "Section 324" in data["at_destination"]


def test_get_route_accepts_section_number(registry, runtime_factory):
    _, ui_action, ok = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE), "get_route", {"to": "111"}
    )

    assert ok is True
    assert isinstance(ui_action, ShowRouteAction)
    assert ui_action.route.to_zone == "sec_111_117"


def test_get_route_unknown_location_returns_valid_ids(registry, runtime_factory):
    data, ui_action, ok = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE), "get_route", {"to": "vip_lounge"}
    )

    assert ok is False
    assert ui_action is None
    assert data["error"] == "unknown_location"
    assert "gate_c" in data["valid_zone_ids"]


def test_transit_advice_changes_by_phase(registry, runtime_factory):
    pre, _, _ = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE), "get_transit_advice", {}
    )
    post, ui_action, _ = registry.execute(
        runtime_factory(POST_MATCH_MINUTE), "get_transit_advice", {}
    )

    assert pre["phase"] == "pre_match"
    assert post["phase"] == "post_match"
    assert pre["advice_key"] == "pre_match"
    assert post["advice_key"] in ("wait_out", "go_now")
    assert pre["recommendation"] != post["recommendation"]
    assert isinstance(ui_action, HighlightZoneAction)
    assert ui_action.zone_id == "transit_hub"


def test_match_info_replays_scripted_goals(registry, runtime_factory):
    def score_at_minute(minute: float) -> str:
        data, _, ok = registry.execute(runtime_factory(minute), "get_match_info", {})
        assert ok is True
        return data["score"]

    assert score_at_minute(-10.0) == "not started"
    assert score_at_minute(30.0) == "Argentina 1-0 France"  # Alvarez 23'
    assert score_at_minute(90.0) == "Argentina 1-1 France"  # wall 90 = match 75', Mbappe 67'
    assert score_at_minute(130.0) == "Argentina 2-1 France"  # Messi 88'


def test_crowd_status_for_zone_highlights_it(registry, runtime_factory):
    data, ui_action, ok = registry.execute(
        runtime_factory(SECOND_HALF_MINUTE), "get_crowd_status", {"zone_id": "conc_100_e"}
    )

    assert ok is True
    assert data["zone_id"] == "conc_100_e"
    assert data["crowd_label"] in ("low", "moderate", "high", "severe")
    assert isinstance(ui_action, HighlightZoneAction)


def test_unknown_tool_is_reported_not_raised(registry, runtime_factory):
    data, ui_action, ok = registry.execute(
        runtime_factory(PRE_MATCH_MINUTE), "hack_the_planet", {}
    )

    assert ok is False
    assert ui_action is None
    assert data["error"] == "unknown_tool"
