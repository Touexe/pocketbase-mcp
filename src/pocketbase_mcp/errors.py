"""Agent-directive error contract.

Every tool returns either ok_response() or to_agent_error() — no tracebacks
escape to the agent. ToolError is reserved for the two cases where continuing
is meaningless: no client configured, and a destructive confirmation mismatch.
"""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError
from pocketbase.utils.errors import ErrorType, PocketbaseException

# Per-ErrorType hint table. Maps each error class to a recovery directive.
_HINTS: dict[ErrorType, str] = {
    ErrorType.RECORD_NOT_FOUND: (
        "Use find_records with a filter to locate the id, "
        "or verify the collection name with describe_schema."
    ),
    ErrorType.RECORD_LIST_NOT_FOUND: (
        "No records matched the filter. Broaden the filter or check the collection "
        "name with describe_schema."
    ),
    ErrorType.RECORD_NOT_CREATED: (
        "Record creation failed validation. Use describe_collection to see required "
        "fields and constraints."
    ),
    ErrorType.RECORD_NOT_UPDATED: (
        "Record update failed. Confirm the id with find_records and check field "
        "constraints with describe_collection."
    ),
    ErrorType.RECORD_NOT_DELETED: (
        "Record deletion failed. Confirm the id exists with find_records."
    ),
    ErrorType.RECORD_PERMISSION_ERROR: (
        "Insufficient permissions. Use connect as='superuser' or authenticate as "
        "a user with the required access."
    ),
    ErrorType.COLLECTION_NOT_FOUND: (
        "Collection not found. Use describe_schema to list available collections."
    ),
    ErrorType.COLLECTION_LIST_NOT_FOUND: (
        "No collections found. Use describe_schema with refresh=true if the schema "
        "was recently changed."
    ),
    ErrorType.COLLECTION_NOT_CREATED: (
        "Collection creation failed. Check field definitions with describe_collection "
        "and ensure relation targets exist."
    ),
    ErrorType.COLLECTION_NOT_UPDATED: (
        "Collection update failed. Verify the schema with describe_collection."
    ),
    ErrorType.COLLECTION_NOT_DELETED: (
        "Collection deletion failed. Ensure no other collections hold relations to it."
    ),
    ErrorType.COLLECTION_PERMISSION_ERROR: (
        "Superuser access required. Use connect as='superuser'."
    ),
    ErrorType.BATCH_REQUEST_ERROR: (
        "Batch request failed. Review individual operation errors and check field "
        "constraints with describe_collection."
    ),
    ErrorType.BATCH_REQUEST_PERMISSION_ERROR: (
        "Batch request denied. Use connect to authenticate with the required identity."
    ),
    ErrorType.UNAUTHORIZED_ERROR: (
        "Not authenticated. Use connect as='superuser' for admin operations or "
        "connect as='user' for record-level access."
    ),
    ErrorType.AUTH_RECORD_FAILED_AUTHENTICATION: (
        "Authentication failed. Verify credentials and collection name. "
        "Use connect as='status' to see the current identity."
    ),
    ErrorType.BAD_REQUEST_ERROR: (
        "Bad request. Check the payload with describe_collection for required fields "
        "and valid values."
    ),
    ErrorType.TOO_MANY_REQUESTS_ERROR: (
        "Rate limited by PocketBase. Wait before retrying or reduce request frequency."
    ),
    ErrorType.FILE_NOT_FOUND: (
        "File not found. Use find_records to confirm the record id and filename."
    ),
    ErrorType.LOG_NOT_FOUND: (
        "Log entry not found. Use read_logs to list available entries."
    ),
    ErrorType.CRON_NOT_FOUND: (
        "Cron job not found. Use inspect_server to list registered cron jobs."
    ),
    ErrorType.UNKNOWN_ERROR: (
        "Unexpected error from PocketBase. Check inspect_server for server health."
    ),
}


# pypocketbase does not classify by HTTP status: a bare 403/404/401 arrives as
# UNKNOWN_ERROR. Recover the contract's error class from the status code so the
# agent gets an actionable error_type and hint instead of "unexpected error".
_STATUS_FALLBACK: dict[int, ErrorType] = {
    401: ErrorType.UNAUTHORIZED_ERROR,
    403: ErrorType.UNAUTHORIZED_ERROR,
    404: ErrorType.COLLECTION_NOT_FOUND,
    429: ErrorType.TOO_MANY_REQUESTS_ERROR,
}


def to_agent_error(exc: PocketbaseException) -> dict[str, Any]:
    """Map a PocketbaseException to a structured agent-directive error dict."""
    status: int | None = None
    try:
        status = exc.response.code  # type: ignore[union-attr]
    except AttributeError:
        try:
            status = exc.response.status_code  # type: ignore[union-attr]
        except AttributeError:
            pass

    error_type = exc.type
    if error_type == ErrorType.UNKNOWN_ERROR and status is not None:
        error_type = _STATUS_FALLBACK.get(status, error_type)

    hint = _HINTS.get(error_type)
    if hint is None:
        # Fallback: use the library's own DEBUG string
        hint = getattr(error_type.value, "DEBUG", str(error_type.value))

    return {
        "ok": False,
        "error_type": error_type.name,
        "message": exc.original_message,
        "hint": hint,
        "status": status,
    }


def ok_response(data: Any, hint: str | None = None) -> dict[str, Any]:
    """Wrap a successful result with ok:true and an optional next-step hint."""
    result: dict[str, Any] = {"ok": True, "data": data}
    if hint is not None:
        result["hint"] = hint
    return result
