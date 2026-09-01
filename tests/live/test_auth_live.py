"""Section 7 — live auth operations: connect, manage_auth. No response leaks a secret."""

from __future__ import annotations

import pytest

from pocketbase_mcp.config import settings

from .helpers import err_payload, ok_data, serialize

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


async def test_connect_superuser_reports_identity(live_client) -> None:
    """7.1 — connect as superuser reports the identity in effect."""
    data = ok_data(
        await live_client.call_tool(
            "connect",
            {"as_": "superuser", "email": settings.admin_email, "password": settings.admin_password},
        )
    )
    assert data["identity"] == f"superuser:{settings.admin_email}"

    status = ok_data(await live_client.call_tool("connect", {"as_": "status"}))
    assert status["identity"] == f"superuser:{settings.admin_email}"


async def test_connect_response_carries_no_secret(live_client) -> None:
    """7.2 — the serialized connect response contains neither the password nor a token."""
    result = await live_client.call_tool(
        "connect",
        {"as_": "superuser", "email": settings.admin_email, "password": settings.admin_password},
    )
    blob = serialize(result.data)
    assert settings.admin_password not in blob
    assert "token" not in blob.lower()


async def test_failed_connect_leaves_identity_untouched(live_client) -> None:
    """7.3 — a failed connect does not change the identity already in effect."""
    before = ok_data(await live_client.call_tool("connect", {"as_": "status"}))["identity"]

    failed = await live_client.call_tool(
        "connect",
        {"as_": "superuser", "email": "nobody@example.invalid", "password": "wrong-password"},
        raise_on_error=False,
    )
    assert err_payload(failed)["ok"] is False

    after = ok_data(await live_client.call_tool("connect", {"as_": "status"}))["identity"]
    assert after == before


async def test_manage_auth_missing_argument_is_structured_error(live_client) -> None:
    """7.4 — manage_auth with a missing required argument lists that action's requirements,
    before any request reaches the server."""
    result = await live_client.call_tool(
        "manage_auth",
        {"action": "confirm_password_reset", "collection": "users"},
        raise_on_error=False,
    )
    payload = err_payload(result)
    assert payload["error_type"] == "MISSING_ARGS"
    for arg in ("token", "password", "password_confirm"):
        assert arg in payload["message"]


async def test_manage_auth_response_has_no_token(live_client) -> None:
    """7.5 — no manage_auth response contains a token or confirmation code."""
    result = await live_client.call_tool(
        "manage_auth",
        {"action": "confirm_verification", "collection": "users"},
        raise_on_error=False,
    )
    blob = serialize(result.data)
    # A MISSING_ARGS message may *name* the `token` parameter (see 7.4); what must
    # never appear is a token *value* — a token field carrying data or a ?token= URL.
    assert '"token":' not in blob
    assert "token=" not in blob
    assert "confirmcode" not in blob.lower().replace("_", "").replace(" ", "")
