"""Tests for the agent error contract."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pocketbase.utils.errors import ErrorType

from pocketbase_mcp.errors import ok_response, to_agent_error


def _make_exc(error_type: ErrorType, message: str = "test error") -> MagicMock:
    exc = MagicMock()
    exc.type = error_type
    exc.original_message = message
    exc.response = MagicMock()
    exc.response.code = 400
    return exc


def test_every_error_type_has_nonempty_hint():
    """Every ErrorType maps to a non-empty hint — no silent gaps."""
    for et in ErrorType:
        exc = _make_exc(et)
        result = to_agent_error(exc)
        assert result["hint"], f"Empty hint for {et.name}"
        assert result["ok"] is False
        assert result["error_type"] == et.name


def test_error_response_structure():
    exc = _make_exc(ErrorType.RECORD_NOT_FOUND, "not found")
    result = to_agent_error(exc)
    assert result["ok"] is False
    assert result["message"] == "not found"
    assert result["status"] == 400
    assert "find_records" in result["hint"]


def test_ok_response_structure():
    result = ok_response({"id": "abc"}, hint="use find_records next")
    assert result["ok"] is True
    assert result["data"] == {"id": "abc"}
    assert result["hint"] == "use find_records next"


def test_ok_response_no_hint():
    result = ok_response({"id": "abc"})
    assert "hint" not in result
