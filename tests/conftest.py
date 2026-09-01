"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client
from result import Ok

from pocketbase_mcp.domain.schema import SchemaCache
from pocketbase_mcp.server import ServerState, build_mcp


@pytest.fixture
def mock_pb_client() -> MagicMock:
    """A MagicMock that stands in for the pypocketbase Client."""
    client = MagicMock()
    client.filter = MagicMock(side_effect=lambda tmpl, **kw: tmpl)  # passthrough by default
    return client


@pytest.fixture
def server_state(mock_pb_client: MagicMock) -> ServerState:
    schema_cache = MagicMock(spec=SchemaCache)
    schema_cache.get_fields = AsyncMock(return_value=Ok([]))
    return ServerState(
        pb=mock_pb_client,
        schema_cache=schema_cache,
        identity="anonymous",
        startup_auth_error=None,
    )


@pytest.fixture
async def mcp_client(server_state: ServerState) -> AsyncGenerator[Client, None]:
    """In-memory FastMCP client connected to the server under test.

    fastmcp 3.x dropped ``Client(mcp, context=...)``; the lifespan context is
    now injected only via a ``lifespan`` passed to ``build_mcp`` at construction.
    """

    @asynccontextmanager
    async def _test_lifespan(_server: Any) -> AsyncGenerator[dict[str, ServerState], None]:
        yield {"pb": server_state}

    mcp = build_mcp(lifespan=_test_lifespan)

    async with Client(mcp) as client:
        yield client
