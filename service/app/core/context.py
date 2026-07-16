"""Fan context: who the fan is and where they most likely are right now.

There is no real positioning. Before kickoff the fan is assumed to be at
their assigned gate; from kickoff onwards, at their seat section. Chat tools
accept an explicit `from` location to override the inference.
"""

from dataclasses import dataclass

from ..models.entities import Match, Phase, Ticket, Zone
from .clock import phase_for_minute
from .stadium import StadiumRepository


@dataclass(frozen=True)
class FanState:
    ticket: Ticket
    match: Match
    seat_zone: Zone
    gate_zone: Zone
    current_zone: Zone
    phase: Phase
    minute: float


class ContextService:
    """Resolves the mock ticket against the stadium graph, failing fast if
    the fixtures disagree."""

    def __init__(self, repo: StadiumRepository, match: Match, ticket: Ticket) -> None:
        seat_zone = repo.zone_for_section(ticket.section)
        if seat_zone is None:
            raise ValueError(f"ticket section {ticket.section} not found in stadium data")
        gate_zone = repo.zone_for_gate(ticket.gate)
        if gate_zone is None:
            raise ValueError(f"ticket gate {ticket.gate} not found in stadium data")
        self.match = match
        self.ticket = ticket
        self.seat_zone = seat_zone
        self.gate_zone = gate_zone

    def state(self, minute: float) -> FanState:
        phase = phase_for_minute(minute)
        current_zone = self.gate_zone if phase == "pre_match" else self.seat_zone
        return FanState(
            ticket=self.ticket,
            match=self.match,
            seat_zone=self.seat_zone,
            gate_zone=self.gate_zone,
            current_zone=current_zone,
            phase=phase,
            minute=minute,
        )
