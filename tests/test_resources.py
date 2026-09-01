"""Tests for schema resource."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from result import Err, Ok


def _make_collection(name: str, cid: str, fields=None):
    c = MagicMock()
    c.name = name
    c.id = cid
    c.type = "base"
    c.fields = fields or []
    return c


def _make_ctx(schema_cache):
    state = MagicMock()
    state.schema_cache = schema_cache
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"pb": state}
    return ctx


@pytest.mark.asyncio
async def test_schema_resource_returns_collection_list():
    """Resource returns ok=True with collection summary matching the cache."""
    col_a = _make_collection("posts", "id_a", fields=[MagicMock(), MagicMock()])
    col_b = _make_collection("users", "id_b", fields=[MagicMock()])

    cache = MagicMock()
    cache.all_collections = AsyncMock(return_value=Ok([col_a, col_b]))

    ctx = _make_ctx(cache)

    from pocketbase_mcp.resources import schema_resource

    raw = await schema_resource(ctx)
    payload = json.loads(raw)

    assert payload["ok"] is True
    names = {c["name"] for c in payload["data"]}
    assert names == {"posts", "users"}
    posts_entry = next(c for c in payload["data"] if c["name"] == "posts")
    assert posts_entry["field_count"] == 2


@pytest.mark.asyncio
async def test_schema_resource_returns_error_on_load_failure():
    """Resource returns ok=False with hint when cache load fails — not an empty list."""
    cache = MagicMock()
    cache.all_collections = AsyncMock(return_value=Err("connection refused"))

    ctx = _make_ctx(cache)

    from pocketbase_mcp.resources import schema_resource

    raw = await schema_resource(ctx)
    payload = json.loads(raw)

    assert payload["ok"] is False
    assert payload["error_type"] == "SCHEMA_LOAD_ERROR"
    assert "connection refused" in payload["message"]
    assert "hint" in payload
    # Must NOT be an empty list
    assert "data" not in payload or payload.get("data") is None
