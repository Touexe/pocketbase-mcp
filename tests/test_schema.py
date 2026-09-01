"""Tests for SchemaCache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from result import Err, Ok

from pocketbase_mcp.domain.schema import SchemaCache, validate_payload


def _make_collection(name: str, fields: list = []) -> MagicMock:
    col = MagicMock()
    col.name = name
    col.id = f"id_{name}"
    col.type = "base"
    col.fields = fields
    return col


@pytest.mark.asyncio
async def test_cache_loads_once():
    """Lazy population happens exactly once per session."""
    pb = MagicMock()
    col = _make_collection("posts")
    pb.collections.get_full_list = AsyncMock(return_value=Ok([col]))

    cache = SchemaCache(pb)
    await cache.all_collections()
    await cache.all_collections()

    pb.collections.get_full_list.assert_called_once()


@pytest.mark.asyncio
async def test_cache_load_failure_surfaces_as_error():
    """A failed load returns Err with a message, not an empty cache."""
    pb = MagicMock()
    err_exc = MagicMock()
    err_exc.original_message = "unauthorized"
    pb.collections.get_full_list = AsyncMock(return_value=Err(err_exc))

    cache = SchemaCache(pb)
    result = await cache.all_collections()

    assert isinstance(result, Err)
    assert "unauthorized" in result.err_value


@pytest.mark.asyncio
async def test_invalidate_forces_reload():
    pb = MagicMock()
    col = _make_collection("posts")
    pb.collections.get_full_list = AsyncMock(return_value=Ok([col]))

    cache = SchemaCache(pb)
    await cache.all_collections()
    cache.invalidate()
    await cache.all_collections()

    assert pb.collections.get_full_list.call_count == 2


def _make_field(name: str, required: bool = False, system: bool = False) -> MagicMock:
    f = MagicMock()
    f.name = name
    f.required = required
    f.system = system
    return f


def test_validate_unknown_field():
    fields = [_make_field("title"), _make_field("body")]
    errors = validate_payload(fields, {"title": "hi", "ghost": "foo"}, "create")
    assert any("ghost" in e for e in errors)


def test_validate_missing_required_on_create():
    fields = [_make_field("title", required=True), _make_field("body")]
    errors = validate_payload(fields, {"body": "hello"}, "create")
    assert any("title" in e for e in errors)


def test_validate_update_skips_required_check():
    fields = [_make_field("title", required=True)]
    errors = validate_payload(fields, {}, "update")
    assert not errors


def test_validate_ok():
    fields = [_make_field("title", required=True)]
    errors = validate_payload(fields, {"title": "hi"}, "create")
    assert not errors
