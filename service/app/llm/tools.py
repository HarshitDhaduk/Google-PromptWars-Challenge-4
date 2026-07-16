"""Tool layer: the grounding contract between the model and the engines.

Every tool is read-only over fixtures and simulation state and returns
(model_facing_data, optional_ui_action). Inputs are validated here so a
wrong id comes back as a self-correcting error payload the model can fix
on its next round, never as an exception.
"""

import logging
import math
from dataclasses import dataclass
from typing import Callable, Sequence

from ..core.clock import match_minute_for, minutes_to_kickoff_for
from ..core.context import FanState, score_at
from ..core.crowd import CrowdSimulator
from ..core.routing import RouteNotFoundError, Router
from ..core.stadium import StadiumRepository
from ..models.entities import (
    AmenityWithEta,
    HighlightAmenitiesAction,
    HighlightZoneAction,
    ShowRouteAction,
    UiAction,
    Zone,
)
from .provider import ToolDeclaration

logger = logging.getLogger("stadium_copilot.tools")

DIETARY_TAGS = ("halal", "vegetarian", "vegan", "gluten_free")
DEFAULT_AMENITY_LIMIT = 3
MAX_AMENITY_LIMIT = 5

TRANSIT_HUB_ZONE = "transit_hub"
RIDESHARE_GATE_ZONE = "gate_a"


@dataclass(frozen=True)
class ToolRuntime:
    """Everything a tool may read; captured once per chat request."""

    repo: StadiumRepository
    crowd: CrowdSimulator
    router: Router
    fan: FanState


class ToolInputError(Exception):
    """Invalid tool arguments; `extra` becomes the self-correction payload."""

    def __init__(self, code: str, extra: dict | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.extra = extra or {}


ToolImpl = Callable[[ToolRuntime, dict], tuple[dict, UiAction | None]]


@dataclass(frozen=True)
class Tool:
    declaration: ToolDeclaration
    run: ToolImpl


class ToolRegistry:
    def __init__(self, tools: Sequence[Tool]) -> None:
        self._tools = {tool.declaration.name: tool for tool in tools}

    @property
    def declarations(self) -> list[ToolDeclaration]:
        return [tool.declaration for tool in self._tools.values()]

    def execute(
        self, runtime: ToolRuntime, name: str, args: dict | None
    ) -> tuple[dict, UiAction | None, bool]:
        """Run a tool; never raises. Returns (data, ui_action, ok)."""
        tool = self._tools.get(name)
        if tool is None:
            return {"error": "unknown_tool", "valid_tools": sorted(self._tools)}, None, False
        try:
            data, ui_action = tool.run(runtime, args or {})
            return data, ui_action, True
        except ToolInputError as err:
            return {"error": err.code, **err.extra}, None, False
        except RouteNotFoundError as err:
            return {"error": "no_route", "detail": str(err)}, None, False
        except Exception:
            logger.exception("tool %s failed", name)
            return {"error": "tool_failed"}, None, False


# --------------------------------------------------------------------------
# Location resolution shared by routing-flavored tools
# --------------------------------------------------------------------------

_SELF_REFS = frozenset({"", "current", "my_location", "here"})
_SEAT_REFS = frozenset({"my_seat", "seat"})
_GATE_REFS = frozenset({"my_gate", "assigned_gate"})


def _resolve_location(runtime: ToolRuntime, ref: object) -> Zone:
    """Accepts zone ids, amenity ids, section numbers, gate letters, 'my_seat'."""
    if ref is None:
        return runtime.fan.current_zone
    token = str(ref).strip()
    lowered = token.lower()
    if lowered in _SELF_REFS:
        return runtime.fan.current_zone
    if lowered in _SEAT_REFS:
        return runtime.fan.seat_zone
    if lowered in _GATE_REFS:
        return runtime.fan.gate_zone

    repo = runtime.repo
    zone = repo.zones_by_id.get(lowered)
    if zone is not None:
        return zone
    amenity = repo.amenities_by_id.get(lowered)
    if amenity is not None:
        return repo.zones_by_id[amenity.zone_id]
    section_zone = repo.zone_for_section(token)
    if section_zone is not None:
        return section_zone
    if len(token) == 1:
        gate_zone = repo.zone_for_gate(token)
        if gate_zone is not None:
            return gate_zone
    raise ToolInputError(
        "unknown_location",
        {
            "given": token,
            "valid_zone_ids": sorted(repo.zones_by_id),
            "valid_amenity_ids": sorted(repo.amenities_by_id),
            "also_accepted": ["my_seat", "my_gate", "current", "a section number like '324'"],
        },
    )


# --------------------------------------------------------------------------
# Tool implementations
# --------------------------------------------------------------------------


def _get_ticket_context(runtime: ToolRuntime, _: dict) -> tuple[dict, UiAction | None]:
    fan = runtime.fan
    ticket = fan.ticket
    data = {
        "match": f"{fan.match.home} vs {fan.match.away} - {fan.match.stage}",
        "section": ticket.section,
        "row": ticket.row,
        "seat": ticket.seat,
        "entry_gate": ticket.gate,
        "seat_zone_id": fan.seat_zone.id,
        "seat_zone_name": fan.seat_zone.name,
        "gate_zone_id": fan.gate_zone.id,
        "current_location_zone_id": fan.current_zone.id,
        "current_location_name": fan.current_zone.name,
        "location_note": (
            "Location is inferred from the match phase. If the fan says they are "
            "somewhere else, pass it as `from` in get_route."
        ),
    }
    return data, None


def _get_match_info(runtime: ToolRuntime, _: dict) -> tuple[dict, UiAction | None]:
    fan = runtime.fan
    match = fan.match
    scoreboard_minute = match_minute_for(fan.minute)
    home_goals, away_goals = score_at(match, scoreboard_minute)
    events = [
        {"minute": event.minute, "type": event.type, "team": event.team, "player": event.player}
        for event in match.events
        if scoreboard_minute is not None and event.minute <= scoreboard_minute
    ]
    data = {
        "stage": match.stage,
        "fixture": f"{match.home} vs {match.away}",
        "venue": f"{match.venue}, {match.city}",
        "kickoff_utc": match.kickoff_utc.isoformat(),
        "phase": fan.phase,
        "match_minute": scoreboard_minute,
        "minutes_to_kickoff": minutes_to_kickoff_for(fan.minute),
        "score": (
            f"{match.home} {home_goals}-{away_goals} {match.away}"
            if scoreboard_minute is not None
            else "not started"
        ),
        "events_so_far": events,
    }
    return data, None


def _find_amenities(runtime: ToolRuntime, args: dict) -> tuple[dict, UiAction | None]:
    repo = runtime.repo
    valid_categories = sorted({amenity.category for amenity in repo.amenities})
    category = str(args.get("category", "")).strip().lower()
    if category not in valid_categories:
        raise ToolInputError("unknown_category", {"valid_categories": valid_categories})

    dietary = args.get("dietary")
    if dietary is not None:
        dietary = str(dietary).strip().lower()
        if dietary not in DIETARY_TAGS:
            raise ToolInputError("unknown_dietary_tag", {"valid_dietary_tags": list(DIETARY_TAGS)})

    try:
        limit = int(args.get("limit") or DEFAULT_AMENITY_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_AMENITY_LIMIT
    limit = max(1, min(limit, MAX_AMENITY_LIMIT))

    origin = runtime.fan.current_zone
    enriched = [
        AmenityWithEta(
            id=amenity.id,
            name=amenity.name,
            category=amenity.category,
            zone_id=amenity.zone_id,
            zone_name=repo.zones_by_id[amenity.zone_id].name,
            eta_minutes=runtime.router.eta_minutes(origin.id, amenity.zone_id, runtime.fan.minute),
            tags=amenity.tags,
        )
        for amenity in repo.amenities
        if amenity.category == category and (dietary is None or dietary in amenity.tags)
    ]
    enriched.sort(key=lambda item: (item.eta_minutes, item.name))
    selected = enriched[:limit]

    data = {
        "from_zone": origin.id,
        "from_name": origin.name,
        "results": [item.model_dump() for item in selected],
    }
    if not selected:
        data["note"] = "No amenities match these filters."
        return data, None
    return data, HighlightAmenitiesAction(amenities=selected)


def _get_route(runtime: ToolRuntime, args: dict) -> tuple[dict, UiAction | None]:
    if not args.get("to"):
        raise ToolInputError("missing_destination", {"hint": "pass `to` (zone id, amenity id, section number, or 'my_seat')"})
    destination = _resolve_location(runtime, args.get("to"))
    origin = _resolve_location(runtime, args.get("from"))
    accessible = bool(args.get("accessible", False))

    route = runtime.router.route(origin.id, destination.id, runtime.fan.minute, accessible=accessible)
    data = {
        "from": origin.name,
        "to": destination.name,
        "accessible": accessible,
        "total_minutes": max(1, math.ceil(route.total_seconds / 60.0)),
        "steps": [step.instruction_en for step in route.steps],
    }
    if origin.id == destination.id:
        data["note"] = "Origin and destination are the same zone - the fan is already there."
    if destination.id == runtime.fan.seat_zone.id:
        ticket = runtime.fan.ticket
        data["at_destination"] = f"Section {ticket.section}, Row {ticket.row}, Seat {ticket.seat}"
    return data, ShowRouteAction(route=route)


def _get_crowd_status(runtime: ToolRuntime, args: dict) -> tuple[dict, UiAction | None]:
    minute = runtime.fan.minute
    zone_ref = args.get("zone_id")
    if zone_ref:
        zone = runtime.repo.zones_by_id.get(str(zone_ref).strip().lower())
        if zone is None:
            raise ToolInputError("unknown_zone", {"valid_zone_ids": sorted(runtime.repo.zones_by_id)})
        info = runtime.crowd.info(zone.id, minute)
        data = {
            "zone_id": zone.id,
            "zone_name": zone.name,
            "phase": runtime.fan.phase,
            "crowd_label": info.label,
            "crowd_level": info.level,
            "walk_time_multiplier": info.multiplier,
        }
        return data, HighlightZoneAction(zone_id=zone.id)

    snapshot = runtime.crowd.snapshot(minute)
    ranked = sorted(snapshot.items(), key=lambda item: item[1].level, reverse=True)

    def summarize(zone_id: str) -> dict:
        info = snapshot[zone_id]
        return {
            "zone_id": zone_id,
            "zone_name": runtime.repo.zones_by_id[zone_id].name,
            "crowd_label": info.label,
            "crowd_level": info.level,
        }

    data = {
        "phase": runtime.fan.phase,
        "busiest": [summarize(zone_id) for zone_id, _ in ranked[:5]],
        "calmest": [summarize(zone_id) for zone_id, _ in ranked[-3:][::-1]],
    }
    return data, None


def _get_transit_advice(runtime: ToolRuntime, _: dict) -> tuple[dict, UiAction | None]:
    fan = runtime.fan
    minute = fan.minute
    hub = runtime.repo.zones_by_id[TRANSIT_HUB_ZONE]
    hub_info = runtime.crowd.info(hub.id, minute)
    hub_eta = runtime.router.eta_minutes(fan.current_zone.id, hub.id, minute)
    rideshare_eta = runtime.router.eta_minutes(fan.current_zone.id, RIDESHARE_GATE_ZONE, minute)

    options = [
        {
            "mode": "rail",
            "boarding_at": hub.name,
            "walk_eta_minutes": hub_eta,
            "crowd_label": hub_info.label,
            "note": "NJ Transit Meadowlands rail shuttle to Secaucus Junction.",
        },
        {
            "mode": "bus",
            "boarding_at": hub.name,
            "walk_eta_minutes": hub_eta,
            "crowd_label": hub_info.label,
            "note": "Coach USA 351 event bus toward Port Authority.",
        },
        {
            "mode": "rideshare",
            "boarding_at": "Rideshare lot outside Gate A",
            "walk_eta_minutes": rideshare_eta,
            "crowd_label": runtime.crowd.info(RIDESHARE_GATE_ZONE, minute).label,
            "note": "Expect surge pricing right after the final whistle.",
        },
    ]

    if fan.phase == "pre_match":
        advice_key = "pre_match"
        recommendation = (
            f"No exit planning needed yet - enjoy the build-up. The rail plaza is {hub_info.label} "
            f"and about {hub_eta} min away."
        )
    elif fan.phase in ("first_half", "halftime") or minute < 90:
        advice_key = "enjoy"
        recommendation = (
            "Relax and enjoy the match. Ask me again around the 75th minute and I will time "
            "your exit against the rail crowds."
        )
    elif fan.phase == "second_half":
        advice_key = "leave_early"
        recommendation = (
            f"If you want to beat the rush, leave about 10 minutes before the final whistle: "
            f"the rail plaza is {hub_info.label} now but typically severe for ~30 minutes after full time."
        )
    elif hub_info.label in ("high", "severe"):
        advice_key = "wait_out"
        recommendation = (
            f"The rail plaza is {hub_info.label} right now. Waiting 20-30 minutes on the concourse, "
            f"or taking the bus queue, is usually faster than joining the crush."
        )
    else:
        advice_key = "go_now"
        recommendation = (
            f"Crowds have eased - head to {hub.name} now, about {hub_eta} min from {fan.current_zone.name}."
        )

    data = {
        "phase": fan.phase,
        "from": fan.current_zone.name,
        "rail_plaza_crowd": hub_info.label,
        "advice_key": advice_key,
        "options": options,
        "recommendation": recommendation,
    }
    return data, HighlightZoneAction(zone_id=hub.id)


# --------------------------------------------------------------------------
# Declarations (plain JSON Schema via parameters_json_schema)
# --------------------------------------------------------------------------


def build_tool_registry() -> ToolRegistry:
    amenity_categories = [
        "food", "restroom", "water", "first_aid", "prayer", "info", "merch", "sensory_room",
    ]
    location_hint = (
        "A zone id (e.g. 'conc_100_e'), amenity id (e.g. 'food_halal_e'), "
        "section number (e.g. '324'), gate letter, or 'my_seat'/'my_gate'/'current'."
    )
    tools = [
        Tool(
            ToolDeclaration(
                name="get_ticket_context",
                description=(
                    "The fan's ticket (section/row/seat, entry gate) and their inferred "
                    "current location inside the stadium."
                ),
                parameters={"type": "object", "properties": {}},
            ),
            _get_ticket_context,
        ),
        Tool(
            ToolDeclaration(
                name="get_match_info",
                description="Live match state: fixture, phase, scoreboard minute, score, and goals so far.",
                parameters={"type": "object", "properties": {}},
            ),
            _get_match_info,
        ),
        Tool(
            ToolDeclaration(
                name="find_amenities",
                description=(
                    "Find the nearest amenities by walk time from the fan's current location. "
                    "Use dietary only with category='food'."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": amenity_categories,
                            "description": "Amenity category to search for.",
                        },
                        "dietary": {
                            "type": "string",
                            "enum": list(DIETARY_TAGS),
                            "description": "Optional dietary filter for food.",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": MAX_AMENITY_LIMIT,
                            "description": "Maximum number of results (default 3).",
                        },
                    },
                    "required": ["category"],
                },
            ),
            _find_amenities,
        ),
        Tool(
            ToolDeclaration(
                name="get_route",
                description=(
                    "Congestion-aware walking route between two places in the stadium. "
                    "Set accessible=true for a step-free route (elevators, no stairs)."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": f"Destination. {location_hint}"},
                        "from": {
                            "type": "string",
                            "description": f"Origin; defaults to the fan's current location. {location_hint}",
                        },
                        "accessible": {
                            "type": "boolean",
                            "description": "True for a step-free route.",
                        },
                    },
                    "required": ["to"],
                },
            ),
            _get_route,
        ),
        Tool(
            ToolDeclaration(
                name="get_crowd_status",
                description=(
                    "Live crowd congestion. Pass zone_id for one zone, or omit it for the "
                    "busiest/calmest stadium-wide summary."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "zone_id": {
                            "type": "string",
                            "description": "Optional zone id to inspect.",
                        }
                    },
                },
            ),
            _get_crowd_status,
        ),
        Tool(
            ToolDeclaration(
                name="get_transit_advice",
                description=(
                    "Phase-aware advice for leaving the stadium: rail/bus/rideshare options, "
                    "walk times, crowd levels, and a recommendation on when to leave."
                ),
                parameters={"type": "object", "properties": {}},
            ),
            _get_transit_advice,
        ),
    ]
    return ToolRegistry(tools)
