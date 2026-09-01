"""Tests for MCP prompts registration and content."""

from __future__ import annotations

import pytest


def _text(message) -> str:
    """Message.content is a TextContent object under fastmcp 3.x, not a bare str."""
    content = message.content
    return content if isinstance(content, str) else content.text


@pytest.mark.asyncio
async def test_all_prompt_names_registered():
    """inspect_then_query, safe_delete, create_with_validation appear in server prompts."""
    from pocketbase_mcp.server import build_mcp

    mcp = build_mcp()
    names = {p.name for p in await mcp.list_prompts()}

    assert "inspect_then_query" in names, f"Missing prompt; registered: {names}"
    assert "safe_delete" in names, f"Missing prompt; registered: {names}"
    assert "create_with_validation" in names, f"Missing prompt; registered: {names}"


@pytest.mark.asyncio
async def test_inspect_then_query_no_collection():
    """inspect_then_query with no collection returns generic schema-discovery messages."""
    from pocketbase_mcp.prompts import inspect_then_query

    messages = await inspect_then_query(collection=None)
    assert len(messages) >= 1
    content = _text(messages[0])
    assert "describe_schema" in content or "collections" in content.lower()


@pytest.mark.asyncio
async def test_inspect_then_query_with_collection():
    """inspect_then_query with collection names the collection in messages."""
    from pocketbase_mcp.prompts import inspect_then_query

    messages = await inspect_then_query(collection="posts")
    assert len(messages) >= 1
    content = _text(messages[0])
    assert "posts" in content


@pytest.mark.asyncio
async def test_safe_delete_references_confirm_count():
    """safe_delete prompt instructs agent to use confirm_count."""
    from pocketbase_mcp.prompts import safe_delete

    messages = await safe_delete(collection="posts", filter_description="old drafts")
    content = " ".join(_text(m) for m in messages)
    assert "confirm_count" in content
    assert "posts" in content


@pytest.mark.asyncio
async def test_create_with_validation_references_describe_collection():
    """create_with_validation prompt requires describe_collection first."""
    from pocketbase_mcp.prompts import create_with_validation

    messages = await create_with_validation(collection="articles")
    content = " ".join(_text(m) for m in messages)
    assert "describe_collection" in content
    assert "articles" in content
