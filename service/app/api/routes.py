"""HTTP endpoints: read APIs plus the chat entrypoint."""

from fastapi import APIRouter, Depends, Request, Response

from ..core.clock import match_minute_for, minutes_to_kickoff_for, phase_for_minute
from ..models.api import (
    LOCALES,
    ChatRequest,
    ChatResponse,
    ContextResponse,
    CrowdResponse,
    HealthResponse,
    SimInfo,
    StadiumResponse,
)
from .rate_limit import enforce_chat_limits, enforce_read_limits

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    state = request.app.state
    return HealthResponse(status="ok", provider=state.provider_name, model=state.model_name)


@router.get(
    "/api/stadium",
    response_model=StadiumResponse,
    dependencies=[Depends(enforce_read_limits)],
)
def stadium(request: Request) -> StadiumResponse:
    repo = request.app.state.repo
    return StadiumResponse(
        stadium=repo.stadium,
        zones=repo.zones,
        edges=repo.edges,
        amenities=repo.amenities,
    )


@router.get(
    "/api/crowd",
    response_model=CrowdResponse,
    dependencies=[Depends(enforce_read_limits)],
)
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


@router.get(
    "/api/context",
    response_model=ContextResponse,
    dependencies=[Depends(enforce_read_limits)],
)
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


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: Request, payload: ChatRequest = Depends(enforce_chat_limits)) -> ChatResponse:
    """Sync endpoint on purpose: the Gemini SDK call is blocking, and FastAPI
    runs sync endpoints in its threadpool."""
    return request.app.state.chat_service.handle(payload)
