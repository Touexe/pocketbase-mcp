"""Section 6 — live collection management: manage_collection create/update + failure branches."""

from __future__ import annotations

import pytest

from .helpers import err_payload, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [{"name": "title", "type": "text", "required": True}]


async def test_update_adds_a_field(live_client, live_collection) -> None:
    """6.1 — manage_collection(action='update') adds a field; describe_collection reports it."""
    name = await live_collection("mgmt", _FIELDS)

    detail = ok_data(await live_client.call_tool("describe_collection", {"collection": name}))
    kept = [
        {"name": f["name"], "type": f["type"], "required": f["required"]}
        for f in detail["fields"]
        if f["name"] not in {"id"}
    ]
    kept.append({"name": "added", "type": "number", "required": False})

    ok_data(
        await live_client.call_tool(
            "manage_collection",
            {"action": "update", "name": name, "fields": kept},
        )
    )
    after = ok_data(await live_client.call_tool("describe_collection", {"collection": name}))
    assert "added" in {f["name"] for f in after["fields"]}


async def test_invalid_view_query_rejected_before_creation(live_client) -> None:
    """6.2 — a view collection with an unexecutable query returns the query's error, creates nothing."""
    name = "mcptest_badview_000001"
    result = await live_client.call_tool(
        "manage_collection",
        {
            "action": "create",
            "name": name,
            "collection_type": "view",
            "view_query": "SELECT this is not valid sql at all",
        },
        raise_on_error=False,
    )
    payload = err_payload(result)
    assert payload["error_type"] == "VIEW_QUERY_INVALID"

    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    assert name not in {c["name"] for c in schema["collections"]}


async def test_unknown_relation_target_rejected(live_client) -> None:
    """6.3 — a relation field pointing at a nonexistent collection returns a structured error."""
    name = "mcptest_badrel_000001"
    result = await live_client.call_tool(
        "manage_collection",
        {
            "action": "create",
            "name": name,
            "fields": [
                {"name": "title", "type": "text", "required": True},
                {"name": "ref", "type": "relation", "collectionId": "no_such_collection_zzzz"},
            ],
        },
        raise_on_error=False,
    )
    payload = err_payload(result)
    assert payload["error_type"] in {"UNKNOWN_RELATION_TARGET", "COLLECTION_NOT_CREATED"}

    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    assert name not in {c["name"] for c in schema["collections"]}
