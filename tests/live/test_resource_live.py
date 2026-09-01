"""Section 11 — live enhancement verification: the pocketbase://schema resource."""

from __future__ import annotations

import json

import pytest

from .helpers import ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [{"name": "title", "type": "text", "required": True}]


async def _resource_names(live_client) -> set[str]:
    contents = await live_client.read_resource("pocketbase://schema")
    payload = json.loads(contents[0].text)
    assert payload["ok"] is True, payload
    return {c["name"] for c in payload["data"]}


async def test_resource_matches_describe_schema(live_client) -> None:
    """11.1 — pocketbase://schema and describe_schema report the same collection names."""
    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    tool_names = {c["name"] for c in schema["collections"]}
    assert await _resource_names(live_client) == tool_names


async def test_resource_reflects_create_and_destroy(live_client) -> None:
    """11.2 — a created collection appears in the resource; a destroyed one disappears."""
    name = "mcptest_resource_000001"
    ok_data(
        await live_client.call_tool(
            "manage_collection", {"action": "create", "name": name, "fields": _FIELDS}
        )
    )
    try:
        assert name in await _resource_names(live_client)
    finally:
        ok_data(
            await live_client.call_tool(
                "destroy_collection",
                {"action": "delete", "name": name, "confirm_name": name},
            )
        )
    assert name not in await _resource_names(live_client)
