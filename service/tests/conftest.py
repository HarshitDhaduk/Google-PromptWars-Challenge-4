"""Shared fixtures: real fixtures loaded once, deterministic seed everywhere."""

import pytest

from app.core.crowd import CrowdSimulator
from app.core.routing import Router
from app.core.stadium import StadiumRepository, load_match_fixture, load_repository

TEST_SEED = 2026


@pytest.fixture(scope="session")
def repo() -> StadiumRepository:
    return load_repository()


@pytest.fixture(scope="session")
def match_and_ticket():
    return load_match_fixture()


@pytest.fixture
def crowd(repo: StadiumRepository) -> CrowdSimulator:
    return CrowdSimulator(repo, seed=TEST_SEED)


@pytest.fixture
def router(repo: StadiumRepository, crowd: CrowdSimulator) -> Router:
    return Router(repo, crowd)


class StubCrowd:
    """Crowd stand-in with fully controlled levels, for exact routing math."""

    def __init__(self, levels: dict[str, float] | None = None, default: float = 0.05):
        self._levels = levels or {}
        self._default = default

    def level(self, zone_id: str, minute: float) -> float:
        return self._levels.get(zone_id, self._default)
