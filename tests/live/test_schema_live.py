"""Section 3 — live schema discovery: describe_schema, describe_collection."""

from __future__ import annotations

import pytest

from .helpers import err_payload, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [
    {"name": "title", "type": "text", "required": True},
    {"name": "score", "type": "number", "required": False},
    {"name": "note", "type": "text", "required": False},
]


async def test_created_collection_appears_in_schema(live_client, live_collection) -> None:
    """3.1 — a freshly created collection shows up in describe_schema(refresh=True)."""
    name = await live_collection("schema", _FIELDS)

    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    entry = next((c for c in schema["collections"] if c["name"] == name), None)
    assert entry is not None, f"{name} missing from {[c['name'] for c in schema['collections']]}"

    detail = ok_data(await live_client.call_tool("describe_collection", {"collection": name}))
    assert entry["field_count"] == len(detail["fields"])
    assert entry["field_count"] >= len(_FIELDS)


async def test_describe_collection_round_trips_field_detail(live_client, live_collection) -> None:
    """3.2 — every declared field is reported with its type and required flag."""
    name = await live_collection("schema", _FIELDS)

    detail = ok_data(await live_client.call_tool("describe_collection", {"collection": name}))
    by_name = {f["name"]: f for f in detail["fields"]}

    for declared in _FIELDS:
        got = by_name.get(declared["name"])
        assert got is not None, f"{declared['name']} not reported"
        assert got["type"] == declared["type"]
        assert got["required"] == declared["required"]


async def test_describe_collection_unknown_name_is_structured_error(live_client) -> None:
    """3.3 — an absent name returns a structured error whose hint names describe_schema."""
    result = await live_client.call_tool(
        "describe_collection",
        {"collection": "mcptest_definitely_absent_zzzz"},
        raise_on_error=False,
    )
    payload = err_payload(result)
    assert payload["error_type"] == "COLLECTION_NOT_FOUND"
    assert "describe_schema" in payload["hint"]
