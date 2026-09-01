"""Tests for auth tools: no sensitive data in responses."""

from __future__ import annotations

import re


def test_connect_source_has_no_token_in_response():
    """connect tool must not expose password or auth token in its return value."""
    import inspect
    from pocketbase_mcp.tools import auth

    src = inspect.getsource(auth.connect)
    # The response dicts returned by ok_response must not include "token" or "password" keys
    # We verify this by checking that the ok_response calls don't pass token/password
    ok_calls = re.findall(r'ok_response\(([^)]+)\)', src, re.DOTALL)
    for call in ok_calls:
        assert "password" not in call, f"password found in ok_response call: {call}"
        # token might appear in a key name for _strip_sensitive; fine as a variable name used internally
        # but should not appear as a key in the returned dict
        assert '"token"' not in call and "'token'" not in call, f"token found in ok_response call: {call}"


def test_manage_auth_source_no_token_in_response():
    """manage_auth must not return passwords or tokens."""
    import inspect
    from pocketbase_mcp.tools import auth

    src = inspect.getsource(auth.manage_auth)
    ok_calls = re.findall(r'ok_response\(([^)]+)\)', src, re.DOTALL)
    for call in ok_calls:
        assert "password" not in call
        assert '"token"' not in call and "'token'" not in call
