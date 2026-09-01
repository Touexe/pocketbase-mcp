"""Live integration test harness.

These fixtures drive the in-memory FastMCP ``Client`` against a REAL PocketBase
server (design D1). Every collection the suite touches is one it created itself,
named with the ``mcptest_`` prefix (D2). Teardown refuses to delete any other
name — that rule is what keeps a mis-pointed ``POCKETBASE_URL`` from destroying
real data. Credentials come only from ``POCKETBASE_ADMIN_EMAIL`` /
``POCKETBASE_ADMIN_PASSWORD`` (D8); no credential value lives in this repo.

Resolution of the design.md open questions:

* **Session-end sweep is always on** — there is no ``--no-live-sweep`` opt-out.
  A run that crashes before teardown leaves ``mcptest_*`` collections behind;
  the next session sweeps them at both start and end, so a fresh run is always
  clean. Debugging leftover state is done by rerunning a single test, not by
  keeping wreckage around.
* **``manage_files`` upload uses a generated temp file**, not a committed binary
  asset. Thumbnail coverage is not exercised, so no real image is required
  (see ``test_files_live.py``).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from secrets import token_hex
from socket import create_connection
from typing import Any
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from fastmcp import Client
from pocketbase import Client as PocketBaseClient
from result import Err

from pocketbase_mcp.config import settings
from pocketbase_mcp.domain.schema import SchemaCache
from pocketbase_mcp.server import ServerState, build_mcp

from .helpers import MCPTEST_PREFIX, assert_test_owned

CollectionFactory = Callable[..., Awaitable[str]]


# --------------------------------------------------------------------------- #
# Collection-time skip guard (tasks 1.4 / 1.5, spec: "skips cleanly")         #
# --------------------------------------------------------------------------- #
def _precondition_failure() -> str | None:
    """Return a stated skip reason, or ``None`` when the live suite may run."""
    if not settings.admin_email:
        return "POCKETBASE_ADMIN_EMAIL is not set"
    if not settings.admin_password:
        return "POCKETBASE_ADMIN_PASSWORD is not set"

    parsed = urlparse(settings.url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with create_connection((host, port), timeout=2):
            pass
    except OSError:
        return f"PocketBase not reachable at {settings.url}"
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark every ``tests/live/`` item ``live`` and skip the lot when a
    precondition is missing — before ``-m`` selection runs."""
    reason = _precondition_failure()
    skip_marker = pytest.mark.skip(reason=f"live suite precondition: {reason}") if reason else None
    for item in items:
        path = str(getattr(item, "fspath", "")).replace("\\", "/")
        if "/tests/live/" not in path:
            continue
        item.add_marker(pytest.mark.live)
        if skip_marker is not None:
            item.add_marker(skip_marker)


# --------------------------------------------------------------------------- #
# Teardown safety rail (task 2.5, spec: "refuses to delete what it does not   #
# own") — `assert_test_owned` lives in helpers.py so test modules share it.   #
# --------------------------------------------------------------------------- #
async def _drop_collection(pb: PocketBaseClient, name: str) -> None:
    assert_test_owned(name)
    await pb.collections.delete(name)  # not-found is a harmless no-op on teardown


async def _sweep(pb: PocketBaseClient) -> None:
    """Delete every remaining ``mcptest_*`` collection and touch nothing else."""
    result = await pb.collections.get_full_list()
    if isinstance(result, Err):
        return
    for collection in result.ok_value:
        if collection.name.startswith(MCPTEST_PREFIX):
            await pb.collections.delete(collection.name)


# --------------------------------------------------------------------------- #
# Session harness (tasks 2.1 / 2.2 / 2.3)                                     #
# --------------------------------------------------------------------------- #
@dataclass
class LiveHarness:
    client: Client
    state: ServerState
    pb: PocketBaseClient


@pytest.fixture(scope="session")
def _session_monkeypatch() -> Generator[Any, None, None]:
    """A session-scoped monkeypatch (the built-in one is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="session")
def _destructive_enabled(_session_monkeypatch) -> None:
    """Register ``delete_records`` / ``destroy_collection`` for the live run (D3)."""
    _session_monkeypatch.setattr(settings, "enable_destructive", True)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _harness(_destructive_enabled) -> AsyncGenerator[LiveHarness, None]:
    pb = PocketBaseClient(url=settings.url)
    await pb.__aenter__()
    cache = SchemaCache(pb)
    state = ServerState(pb=pb, schema_cache=cache)

    @asynccontextmanager
    async def _lifespan(_server: Any):
        yield {"pb": state}

    mcp = build_mcp(lifespan=_lifespan)
    try:
        async with Client(mcp) as client:
            # D8: authenticate the session by dogfooding the connect tool.
            auth = await client.call_tool(
                "connect",
                {
                    "as_": "superuser",
                    "email": settings.admin_email,
                    "password": settings.admin_password,
                },
                raise_on_error=False,
            )
            if auth.is_error or not (auth.data or {}).get("ok"):
                detail = auth.data
                if detail is None and auth.content:
                    detail = getattr(auth.content[0], "text", auth.content[0])
                pytest.fail(f"live session auth via connect failed: {detail}")
            cache.invalidate()
            await _sweep(pb)  # clear a previous crashed run's leftovers
            try:
                yield LiveHarness(client=client, state=state, pb=pb)
            finally:
                await _sweep(pb)
    finally:
        await pb.__aexit__(None, None, None)


@pytest_asyncio.fixture(loop_scope="session")
async def live_client(_harness: LiveHarness) -> Client:
    """The connected, superuser FastMCP client every live test calls tools through."""
    return _harness.client


@pytest_asyncio.fixture(loop_scope="session")
async def live_state(_harness: LiveHarness) -> ServerState:
    """The live ``ServerState`` — for identity assertions only, never for spying on ``pb``."""
    return _harness.state


@pytest_asyncio.fixture(loop_scope="session")
async def anon_client(_harness: LiveHarness) -> AsyncGenerator[Client, None]:
    """A second FastMCP client bound to a fresh, unauthenticated ``ServerState``."""
    pb = PocketBaseClient(url=settings.url)
    await pb.__aenter__()
    state = ServerState(pb=pb, schema_cache=SchemaCache(pb))

    @asynccontextmanager
    async def _lifespan(_server: Any):
        yield {"pb": state}

    try:
        async with Client(build_mcp(lifespan=_lifespan)) as client:
            yield client
    finally:
        await pb.__aexit__(None, None, None)


# --------------------------------------------------------------------------- #
# Ephemeral collection factory (task 2.4, spec: "ephemeral and namespaced")   #
# --------------------------------------------------------------------------- #
@pytest_asyncio.fixture(loop_scope="session")
async def live_collection(_harness: LiveHarness) -> AsyncGenerator[CollectionFactory, None]:
    """Create ``mcptest_<area>_<hex8>`` collections and drop them on teardown,
    even when the requesting test fails."""
    created: list[str] = []

    async def _make(
        area: str,
        fields: list[dict[str, Any]],
        *,
        collection_type: str = "base",
        **extra: Any,
    ) -> str:
        name = f"{MCPTEST_PREFIX}{area}_{token_hex(4)}"
        body: dict[str, Any] = {
            "name": name,
            "type": collection_type,
            "fields": list(fields),
            **extra,
        }
        result = await _harness.pb.collections.create(body)
        if isinstance(result, Err):
            pytest.fail(f"could not create {name}: {result.err_value.original_message}")
        created.append(name)
        _harness.state.schema_cache.invalidate()
        return name

    yield _make

    for name in reversed(created):
        await _drop_collection(_harness.pb, name)
    _harness.state.schema_cache.invalidate()


# --------------------------------------------------------------------------- #
# Progress handler recorder (task 2.7)                                        #
# --------------------------------------------------------------------------- #
@pytest.fixture
def progress_capture() -> tuple[list[dict[str, Any]], Callable[..., Awaitable[None]]]:
    """``(events, handler)`` — pass ``handler`` to ``call_tool(progress_handler=...)``
    and read the recorded events afterwards."""
    events: list[dict[str, Any]] = []

    async def handler(progress: float, total: float | None, message: str | None) -> None:
        events.append({"progress": progress, "total": total, "message": message})

    return events, handler
