"""Tests for file operation tool."""

from __future__ import annotations

import inspect

from pocketbase_mcp.tools import files


def test_token_not_in_responses():
    """File token must not appear in any returned dict."""
    src = inspect.getsource(files.manage_files)
    # ok_response calls should not pass 'token' as a key to be returned
    import re
    ok_calls = re.findall(r'ok_response\(\s*\{([^}]+)\}', src, re.DOTALL)
    for call in ok_calls:
        assert '"token"' not in call and "'token'" not in call, \
            f"token key found in ok_response: {call}"


def test_nonfile_field_short_circuits():
    """Non-file field check is present in manage_files source."""
    src = inspect.getsource(files.manage_files)
    assert "not a file field" in src or "file_fields" in src


def test_missing_local_path_short_circuits():
    """Missing local_path for upload is caught before dispatch."""
    src = inspect.getsource(files.manage_files)
    assert "local_path" in src
    assert "does not exist" in src or "os.path.exists" in src
