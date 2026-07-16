"""Domain models: stadium topology, match fixture, routing, and chat UI actions."""

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

ZoneKind = Literal["gate", "concourse", "section", "transit"]
EdgeKind = Literal["walkway", "stairs", "elevator"]
AmenityCategory = Literal[
    "food", "restroom", "water", "first_aid", "prayer", "info", "merch", "sensory_room"
]
CrowdLabel = Literal["low", "moderate", "high", "severe"]
Phase = Literal["pre_match", "first_half", "halftime", "second_half", "post_match"]


class Zone(BaseModel):
    """A navigable node of the stadium graph (gate, concourse, sections, transit)."""

    id: str
    name: str
    kind: ZoneKind
    level: int
    x: float
    y: float
    sections: list[str] | None = None


class Edge(BaseModel):
    """An undirected connection between two zones; stairs/elevator pairs may run in parallel."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_zone: str = Field(alias="from")
    to_zone: str = Field(alias="to")
    kind: EdgeKind
    base_seconds: float = Field(gt=0)

    @property
    def accessible(self) -> bool:
        """Whether the edge is usable on a step-free route."""
        return self.kind != "stairs"


class Amenity(BaseModel):
    id: str
    name: str
    category: AmenityCategory
    zone_id: str
    tags: list[str] = []


class StadiumInfo(BaseModel):
    name: str
    city: str
    viewbox: str


class Ticket(BaseModel):
    holder: str
    match_id: str
    section: str
    row: str
    seat: str
    gate: str
    level: int


class MatchEvent(BaseModel):
    minute: int
    type: Literal["goal"]
    team: str
    player: str


class Match(BaseModel):
    id: str
    stage: str
    home: str
    away: str
    home_code: str
    away_code: str
    kickoff_utc: datetime
    gates_open_utc: datetime
    venue: str
    city: str
    events: list[MatchEvent] = []


class Point(BaseModel):
    x: float
    y: float


class RouteStep(BaseModel):
    """One leg of a route. The first step is the starting zone (edge_kind=None)."""

    zone_id: str
    name: str
    edge_kind: EdgeKind | None
    seconds: float
    congestion: CrowdLabel
    instruction_en: str


class RouteResult(BaseModel):
    from_zone: str
    to_zone: str
    accessible: bool
    total_seconds: float
    steps: list[RouteStep]
    polyline: list[Point]


class CrowdInfo(BaseModel):
    """Congestion of a zone: level in [0, 1], display label, and walk-time multiplier."""

    level: float
    label: CrowdLabel
    multiplier: float


SeatStatus = Literal["sold_out", "limited", "available"]


class SeatInfo(BaseModel):
    """Live box-office availability for one seating section."""

    section: str
    zone_id: str
    level: int
    capacity: int
    available: int
    status: SeatStatus


class AmenityWithEta(BaseModel):
    """An amenity enriched with the walk time from the fan's current location."""

    id: str
    name: str
    category: AmenityCategory
    zone_id: str
    zone_name: str
    eta_minutes: int
    tags: list[str] = []


class ShowRouteAction(BaseModel):
    type: Literal["show_route"] = "show_route"
    route: RouteResult


class HighlightAmenitiesAction(BaseModel):
    type: Literal["highlight_amenities"] = "highlight_amenities"
    amenities: list[AmenityWithEta]


class HighlightZoneAction(BaseModel):
    type: Literal["highlight_zone"] = "highlight_zone"
    zone_id: str


UiAction = Annotated[
    Union[ShowRouteAction, HighlightAmenitiesAction, HighlightZoneAction],
    Field(discriminator="type"),
]
