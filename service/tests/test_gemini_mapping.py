"""Gemini wire-format mapping, tested without a client or network access."""

from google.genai import types

from app.llm.gemini import build_contents, to_function_declarations
from app.llm.provider import (
    HistoryTurn,
    ToolCall,
    ToolDeclaration,
    ToolExchange,
    ToolResult,
)


def test_declarations_pass_json_schema_through():
    declaration = ToolDeclaration(
        name="get_route",
        description="Route between zones.",
        parameters={
            "type": "object",
            "properties": {"to": {"type": "string"}},
            "required": ["to"],
        },
    )

    (converted,) = to_function_declarations([declaration])

    assert converted.name == "get_route"
    assert converted.description == "Route between zones."
    assert converted.parameters_json_schema == declaration.parameters


def test_build_contents_orders_history_message_and_tool_exchange():
    history = [
        HistoryTurn(role="user", text="hi"),
        HistoryTurn(role="assistant", text="hello!"),
    ]
    call = ToolCall(name="get_route", args={"to": "my_seat"})
    exchange = ToolExchange(
        calls=[call],
        results=[ToolResult(call=call, data={"total_minutes": 9})],
    )

    contents = build_contents(history, "take me to my seat", [exchange])

    assert [content.role for content in contents] == ["user", "model", "user", "model", "user"]
    function_call_part = contents[3].parts[0]
    assert function_call_part.function_call.name == "get_route"
    assert dict(function_call_part.function_call.args) == {"to": "my_seat"}
    function_response_part = contents[4].parts[0]
    assert function_response_part.function_response.name == "get_route"
    assert function_response_part.function_response.response == {
        "result": {"total_minutes": 9}
    }


def test_build_contents_replays_raw_model_content_verbatim():
    raw = types.Content(
        role="model",
        parts=[types.Part.from_function_call(name="get_route", args={"to": "my_seat"})],
    )
    call = ToolCall(name="get_route", args={"to": "my_seat"})
    exchange = ToolExchange(
        calls=[call],
        results=[ToolResult(call=call, data={"ok": True})],
        raw_content=raw,
    )

    contents = build_contents([], "msg", [exchange])

    assert contents[1] is raw
