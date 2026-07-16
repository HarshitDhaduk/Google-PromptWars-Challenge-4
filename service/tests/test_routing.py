"""Routing engine: shortest paths, congestion avoidance, accessibility."""

import pytest

from app.core.routing import RouteNotFoundError, Router
from app.core.stadium import StadiumRepository
from app.models.entities import Edge, StadiumInfo, Zone

from .conftest import StubCrowd

TICKET_GATE = "gate_c"
TICKET_SECTION_ZONE = "sec_320_326"


def test_shortest_path_gate_to_seat_expected_sequence(repo):
    """With uniform congestion the ticket route takes the east stairs."""
    router = Router(repo, StubCrowd(default=0.2))
    route = router.route(TICKET_GATE, TICKET_SECTION_ZONE, minute=-30.0)

    assert [step.zone_id for step in route.steps] == [
        "gate_c",
        "conc_100_e",
        "conc_300_e",
        "sec_320_326",
    ]
    assert [step.edge_kind for step in route.steps] == [None, "walkway", "stairs", "walkway"]


def test_congestion_reroutes_around_ring(repo):
    """A severe crush on the east lower concourse pushes the route south."""
    quiet = Router(repo, StubCrowd(default=0.05))
    congested = Router(repo, StubCrowd(levels={"conc_100_e": 0.95}, default=0.05))

    baseline = quiet.route(TICKET_GATE, TICKET_SECTION_ZONE, minute=-30.0)
    rerouted = congested.route(TICKET_GATE, TICKET_SECTION_ZONE, minute=-30.0)

    baseline_zones = [step.zone_id for step in baseline.steps]
    rerouted_zones = [step.zone_id for step in rerouted.steps]
    assert "conc_100_e" in baseline_zones
    assert "conc_100_e" not in rerouted_zones
    assert rerouted_zones != baseline_zones


def test_accessible_route_uses_elevator_never_stairs(router):
    route = router.route(TICKET_GATE, TICKET_SECTION_ZONE, minute=-30.0, accessible=True)

    kinds = [step.edge_kind for step in route.steps]
    assert "stairs" not in kinds
    assert "elevator" in kinds
    assert route.accessible is True


def test_accessible_unreachable_raises_route_not_found():
    """Stairs-only vertical link => no step-free path exists."""
    repo = StadiumRepository(
        stadium=StadiumInfo(name="Mini", city="Test", viewbox="0 0 10 10"),
        zones=[
            Zone(id="a", name="A", kind="concourse", level=100, x=0, y=0),
            Zone(id="b", name="B", kind="concourse", level=300, x=1, y=1),
        ],
        edges=[
            Edge(id="s", from_zone="a", to_zone="b", kind="stairs", base_seconds=60)
        ],
        amenities=[],
    )
    router = Router(repo, StubCrowd())

    assert router.route("a", "b", minute=0.0).total_seconds > 0
    with pytest.raises(RouteNotFoundError):
        router.route("a", "b", minute=0.0, accessible=True)


def test_route_steps_have_instructions_and_positive_totals(router):
    route = router.route("gate_a", "sec_333_339", minute=10.0)

    assert route.total_seconds > 0
    assert len(route.steps) >= 3
    assert all(step.instruction_en for step in route.steps)
    assert len(route.polyline) == len(route.steps)
    assert route.steps[0].edge_kind is None
    assert route.steps[0].seconds == 0


def test_same_zone_route_is_trivial(router):
    route = router.route("conc_100_n", "conc_100_n", minute=0.0)

    assert route.total_seconds == 0
    assert [step.zone_id for step in route.steps] == ["conc_100_n"]


def test_same_inputs_identical_route(router):
    first = router.route("gate_d", "sec_311_317", minute=42.0)
    second = router.route("gate_d", "sec_311_317", minute=42.0)

    assert first.model_dump() == second.model_dump()


def test_unknown_zone_raises_value_error(router):
    with pytest.raises(ValueError):
        router.route("gate_c", "vip_lounge", minute=0.0)
