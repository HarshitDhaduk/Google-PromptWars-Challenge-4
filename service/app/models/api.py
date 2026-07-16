"""Request/response schemas for the HTTP API."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .entities import (
    Amenity,
    CrowdInfo,
    Edge,
    Match,
    Phase,
    StadiumInfo,
    Ticket,
    UiAction,
    Zone,
)

Locale = Literal["en", "es", "fr", "ar", "pt", "de"]
LOCALES: tuple[str, ...] = ("en", "es", "fr", "ar", "pt", "de")

ProviderName = Literal["gemini", "mock"]
TurnProvider = Literal["gemini", "mock", "mock-fallback"]

UUID4_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}"
    r"-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_MESSAGE_CHARS = 500


class ChatRequest(BaseModel):
    session_id: str = Field(pattern=UUID4_PATTERN)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    locale: Locale = "en"

    @field_validator("message")
    @classmethod
    def _strip_and_require_visible_text(cls, value: str) -> str:
        cleaned = _CONTROL_CHARS.sub("", value).strip()
        if not cleaned:
            raise ValueError("message must contain visible characters")
        return cleaned


class ToolCallMeta(BaseModel):
    """Judge-facing evidence of grounding: which tool ran and whether it succeeded."""

    name: str
    ok: bool


class ChatResponse(BaseModel):
    reply: str
    ui_actions: list[UiAction] = []
    tool_calls: list[ToolCallMeta] = []
    provider: TurnProvider


class StadiumResponse(BaseModel):
    stadium: StadiumInfo
    zones: list[Zone]
    edges: list[Edge]
    amenities: list[Amenity]


class CrowdResponse(BaseModel):
    sim_time: datetime
    phase: Phase
    match_minute: int | None
    minutes_to_kickoff: int | None
    zones: dict[str, CrowdInfo]


class SimInfo(BaseModel):
    sim_time: datetime
    phase: Phase
    match_minute: int | None
    minutes_to_kickoff: int | None
    speed: float


class ContextResponse(BaseModel):
    match: Match
    ticket: Ticket
    sim: SimInfo
    provider: ProviderName
    locales: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    provider: ProviderName
    model: str | None
