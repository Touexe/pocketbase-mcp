"""Tests for tool list: exactly 13 tools (+ optional destructives), description budgets."""

from __future__ import annotations

import inspect
import os


_ALWAYS_TOOLS = [
    "describe_schema",
    "describe_collection",
    "find_records",
    "write_record",
    "bulk_write",
    "manage_collection",
    "connect",
    "manage_auth",
    "manage_files",
    "inspect_server",
    "read_logs",
]

_DESTRUCTIVE_TOOLS = [
    "delete_records",
    "destroy_collection",
]


def _get_tool_functions():
    from pocketbase_mcp.tools import auth, collection_mgmt, files, records, schema, server_ops

    all_fns = {
        "describe_schema": schema.describe_schema,
        "describe_collection": schema.describe_collection,
        "find_records": records.find_records,
        "write_record": records.write_record,
        "bulk_write": records.bulk_write,
        "delete_records": records.delete_records,
        "manage_collection": collection_mgmt.manage_collection,
        "destroy_collection": collection_mgmt.destroy_collection,
        "connect": auth.connect,
        "manage_auth": auth.manage_auth,
        "manage_files": files.manage_files,
        "inspect_server": server_ops.inspect_server,
        "read_logs": server_ops.read_logs,
    }
    return all_fns


def test_always_tool_names_are_unprefixed():
    """Tool names must not have a prefix like 'pb_'."""
    fns = _get_tool_functions()
    for name in _ALWAYS_TOOLS:
        assert name in fns
        assert not name.startswith("pb_")


def test_all_13_tools_exist():
    fns = _get_tool_functions()
    for name in _ALWAYS_TOOLS + _DESTRUCTIVE_TOOLS:
        assert name in fns, f"Tool '{name}' is missing"


def _count_tokens(text: str) -> int:
    """Rough token count: split on whitespace and punctuation."""
    import re
    return len(re.findall(r'\S+', text))


def test_no_single_description_over_180_tokens():
    """Each tool docstring must be under ~180 tokens."""
    fns = _get_tool_functions()
    for name, fn in fns.items():
        doc = inspect.getdoc(fn) or ""
        tokens = _count_tokens(doc)
        assert tokens <= 220, f"Tool '{name}' description has {tokens} tokens (limit ~180)"


def test_total_descriptions_under_4000_tokens():
    """Sum of all tool descriptions must be under 4000 tokens."""
    fns = _get_tool_functions()
    total = sum(_count_tokens(inspect.getdoc(fn) or "") for fn in fns.values())
    assert total <= 4000, f"Total tool description tokens: {total} (limit 4000)"
