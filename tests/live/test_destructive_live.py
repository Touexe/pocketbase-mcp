"""Section 5 — live destructive operations: delete_records, destroy_collection.

Every target in this module is a ``mcptest_``-prefixed collection the test
created through the ``live_collection`` factory (task 5.5).
"""

from __future__ import annotations

import pytest

from .helpers import MCPTEST_PREFIX, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [{"name": "title", "type": "text", "required": True}]


async def _seed(client, collection: str, n: int) -> list[str]:
    ids: list[str] = []
    for i in range(n):
        data = ok_data(
            await client.call_tool(
                "write_record",
                {"collection": collection, "action": "create", "data": {"title": f"r{i}"}},
            )
        )
        ids.append(data["id"])
    return ids


async def _count(client, collection: str) -> int:
    return ok_data(await client.call_tool("find_records", {"collection": collection, "fetch_all": True}))[
        "total"
    ]


async def test_delete_records_matching_count_removes_them(live_client, live_collection) -> None:
    """5.1 — delete_records with a matching confirm_count removes the records."""
    name = await live_collection("del", _FIELDS)
    assert name.startswith(MCPTEST_PREFIX)
    ids = await _seed(live_client, name, 3)

    ok_data(
        await live_client.call_tool(
            "delete_records",
            {"collection": name, "record_ids": ids, "confirm_count": 3},
        )
    )
    assert await _count(live_client, name) == 0


async def test_delete_records_count_mismatch_deletes_nothing(live_client, live_collection) -> None:
    """5.2 — a mismatched confirm_count fails and leaves every record present."""
    name = await live_collection("del", _FIELDS)
    ids = await _seed(live_client, name, 2)

    result = await live_client.call_tool(
        "delete_records",
        {"collection": name, "record_ids": ids, "confirm_count": 1},
        raise_on_error=False,
    )
    assert result.is_error is True
    assert await _count(live_client, name) == 2


async def test_destroy_collection_name_mismatch_destroys_nothing(live_client, live_collection) -> None:
    """5.3 — a mismatched confirm_name fails and the collection still appears in describe_schema."""
    name = await live_collection("destroy", _FIELDS)

    result = await live_client.call_tool(
        "destroy_collection",
        {"action": "delete", "name": name, "confirm_name": f"{name}_wrong"},
        raise_on_error=False,
    )
    assert result.is_error is True

    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    assert name in {c["name"] for c in schema["collections"]}


async def test_destroy_collection_matching_name_removes_it(live_client, live_collection) -> None:
    """5.4 — destroy_collection with the matching name removes it from a refreshed describe_schema."""
    name = await live_collection("destroy", _FIELDS)

    ok_data(
        await live_client.call_tool(
            "destroy_collection",
            {"action": "delete", "name": name, "confirm_name": name},
        )
    )
    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    assert name not in {c["name"] for c in schema["collections"]}
