"""Read endpoints for stadium data, live crowd state, and fan context.

The chat endpoint is added by the LLM layer once providers exist; everything
here is deterministic and side-effect free.
"""

from fastapi import APIRouter, Request, Response

from ..core.clock import match_minute_for, minutes_to_kickoff_for, phase_for_minute
from ..models.api import (
    LOCALES,
    ContextResponse,
    CrowdResponse,
    HealthResponse,
    SimInfo,
    StadiumResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    state = request.app.state
    return HealthResponse(status="ok", provider=state.provider_name, model=state.model_name)


@router.get("/api/stadium", response_model=StadiumResponse)
def stadium(request: Request) -> StadiumResponse:
    repo = request.app.state.repo
    return StadiumResponse(
        stadium=repo.stadium,
        zones=repo.zones,
        edges=repo.edges,
        amenities=repo.amenities,
    )


@router.get("/api/crowd", response_model=CrowdResponse)
def crowd(request: Request, response: Response) -> CrowdResponse:
    response.headers["Cache-Control"] = "no-store"
    state = request.app.state
    minute = state.clock.sim_minute()
    return CrowdResponse(
        sim_time=state.clock.sim_time(),
        phase=phase_for_minute(minute),
        match_minute=match_minute_for(minute),
        minutes_to_kickoff=minutes_to_kickoff_for(minute),
        zones=state.crowd.snapshot(minute),
    )


@router.get("/api/context", response_model=ContextResponse)
def context(request: Request, response: Response) -> ContextResponse:
    response.headers["Cache-Control"] = "no-store"
    state = request.app.state
    minute = state.clock.sim_minute()
    return ContextResponse(
        match=state.context.match,
        ticket=state.context.ticket,
        sim=SimInfo(
            sim_time=state.clock.sim_time(),
            phase=phase_for_minute(minute),
            match_minute=match_minute_for(minute),
            minutes_to_kickoff=minutes_to_kickoff_for(minute),
            speed=state.clock.speed,
        ),
        provider=state.provider_name,
        locales=list(LOCALES),
    )
