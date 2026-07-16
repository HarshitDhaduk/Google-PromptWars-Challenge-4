"""Chat orchestrator: the provider-agnostic tool loop.

Owns hard safety caps (rounds, tool calls), collects ui_actions for the map,
keeps durable history to text turns only, and falls back to the mock provider
if Gemini fails - the demo never hard-fails on a free-tier hiccup.
"""

import logging
from dataclasses import dataclass

from ..core.clock import SimClock
from ..core.context import ContextService
from ..core.crowd import CrowdSimulator
from ..core.routing import Router
from ..core.seats import SeatSimulator
from ..core.stadium import StadiumRepository
from ..models.api import ChatRequest, ChatResponse, ToolCallMeta, TurnProvider
from ..models.entities import UiAction
from .prompts import build_system_prompt
from .provider import (
    ModelProvider,
    ProviderError,
    TextTurn,
    ToolExchange,
    ToolResult,
)
from .sessions import SessionStore
from .tools import ToolRegistry, ToolRuntime

logger = logging.getLogger("stadium_copilot.chat")

MAX_ROUNDS = 4
MAX_TOOL_CALLS_PER_REQUEST = 6

_FALLBACK_REPLY = {
    "en": "Sorry - I could not complete that request. Please try rephrasing, or visit Guest Services at Gate A or C.",
    "es": "Lo siento, no pude completar esa solicitud. Intenta reformularla o visita Atención al Cliente en la Puerta A o C.",
    "fr": "Désolé, je n'ai pas pu traiter cette demande. Reformulez-la ou adressez-vous aux services aux spectateurs (Porte A ou C).",
    "ar": "عذرًا، لم أتمكن من إكمال هذا الطلب. حاول إعادة الصياغة أو توجه إلى خدمات الضيوف عند البوابة A أو C.",
    "pt": "Desculpe, não consegui concluir esse pedido. Tente reformular ou procure o Atendimento ao Torcedor no Portão A ou C.",
    "de": "Entschuldigung, ich konnte diese Anfrage nicht abschließen. Bitte anders formulieren oder den Gästeservice an Gate A oder C fragen.",
}


@dataclass
class _LoopOutcome:
    reply: str
    ui_actions: list[UiAction]
    tool_calls: list[ToolCallMeta]


class ChatService:
    def __init__(
        self,
        *,
        primary: ModelProvider,
        mock_fallback: ModelProvider,
        registry: ToolRegistry,
        sessions: SessionStore,
        repo: StadiumRepository,
        crowd: CrowdSimulator,
        seats: SeatSimulator,
        router: Router,
        context: ContextService,
        clock: SimClock,
    ) -> None:
        self._primary = primary
        self._mock = mock_fallback
        self._registry = registry
        self._sessions = sessions
        self._repo = repo
        self._crowd = crowd
        self._seats = seats
        self._router = router
        self._context = context
        self._clock = clock

    def handle(self, request: ChatRequest) -> ChatResponse:
        minute = self._clock.sim_minute()
        fan = self._context.state(minute)
        runtime = ToolRuntime(
            repo=self._repo,
            crowd=self._crowd,
            seats=self._seats,
            router=self._router,
            fan=fan,
        )
        system = build_system_prompt(fan, self._repo, request.locale)
        history = self._sessions.history(request.session_id)

        outcome, provider_label = self._attempt(request, system, history, runtime)

        self._sessions.append(request.session_id, "user", request.message)
        self._sessions.append(request.session_id, "assistant", outcome.reply)
        return ChatResponse(
            reply=outcome.reply,
            ui_actions=outcome.ui_actions,
            tool_calls=outcome.tool_calls,
            provider=provider_label,
        )

    def _attempt(
        self,
        request: ChatRequest,
        system: str,
        history: list,
        runtime: ToolRuntime,
    ) -> tuple[_LoopOutcome, TurnProvider]:
        """Primary provider with one retry, then mock fallback (read-only tools
        make re-running the whole loop safe)."""
        attempts: list[tuple[ModelProvider, TurnProvider]]
        if self._primary is self._mock:
            attempts = [(self._primary, "mock")]
        else:
            attempts = [
                (self._primary, "gemini"),
                (self._primary, "gemini"),
                (self._mock, "mock-fallback"),
            ]

        last_error: ProviderError | None = None
        for provider, label in attempts:
            try:
                return self._run_loop(provider, request, system, history, runtime), label
            except ProviderError as err:
                last_error = err
                logger.warning("provider '%s' failed; trying next option", label)
        raise RuntimeError("all chat providers failed") from last_error

    def _run_loop(
        self,
        provider: ModelProvider,
        request: ChatRequest,
        system: str,
        history: list,
        runtime: ToolRuntime,
    ) -> _LoopOutcome:
        exchanges: list[ToolExchange] = []
        ui_actions: list[UiAction] = []
        tool_calls: list[ToolCallMeta] = []
        calls_budget = MAX_TOOL_CALLS_PER_REQUEST

        for _ in range(MAX_ROUNDS):
            turn = provider.generate_turn(
                system=system,
                history=history,
                message=request.message,
                locale=request.locale,
                exchanges=exchanges,
                declarations=self._registry.declarations,
            )
            if isinstance(turn, TextTurn):
                return _LoopOutcome(turn.text, ui_actions, tool_calls)

            results: list[ToolResult] = []
            for call in turn.calls:
                if calls_budget <= 0:
                    results.append(
                        ToolResult(call=call, data={"error": "tool_call_budget_exhausted"})
                    )
                    tool_calls.append(ToolCallMeta(name=call.name, ok=False))
                    continue
                calls_budget -= 1
                data, ui_action, ok = self._registry.execute(runtime, call.name, call.args)
                if ui_action is not None:
                    ui_actions.append(ui_action)
                tool_calls.append(ToolCallMeta(name=call.name, ok=ok))
                results.append(ToolResult(call=call, data=data))
            exchanges.append(
                ToolExchange(calls=list(turn.calls), results=results, raw_content=turn.raw_content)
            )

        reply = _FALLBACK_REPLY.get(request.locale, _FALLBACK_REPLY["en"])
        return _LoopOutcome(reply, ui_actions, tool_calls)
