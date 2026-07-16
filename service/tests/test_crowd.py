"""Crowd simulation: determinism, bounds, phases, and story beats."""

from app.core.clock import (
    match_minute_for,
    minutes_to_kickoff_for,
    phase_for_minute,
)
from app.core.crowd import (
    LEVEL_MAX,
    LEVEL_MIN,
    CrowdSimulator,
    congestion_multiplier,
    crowd_label,
)

from .conftest import TEST_SEED


def test_same_seed_same_minute_identical_levels(repo):
    first = CrowdSimulator(repo, seed=TEST_SEED)
    second = CrowdSimulator(repo, seed=TEST_SEED)

    for minute in (-45.0, 0.0, 52.5, 110.0):
        assert first.snapshot(minute) == second.snapshot(minute)


def test_different_seed_changes_levels(repo):
    first = CrowdSimulator(repo, seed=TEST_SEED)
    other = CrowdSimulator(repo, seed=TEST_SEED + 1)

    differences = [
        zone_id
        for zone_id, info in first.snapshot(0.0).items()
        if other.snapshot(0.0)[zone_id].level != info.level
    ]
    assert differences


def test_levels_clamped_to_bounds(crowd, repo):
    minute = -180.0
    while minute <= 180.0:
        for zone in repo.zones:
            level = crowd.level(zone.id, minute)
            assert LEVEL_MIN <= level <= LEVEL_MAX
        minute += 7.3


def test_phase_boundaries():
    assert phase_for_minute(-0.1) == "pre_match"
    assert phase_for_minute(0.0) == "first_half"
    assert phase_for_minute(44.9) == "first_half"
    assert phase_for_minute(45.0) == "halftime"
    assert phase_for_minute(59.9) == "halftime"
    assert phase_for_minute(60.0) == "second_half"
    assert phase_for_minute(104.9) == "second_half"
    assert phase_for_minute(105.0) == "post_match"


def test_match_minute_mapping():
    assert match_minute_for(-5.0) is None
    assert match_minute_for(10.5) == 10
    assert match_minute_for(50.0) == 45  # halftime shows 45'
    assert match_minute_for(75.0) == 60  # wall 75 = match 60'
    assert match_minute_for(200.0) == 90  # frozen at full time


def test_minutes_to_kickoff():
    assert minutes_to_kickoff_for(-30.2) == 31
    assert minutes_to_kickoff_for(-0.1) == 1
    assert minutes_to_kickoff_for(0.0) is None
    assert minutes_to_kickoff_for(50.0) is None


def test_transit_post_match_exceeds_first_half(crowd):
    assert crowd.level("transit_hub", 115.0) > crowd.level("transit_hub", 30.0)


def test_gates_peak_before_kickoff(crowd):
    assert crowd.level("gate_c", -30.0) > crowd.level("gate_c", 30.0)


def test_multiplier_and_labels():
    assert congestion_multiplier(0.5) == 2.0
    assert crowd_label(0.1) == "low"
    assert crowd_label(0.5) == "moderate"
    assert crowd_label(0.7) == "high"
    assert crowd_label(0.9) == "severe"
