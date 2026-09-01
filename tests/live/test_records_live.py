"""Section 4 — live record operations: write_record, find_records, bulk_write."""

from __future__ import annotations

import pytest

from pocketbase_mcp.config import settings

from .helpers import err_payload, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [
    {"name": "title", "type": "text", "required": True},
    {"name": "score", "type": "number", "required": False},
    {"name": "tag", "type": "text", "required": False},
]


async def _seed(client, collection: str, rows: list[dict]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        data = ok_data(
            await client.call_tool(
                "write_record",
                {"collection": collection, "action": "create", "data": row},
            )
        )
        ids.append(data["id"])
    return ids


async def test_create_then_find_by_id(live_client, live_collection) -> None:
    """4.1 — a record written through write_record reads back with the written values."""
    name = await live_collection("rec", _FIELDS)
    created = ok_data(
        await live_client.call_tool(
            "write_record",
            {
                "collection": name,
                "action": "create",
                "data": {"title": "hello", "score": 7, "tag": "a"},
            },
        )
    )
    rid = created["id"]

    got = ok_data(await live_client.call_tool("find_records", {"collection": name, "record_id": rid}))
    assert got["title"] == "hello"
    assert got["score"] == 7
    assert got["tag"] == "a"


async def test_update_visible_on_next_read(live_client, live_collection) -> None:
    """4.2 — an update through write_record is visible on the following read."""
    name = await live_collection("rec", _FIELDS)
    rid = (await _seed(live_client, name, [{"title": "before", "tag": "x"}]))[0]

    ok_data(
        await live_client.call_tool(
            "write_record",
            {"collection": name, "action": "update", "record_id": rid, "data": {"title": "after"}},
        )
    )
    got = ok_data(await live_client.call_tool("find_records", {"collection": name, "record_id": rid}))
    assert got["title"] == "after"


async def test_parameterized_filter_returns_matching_subset(live_client, live_collection) -> None:
    """4.3 — a bound filter returns exactly the matching records."""
    name = await live_collection("rec", _FIELDS)
    await _seed(
        live_client,
        name,
        [
            {"title": "a", "tag": "keep"},
            {"title": "b", "tag": "keep"},
            {"title": "c", "tag": "drop"},
        ],
    )

    got = ok_data(
        await live_client.call_tool(
            "find_records",
            {
                "collection": name,
                "filter_template": "tag = {:t}",
                "filter_params": {"t": "keep"},
            },
        )
    )
    tags = [r["tag"] for r in got["records"]]
    assert tags == ["keep", "keep"]


async def test_apostrophe_value_binds_safely(live_client, live_collection) -> None:
    """4.4 — a value containing an apostrophe binds as a parameter with no filter-syntax error."""
    name = await live_collection("rec", _FIELDS)
    await _seed(
        live_client,
        name,
        [{"title": "it's alive", "tag": "q"}, {"title": "plain", "tag": "q"}],
    )

    result = await live_client.call_tool(
        "find_records",
        {
            "collection": name,
            "filter_template": "title = {:t}",
            "filter_params": {"t": "it's alive"},
        },
        raise_on_error=False,
    )
    got = ok_data(result)
    assert [r["title"] for r in got["records"]] == ["it's alive"]


async def test_fetch_all_crosses_page_boundaries(live_client, live_collection) -> None:
    """4.5 — fetch_all returns every record across more than one internal page (batch=200)."""
    name = await live_collection("rec", _FIELDS)
    total = 205
    rows = [{"title": f"r{i}", "tag": "bulk"} for i in range(total)]
    for start in range(0, total, settings.batch_limit):
        chunk = rows[start : start + settings.batch_limit]
        ok_data(
            await live_client.call_tool(
                "bulk_write",
                {
                    "operations": [
                        {"collection": name, "action": "create", "data": row} for row in chunk
                    ]
                },
            )
        )

    got = ok_data(
        await live_client.call_tool("find_records", {"collection": name, "fetch_all": True})
    )
    assert got["total"] == total


async def test_bulk_write_mixed_batch_reports_per_operation(live_client, live_collection) -> None:
    """4.6 — a mixed create/update batch reports a result per op in submission order."""
    name = await live_collection("rec", _FIELDS)
    existing = (await _seed(live_client, name, [{"title": "old", "tag": "m"}]))[0]

    batch = ok_data(
        await live_client.call_tool(
            "bulk_write",
            {
                "operations": [
                    {"collection": name, "action": "create", "data": {"title": "new", "tag": "m"}},
                    {
                        "collection": name,
                        "action": "update",
                        "record_id": existing,
                        "data": {"title": "changed"},
                    },
                ]
            },
        )
    )
    assert batch["count"] == 2
    assert len(batch["results"]) == 2

    after = ok_data(
        await live_client.call_tool(
            "find_records",
            {"collection": name, "filter_template": "tag = {:t}", "filter_params": {"t": "m"}},
        )
    )
    titles = {r["title"] for r in after["records"]}
    assert titles == {"new", "changed"}


async def test_bulk_write_unknown_field_creates_nothing(live_client, live_collection) -> None:
    """4.7 — a batch with an unknown field returns a structured error and writes nothing."""
    name = await live_collection("rec", _FIELDS)

    result = await live_client.call_tool(
        "bulk_write",
        {
            "operations": [
                {"collection": name, "action": "create", "data": {"title": "ok", "tag": "z"}},
                {"collection": name, "action": "create", "data": {"title": "bad", "nonesuch": 1}},
            ]
        },
        raise_on_error=False,
    )
    payload = err_payload(result)
    assert payload["error_type"] == "VALIDATION_ERROR"

    after = ok_data(await live_client.call_tool("find_records", {"collection": name, "fetch_all": True}))
    assert after["total"] == 0
