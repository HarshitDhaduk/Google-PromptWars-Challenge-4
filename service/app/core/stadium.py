"""Fixture loading and indexed, validated read access to stadium data."""

import json
from pathlib import Path

from ..models.entities import Amenity, Edge, Match, StadiumInfo, Ticket, Zone

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class StadiumDataError(ValueError):
    """The stadium fixtures are internally inconsistent."""


class StadiumRepository:
    """Read-only, indexed view over the validated stadium fixtures."""

    def __init__(
        self,
        stadium: StadiumInfo,
        zones: list[Zone],
        edges: list[Edge],
        amenities: list[Amenity],
    ) -> None:
        self.stadium = stadium
        self.zones = zones
        self.edges = edges
        self.amenities = amenities
        self.zones_by_id = {zone.id: zone for zone in zones}
        self.amenities_by_id = {amenity.id: amenity for amenity in amenities}
        self._zone_by_section = {
            section: zone.id
            for zone in zones
            if zone.sections
            for section in zone.sections
        }
        self._validate()
        self.adjacency: dict[str, list[Edge]] = {zone.id: [] for zone in zones}
        for edge in edges:
            self.adjacency[edge.from_zone].append(edge)
            self.adjacency[edge.to_zone].append(edge)

    def _validate(self) -> None:
        if len(self.zones_by_id) != len(self.zones):
            raise StadiumDataError("duplicate zone ids in stadium.json")
        if len(self.amenities_by_id) != len(self.amenities):
            raise StadiumDataError("duplicate amenity ids in stadium.json")
        edge_ids = {edge.id for edge in self.edges}
        if len(edge_ids) != len(self.edges):
            raise StadiumDataError("duplicate edge ids in stadium.json")
        for edge in self.edges:
            for endpoint in (edge.from_zone, edge.to_zone):
                if endpoint not in self.zones_by_id:
                    raise StadiumDataError(
                        f"edge {edge.id} references unknown zone {endpoint}"
                    )
        for amenity in self.amenities:
            if amenity.zone_id not in self.zones_by_id:
                raise StadiumDataError(
                    f"amenity {amenity.id} references unknown zone {amenity.zone_id}"
                )

    def zone_for_section(self, section: str) -> Zone | None:
        zone_id = self._zone_by_section.get(section.strip())
        return self.zones_by_id.get(zone_id) if zone_id else None

    def zone_for_gate(self, gate: str) -> Zone | None:
        return self.zones_by_id.get(f"gate_{gate.strip().lower()}")

    def neighbors(self, zone_id: str) -> list[tuple[str, Edge]]:
        """(neighbor_zone_id, edge) for every edge touching `zone_id`."""
        result: list[tuple[str, Edge]] = []
        for edge in self.adjacency[zone_id]:
            other = edge.to_zone if edge.from_zone == zone_id else edge.from_zone
            result.append((other, edge))
        return result


def load_repository(data_dir: Path = DATA_DIR) -> StadiumRepository:
    raw = json.loads((data_dir / "stadium.json").read_text(encoding="utf-8"))
    return StadiumRepository(
        stadium=StadiumInfo.model_validate(raw["stadium"]),
        zones=[Zone.model_validate(zone) for zone in raw["zones"]],
        edges=[Edge.model_validate(edge) for edge in raw["edges"]],
        amenities=[Amenity.model_validate(amenity) for amenity in raw["amenities"]],
    )


def load_match_fixture(data_dir: Path = DATA_DIR) -> tuple[Match, Ticket]:
    raw = json.loads((data_dir / "match.json").read_text(encoding="utf-8"))
    return Match.model_validate(raw["match"]), Ticket.model_validate(raw["ticket"])
