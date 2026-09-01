"""Section 11 — live enhancement verification: progress events from find_records and bulk_write."""

from __future__ import annotations

import pytest

from pocketbase_mcp.config import settings

from .helpers import err_payload, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [{"name": "title", "type": "text", "required": True}]


async def _bulk_create(live_client, collection: str, n: int) -> None:
    rows = [{"collection": collection, "action": "create", "data": {"title": f"r{i}"}} for i in range(n)]
    for start in range(0, n, settings.batch_limit):
        ok_data(
            await live_client.call_tool(
                "bulk_write", {"operations": rows[start : start + settings.batch_limit]}
            )
        )


async def test_multi_page_fetch_all_emits_progress(live_client, live_collection, progress_capture) -> None:
    """11.3 — a genuinely multi-page fetch_all emits at least one progress event and
    returns every seeded record."""
    events, handler = progress_capture
    name = await live_collection("prog", _FIELDS)
    total = 205  # internal batch size is 200 -> two pages
    await _bulk_create(live_client, name, total)

    data = ok_data(
        await live_client.call_tool(
            "find_records", {"collection": name, "fetch_all": True}, progress_handler=handler
        )
    )
    assert data["total"] == total
    assert len(events) >= 1


async def test_single_page_fetch_all_emits_no_progress(
    live_client, live_collection, progress_capture
) -> None:
    """11.4 — a single-page fetch_all emits no progress event."""
    events, handler = progress_capture
    name = await live_collection("prog", _FIELDS)
    await _bulk_create(live_client, name, 5)

    ok_data(
        await live_client.call_tool(
            "find_records", {"collection": name, "fetch_all": True}, progress_handler=handler
        )
    )
    assert events == []


async def test_bulk_write_progress_matches_operation_count(
    live_client, live_collection, progress_capture
) -> None:
    """11.5 — a successful bulk_write emits a progress event whose completed count equals
    the operation count; a validation-failed one emits none."""
    events, handler = progress_capture
    name = await live_collection("prog", _FIELDS)

    ops = [{"collection": name, "action": "create", "data": {"title": f"r{i}"}} for i in range(4)]
    ok_data(await live_client.call_tool("bulk_write", {"operations": ops}, progress_handler=handler))
    assert len(events) >= 1
    assert events[-1]["progress"] == len(ops)

    events.clear()
    bad = await live_client.call_tool(
        "bulk_write",
        {"operations": [{"collection": name, "action": "create", "data": {"ghost": 1}}]},
        progress_handler=handler,
        raise_on_error=False,
    )
    assert err_payload(bad)["error_type"] == "VALIDATION_ERROR"
    assert events == []

    after = ok_data(await live_client.call_tool("find_records", {"collection": name, "fetch_all": True}))
    assert after["total"] == 4  # the failed batch created nothing
