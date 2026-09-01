"""Auth tools: connect, manage_auth."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from result import Err

from ..errors import ok_response, to_agent_error
from ..server import ServerState

_SENTINEL_FIELDS = {"password", "token", "confirmToken", "confirm_token"}


def _strip_sensitive(d: dict[str, Any]) -> dict[str, Any]:
    """Remove password/token fields from a dict before returning to the agent."""
    return {k: v for k, v in d.items() if k.lower() not in _SENTINEL_FIELDS}


async def connect(
    ctx: Context,
    as_: Annotated[
        Literal["superuser", "user", "impersonate", "status"],
        "superuser: authenticate with admin creds; user: authenticate as a collection record; impersonate: assume another user's identity (superuser required); status: report current identity.",
    ] = "status",
    collection: Annotated[str | None, "Collection name for action='user' (e.g. 'users')."] = None,
    email: Annotated[str | None, "Email or username for 'user' or 'superuser' auth."] = None,
    password: Annotated[str | None, "Password for 'user' or 'superuser' auth."] = None,
    user_id: Annotated[str | None, "Record id to impersonate (action='impersonate')."] = None,
) -> dict[str, Any]:
    """USE WHEN you need to authenticate or check the current session identity.

    EXAMPLES:
    - Check identity: connect(as_="status")
    - Superuser: connect(as_="superuser", email="admin@x.com", password="...")
    - User: connect(as_="user", collection="users", email="u@x.com", password="...")
    - Impersonate: connect(as_="impersonate", user_id="abc123")

    NEXT STEPS: All subsequent tool calls in this session use the new identity.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    if as_ == "status":
        return ok_response(
            {
                "identity": state.identity,
                "startup_auth_error": state.startup_auth_error,
            },
            hint="Use connect(as_='superuser') to authenticate as admin.",
        )

    prev_identity = state.identity

    if as_ == "superuser":
        if not email or not password:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "email and password required for as_='superuser'.", "hint": "Provide email and password."}
        result = await pb.superusers.auth_with_password(email, password)
        if isinstance(result, Err):
            return to_agent_error(result.err_value)
        state.identity = f"superuser:{email}"

    elif as_ == "user":
        if not collection:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "collection required for as_='user'.", "hint": "Provide the collection name (e.g. 'users')."}
        if not email or not password:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "email and password required for as_='user'.", "hint": "Provide email and password."}
        result = await pb.collection(collection).auth_with_password(email, password)
        if isinstance(result, Err):
            return to_agent_error(result.err_value)
        state.identity = f"user:{collection}:{email}"

    elif as_ == "impersonate":
        if not user_id:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "user_id required for as_='impersonate'.", "hint": "Provide the record id of the user to impersonate."}
        result = await pb.superusers.impersonate(user_id)
        if isinstance(result, Err):
            # Leave existing identity untouched
            return to_agent_error(result.err_value)
        state.identity = f"impersonate:{user_id}"

    return ok_response(
        {
            "identity": state.identity,
            "previous_identity": prev_identity,
            "note": "All subsequent calls in this session use this identity.",
        },
        hint="Use connect(as_='status') to verify at any time.",
    )


async def manage_auth(
    ctx: Context,
    action: Annotated[
        Literal[
            "request_password_reset",
            "confirm_password_reset",
            "request_verification",
            "confirm_verification",
            "request_email_change",
            "confirm_email_change",
            "refresh",
        ],
        "Auth lifecycle action.",
    ],
    collection: Annotated[str | None, "Collection name (required for all actions except refresh)."] = None,
    email: Annotated[str | None, "Email address (request_* actions)."] = None,
    token: Annotated[str | None, "Confirmation token from the email link (confirm_* actions)."] = None,
    new_email: Annotated[str | None, "New email address (request_email_change only)."] = None,
    password: Annotated[str | None, "New password (confirm_password_reset) or current password (confirm_email_change)."] = None,
    password_confirm: Annotated[str | None, "Password confirmation (confirm_password_reset only)."] = None,
) -> dict[str, Any]:
    """USE WHEN you need to manage auth lifecycle: password reset, verification, email change, or token refresh.

    EXAMPLES:
    - Request reset: manage_auth(action="request_password_reset", collection="users", email="u@x.com")
    - Confirm reset: manage_auth(action="confirm_password_reset", collection="users", token="...", password="new", password_confirm="new")
    - Refresh token: manage_auth(action="refresh", collection="users")

    NEXT STEPS: connect(as_='status') to verify identity after refresh.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Per-action required-arg validation
    required_args: dict[str, list[str]] = {
        "request_password_reset": ["collection", "email"],
        "confirm_password_reset": ["collection", "token", "password", "password_confirm"],
        "request_verification": ["collection", "email"],
        "confirm_verification": ["collection", "token"],
        "request_email_change": ["collection", "new_email"],
        "confirm_email_change": ["collection", "token", "password"],
        "refresh": ["collection"],
    }

    locals_map = {
        "collection": collection,
        "email": email,
        "token": token,
        "new_email": new_email,
        "password": password,
        "password_confirm": password_confirm,
    }
    missing = [k for k in required_args.get(action, []) if not locals_map.get(k)]
    if missing:
        return {
            "ok": False,
            "error_type": "MISSING_ARGS",
            "message": f"action='{action}' requires: {', '.join(missing)}.",
            "hint": f"Provide the missing argument(s): {', '.join(missing)}.",
        }

    svc = pb.collection(collection)  # type: ignore[arg-type]

    if action == "request_password_reset":
        result = await svc.request_password_reset(email)  # type: ignore[arg-type]
    elif action == "confirm_password_reset":
        result = await svc.confirm_password_reset(token, password, password_confirm)  # type: ignore[arg-type]
    elif action == "request_verification":
        result = await svc.request_verification(email)  # type: ignore[arg-type]
    elif action == "confirm_verification":
        result = await svc.confirm_verification(token)  # type: ignore[arg-type]
    elif action == "request_email_change":
        result = await svc.request_email_change(new_email)  # type: ignore[arg-type]
    elif action == "confirm_email_change":
        result = await svc.confirm_email_change(token, password)  # type: ignore[arg-type]
    elif action == "refresh":
        result = await svc.auth_refresh()

    if isinstance(result, Err):
        return to_agent_error(result.err_value)

    return ok_response(
        {"action": action, "collection": collection, "status": "success"},
        hint="Use connect(as_='status') to verify the current identity.",
    )
