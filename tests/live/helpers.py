"""Shared assertions for the live suite.

Every live test asserts on the agent-visible envelope a tool returns —
``ok`` / ``error_type`` / ``message`` / ``hint`` / payload — and never on
calls made to the underlying ``pypocketbase`` client (design D5).
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp.client.client import CallToolResult

MCPTEST_PREFIX = "mcptest_"


def assert_test_owned(name: str) -> None:
    """Raise unless ``name`` carries the ``mcptest_`` prefix (teardown safety rail, D2)."""
    if not name.startswith(MCPTEST_PREFIX):
        raise RuntimeError(
            f"live teardown refused: {name!r} does not carry the {MCPTEST_PREFIX!r} prefix; "
            "no live test may name a collection it did not create"
        )


_TRACEBACK_MARKERS = (
    "Traceback (most recent call last)",
    'File "',
    ".py\", line ",
    "PocketbaseException",
    "aiohttp.client_exceptions",
)


def ok_data(result: CallToolResult) -> Any:
    """Assert a success envelope and return its ``data`` payload."""
    assert not result.is_error, _text(result)
    payload = result.data
    assert isinstance(payload, dict), f"expected a dict envelope, got {payload!r}"
    assert payload.get("ok") is True, f"expected ok=True, got {payload!r}"
    return payload["data"]


def err_payload(result: CallToolResult) -> dict[str, Any]:
    """Return a structured-error envelope.

    Handles both shapes: a returned ``{"ok": False, ...}`` dict, and a raised
    ``ToolError`` (the two destructive-confirmation guards), which arrives as an
    error result with only text content.
    """
    payload = result.data
    if payload is None:
        return {
            "ok": False,
            "error_type": None,
            "message": _text(result),
            "hint": None,
            "status": None,
        }
    assert isinstance(payload, dict), f"expected a dict envelope, got {payload!r}"
    assert payload.get("ok") is False, f"expected ok=False, got {payload!r}"
    return payload


def serialize(obj: Any) -> str:
    """Deterministic string form of any envelope, for secret-leak scans."""
    return json.dumps(obj, default=str, sort_keys=True)


def assert_no_traceback(text: str) -> None:
    """Fail if an error message carries a stack trace or an exception class name."""
    for marker in _TRACEBACK_MARKERS:
        assert marker not in text, f"error message leaked internal detail {marker!r}: {text!r}"


def _text(result: CallToolResult) -> str:
    if result.content:
        return " ".join(getattr(c, "text", str(c)) for c in result.content)
    return repr(result.data)
