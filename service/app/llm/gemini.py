"""All google-genai SDK contact, isolated behind the ModelProvider protocol.

The mapping helpers are module functions so they can be unit-tested without
a client or network access.
"""

import logging
from typing import Sequence

from google import genai
from google.genai import types

from .provider import (
    FunctionCallTurn,
    HistoryTurn,
    ProviderError,
    TextTurn,
    ToolCall,
    ToolDeclaration,
    ToolExchange,
    Turn,
)

logger = logging.getLogger("stadium_copilot.gemini")

REQUEST_TIMEOUT_MS = 25_000
TEMPERATURE = 0.4
MAX_OUTPUT_TOKENS = 1024


def to_function_declarations(
    declarations: Sequence[ToolDeclaration],
) -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name=declaration.name,
            description=declaration.description,
            parameters_json_schema=declaration.parameters,
        )
        for declaration in declarations
    ]


def build_contents(
    history: Sequence[HistoryTurn],
    message: str,
    exchanges: Sequence[ToolExchange],
) -> list[types.Content]:
    """Neutral conversation -> Gemini contents.

    Function responses use role "user", per the Gemini function-calling
    protocol. When available, the model's verbatim content (raw_content,
    which may carry thought signatures) is replayed instead of a rebuilt one.
    """
    contents = [
        types.Content(
            role="user" if turn.role == "user" else "model",
            parts=[types.Part.from_text(text=turn.text)],
        )
        for turn in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    for exchange in exchanges:
        if exchange.raw_content is not None:
            contents.append(exchange.raw_content)
        else:
            contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(name=call.name, args=call.args)
                        for call in exchange.calls
                    ],
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name=result.call.name, response={"result": result.data}
                    )
                    for result in exchange.results
                ],
            )
        )
    return contents


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, models: Sequence[str]) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
        # Ordered, de-duplicated: the primary model first, then fallbacks
        # tried when the primary is unavailable (e.g. 503 capacity spikes).
        self._models = list(dict.fromkeys(model for model in models if model))

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
        del locale  # Gemini infers the reply language from the message itself
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=to_function_declarations(declarations))],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        contents = build_contents(history, message, exchanges)

        last_error: Exception | None = None
        for model in self._models:
            try:
                response = self._client.models.generate_content(
                    model=model, contents=contents, config=config
                )
                return _to_turn(response)
            except Exception as err:
                # Log the error class only; never echo payloads or headers.
                logger.warning("gemini call failed on %s: %s", model, type(err).__name__)
                last_error = err
        raise ProviderError("all gemini models failed") from last_error


def _to_turn(response: types.GenerateContentResponse) -> Turn:
    calls = response.function_calls or []
    if calls:
        raw_content = response.candidates[0].content if response.candidates else None
        return FunctionCallTurn(
            calls=[
                ToolCall(name=call.name or "", args=dict(call.args or {}))
                for call in calls
            ],
            raw_content=raw_content,
        )
    text = (response.text or "").strip()
    if not text:
        raise ProviderError("gemini returned an empty response")
    return TextTurn(text=text)
