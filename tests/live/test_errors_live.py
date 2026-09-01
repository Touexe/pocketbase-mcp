"""Section 10 — live error contract: every provokable branch carries a usable hint
and no traceback."""

from __future__ import annotations

import pytest

from .helpers import assert_no_traceback, err_payload, serialize

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [{"name": "title", "type": "text", "required": True}]


async def test_unknown_collection(live_client) -> None:
    """10.1 — an unknown collection returns COLLECTION_NOT_FOUND, hint names describe_schema."""
    result = await live_client.call_tool(
        "find_records", {"collection": "mcptest_no_such_collection_zzzz"}, raise_on_error=False
    )
    payload = err_payload(result)
    assert payload["error_type"] == "COLLECTION_NOT_FOUND"
    assert "describe_schema" in payload["hint"]


async def test_record_not_found(live_client, live_collection) -> None:
    """10.2 — a well-formed but absent record id returns RECORD_NOT_FOUND with a non-empty hint."""
    name = await live_collection("err", _FIELDS)
    result = await live_client.call_tool(
        "find_records", {"collection": name, "record_id": "abcdefghijklmno"}, raise_on_error=False
    )
    payload = err_payload(result)
    assert payload["error_type"] == "RECORD_NOT_FOUND"
    assert payload["hint"]


async def test_validation_error_names_field_and_known_fields(live_client, live_collection) -> None:
    """10.3 — an unknown field in a write_record payload names the field and the known field names."""
    name = await live_collection("err", _FIELDS)
    result = await live_client.call_tool(
        "write_record",
        {"collection": name, "action": "create", "data": {"title": "ok", "ghostfield": 1}},
        raise_on_error=False,
    )
    payload = err_payload(result)
    assert payload["error_type"] == "VALIDATION_ERROR"
    assert "ghostfield" in payload["message"]
    assert "title" in payload["message"]


async def test_unauthorized_from_anonymous_state(anon_client) -> None:
    """10.4 — an unauthorized call from an anonymous state names connect in its hint."""
    result = await anon_client.call_tool(
        "find_records", {"collection": "_superusers"}, raise_on_error=False
    )
    payload = err_payload(result)
    assert payload["ok"] is False
    assert "UNAUTHOR" in (payload["error_type"] or "") or "PERMISSION" in (payload["error_type"] or "")
    assert "connect" in (payload["hint"] or "").lower()


async def test_no_error_message_leaks_a_traceback(live_client, live_collection) -> None:
    """10.5 — no live error message contains a stack trace or a Python exception class name."""
    name = await live_collection("err", _FIELDS)
    provocations = [
        ("find_records", {"collection": "mcptest_absent_zzzz"}),
        ("find_records", {"collection": name, "record_id": "abcdefghijklmno"}),
        ("write_record", {"collection": name, "action": "create", "data": {"nope": 1}}),
        ("describe_collection", {"collection": "mcptest_absent_zzzz"}),
    ]
    for tool, args in provocations:
        result = await live_client.call_tool(tool, args, raise_on_error=False)
        payload = err_payload(result)
        assert_no_traceback(serialize(payload))
        assert_no_traceback(str(payload.get("message", "")))
