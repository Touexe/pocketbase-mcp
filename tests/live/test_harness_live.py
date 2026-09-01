"""Task 2.8 — test the harness itself.

The prefix guard rejects a name it does not own, and two collections drawn from
the factory get distinct names and are both cleaned up.
"""

from __future__ import annotations

import pytest

from pocketbase_mcp.config import settings

from .helpers import MCPTEST_PREFIX, assert_test_owned, ok_data

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


def test_prefix_guard_rejects_foreign_name() -> None:
    with pytest.raises(RuntimeError):
        assert_test_owned("users")
    assert_test_owned(f"{MCPTEST_PREFIX}anything")  # does not raise


def test_destructive_tools_registered(live_state) -> None:
    assert settings.enable_destructive is True


async def test_two_runs_get_distinct_names(live_client, live_collection) -> None:
    fields = [{"name": "title", "type": "text", "required": True}]
    first = await live_collection("harness", fields)
    second = await live_collection("harness", fields)

    assert first != second
    assert first.startswith(MCPTEST_PREFIX) and second.startswith(MCPTEST_PREFIX)

    schema = ok_data(await live_client.call_tool("describe_schema", {"refresh": True}))
    names = {c["name"] for c in schema["collections"]}
    assert {first, second} <= names
    # teardown (factory finalizer) drops both — verified by the session-end sweep
    # assertion in task 12.6.
