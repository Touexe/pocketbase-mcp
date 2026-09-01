"""Section 9 — live server operations: inspect_server, read_logs."""

from __future__ import annotations

import pytest

from pocketbase_mcp.config import settings

from .helpers import err_payload, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


async def test_inspect_server_reports_sections_and_no_log_entries(live_client) -> None:
    """9.1 — inspect_server as superuser returns health plus each section present or
    marked unavailable with a reason, and carries no individual log entries."""
    data = ok_data(await live_client.call_tool("inspect_server", {}))

    assert "health" in data
    for section in ("settings", "crons", "log_stats"):
        assert section in data, f"{section} missing from {sorted(data)}"
        value = data[section]
        if isinstance(value, dict) and "unavailable" in value:
            assert value["unavailable"], f"{section} unavailable with no reason"

    assert "items" not in data
    assert "logs" not in data


async def test_read_logs_clamps_page_size(live_client) -> None:
    """9.2 — read_logs above the configured max returns entries and states the clamp applied."""
    data = ok_data(
        await live_client.call_tool("read_logs", {"per_page": settings.log_page_size_max + 5000})
    )
    assert data["clamped"] is True
    assert data["per_page"] == settings.log_page_size_max
    assert isinstance(data["items"], list)


async def test_read_logs_from_anonymous_state_is_structured_error(anon_client) -> None:
    """9.3 — read_logs from a non-superuser state returns a structured error whose hint names connect."""
    result = await anon_client.call_tool("read_logs", {}, raise_on_error=False)
    payload = err_payload(result)
    assert payload["error_type"] == "UNAUTHORIZED_ERROR"
    assert "connect" in payload["hint"]
