"""Congestion-aware shortest paths over the stadium graph.

Edge cost = base walk seconds x the average congestion multiplier of the two
endpoint zones, so a packed concourse genuinely pushes routes the long way
around the ring. Accessible mode drops stair edges before searching, forcing
the parallel elevator edges.
"""

import heapq
import math
from itertools import count

from ..models.entities import (
    CrowdLabel,
    Edge,
    Point,
    RouteResult,
    RouteStep,
    Zone,
)
from .crowd import CrowdSimulator, congestion_multiplier, crowd_label
from .stadium import StadiumRepository


class RouteNotFoundError(Exception):
    """No path satisfies the requested constraints (e.g. step-free)."""


class Router:
    def __init__(self, repo: StadiumRepository, crowd: CrowdSimulator) -> None:
        self._repo = repo
        self._crowd = crowd

    def route(
        self,
        from_zone: str,
        to_zone: str,
        minute: float,
        accessible: bool = False,
    ) -> RouteResult:
        zones = self._repo.zones_by_id
        for zone_id in (from_zone, to_zone):
            if zone_id not in zones:
                raise ValueError(f"unknown zone: {zone_id}")

        levels = {zone_id: self._crowd.level(zone_id, minute) for zone_id in zones}
        multipliers = {
            zone_id: congestion_multiplier(level) for zone_id, level in levels.items()
        }

        def edge_cost(edge: Edge) -> float:
            pair = (multipliers[edge.from_zone] + multipliers[edge.to_zone]) / 2.0
            return edge.base_seconds * pair

        parent = self._search(from_zone, to_zone, accessible, edge_cost)
        if from_zone != to_zone and to_zone not in parent:
            constraint = "step-free " if accessible else ""
            raise RouteNotFoundError(
                f"no {constraint}path from {from_zone} to {to_zone}"
            )

        path = _reconstruct(zones, parent, from_zone, to_zone)
        steps, total_seconds = _build_steps(path, levels, edge_cost)
        return RouteResult(
            from_zone=from_zone,
            to_zone=to_zone,
            accessible=accessible,
            total_seconds=round(total_seconds),
            steps=steps,
            polyline=[Point(x=zone.x, y=zone.y) for zone, _ in path],
        )

    def eta_minutes(
        self,
        from_zone: str,
        to_zone: str,
        minute: float,
        accessible: bool = False,
    ) -> int:
        """Congestion-weighted walk time in whole minutes (at least 1)."""
        result = self.route(from_zone, to_zone, minute, accessible)
        return max(1, math.ceil(result.total_seconds / 60.0))

    def _search(self, from_zone, to_zone, accessible, edge_cost):
        """Dijkstra; returns the parent map {zone_id: (previous_zone_id, edge)}."""
        best: dict[str, float] = {from_zone: 0.0}
        parent: dict[str, tuple[str, Edge]] = {}
        tiebreak = count()  # deterministic ordering for equal-cost entries
        frontier: list[tuple[float, int, str]] = [(0.0, next(tiebreak), from_zone)]
        visited: set[str] = set()

        while frontier:
            cost, _, current = heapq.heappop(frontier)
            if current in visited:
                continue
            if current == to_zone:
                break
            visited.add(current)
            for neighbor, edge in self._repo.neighbors(current):
                if neighbor in visited:
                    continue
                if accessible and not edge.accessible:
                    continue
                candidate = cost + edge_cost(edge)
                if candidate < best.get(neighbor, math.inf):
                    best[neighbor] = candidate
                    parent[neighbor] = (current, edge)
                    heapq.heappush(frontier, (candidate, next(tiebreak), neighbor))
        return parent


def _reconstruct(
    zones: dict[str, Zone],
    parent: dict[str, tuple[str, Edge]],
    from_zone: str,
    to_zone: str,
) -> list[tuple[Zone, Edge | None]]:
    """Ordered (zone, edge_used_to_reach_it) pairs; the first edge is None."""
    path: list[tuple[Zone, Edge | None]] = []
    cursor = to_zone
    while cursor != from_zone:
        previous, edge = parent[cursor]
        path.append((zones[cursor], edge))
        cursor = previous
    path.append((zones[from_zone], None))
    path.reverse()
    return path


def _build_steps(path, levels, edge_cost) -> tuple[list[RouteStep], float]:
    steps: list[RouteStep] = []
    total_seconds = 0.0
    for index, (zone, edge) in enumerate(path):
        seconds = edge_cost(edge) if edge else 0.0
        total_seconds += seconds
        label = crowd_label(levels[zone.id])
        previous_zone = path[index - 1][0] if index else None
        steps.append(
            RouteStep(
                zone_id=zone.id,
                name=zone.name,
                edge_kind=edge.kind if edge else None,
                seconds=round(seconds),
                congestion=label,
                instruction_en=_instruction_en(zone, edge, previous_zone, seconds, label),
            )
        )
    return steps, total_seconds


def _instruction_en(
    zone: Zone,
    edge: Edge | None,
    previous_zone: Zone | None,
    seconds: float,
    label: CrowdLabel,
) -> str:
    if edge is None:
        if zone.kind == "gate":
            return f"Enter through {zone.name}"
        return f"Start at {zone.name}"
    minutes = max(1, round(seconds / 60.0))
    if edge.kind in ("stairs", "elevator"):
        direction = "up" if previous_zone and zone.level > previous_zone.level else "down"
        verb = "stairs" if edge.kind == "stairs" else "elevator"
        return f"Take the {verb} {direction} to {zone.name} (~{minutes} min)"
    return f"Walk to {zone.name} (~{minutes} min, {label} crowd)"
