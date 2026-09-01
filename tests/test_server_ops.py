"""Tests for server operation tools."""

from __future__ import annotations

import inspect

from pocketbase_mcp.tools import server_ops


def test_inspect_server_has_no_log_entries():
    """inspect_server should return aggregate stats only, not log entry lists."""
    src = inspect.getsource(server_ops.inspect_server)
    # Must not call logs.list — that's what read_logs does
    assert "logs.list" not in src
    assert "logs.get_one" not in src


def test_no_forbidden_tools_exist():
    """No tools for settings mutation, S3/email tests, Apple secret, cron triggering, or backups."""
    import pocketbase_mcp.tools.server_ops as sops

    # Enumerate all callables in server_ops
    tool_names = [
        name for name, obj in inspect.getmembers(sops, inspect.isfunction)
        if not name.startswith("_")
    ]

    forbidden = {"settings_update", "test_s3", "test_email", "generate_apple_client_secret", "run_cron", "backup"}
    for name in tool_names:
        assert name not in forbidden, f"Forbidden tool found: {name}"
