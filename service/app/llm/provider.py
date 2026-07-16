"""Provider abstraction: one model-generation step, provider-agnostic.

The orchestrator (chat.py) owns the tool loop and never touches SDK types.
Providers translate the neutral conversation view below into their wire
format. `raw_content` lets a provider carry its own verbatim model content
(e.g. Gemini function-call parts with thought signatures) across rounds
without the orchestrator knowing what it is.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence, Union


@dataclass(frozen=True)
class ToolDeclaration:
    """Neutral tool schema; `parameters` is plain JSON Schema."""

    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    data: dict


@dataclass(frozen=True)
class HistoryTurn:
    role: Literal["user", "assistant"]
    text: str


@dataclass
class ToolExchange:
    """One completed round: the model's calls and the tools' answers."""

    calls: list[ToolCall]
    results: list[ToolResult] = field(default_factory=list)
    raw_content: object | None = None


@dataclass(frozen=True)
class TextTurn:
    text: str


@dataclass(frozen=True)
class FunctionCallTurn:
    calls: list[ToolCall]
    raw_content: object | None = None


Turn = Union[TextTurn, FunctionCallTurn]


class ProviderError(RuntimeError):
    """The model provider failed to produce a usable turn."""


class ModelProvider(Protocol):
    name: str

    def generate_turn(
        self,
        *,
        system: str,
        history: Sequence[HistoryTurn],
        message: str,
        locale: str,
        exchanges: Sequence[ToolExchange],
        declarations: Sequence[ToolDeclaration],
    ) -> Turn:
        """Produce the next turn given the conversation so far."""
        ...
