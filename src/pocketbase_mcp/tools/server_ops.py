"""Server operation tools: inspect_server, read_logs."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from result import Err

from ..config import settings
from ..errors import ok_response, to_agent_error
from ..server import ServerState


async def inspect_server(
    ctx: Context,
) -> dict[str, Any]:
    """USE WHEN you need an overview of server health, settings, cron jobs, and log statistics.

    EXAMPLES:
    - "Is PocketBase running?" -> inspect_server()
    - "What cron jobs are registered?" -> inspect_server()
    - "How many requests in the last 7 days?" -> inspect_server()

    NEXT STEPS: read_logs for detailed log entries; connect(as_='superuser') for full access.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb
    output: dict[str, Any] = {}

    # Health — always attempted
    health_result = await pb.health.check()
    if isinstance(health_result, Err):
        output["health"] = {"unavailable": health_result.err_value.original_message}
    else:
        output["health"] = health_result.ok_value

    # Settings summary — superuser only
    settings_result = await pb.settings.get()
    if isinstance(settings_result, Err):
        err = settings_result.err_value
        if hasattr(err, "type"):
            output["settings"] = {
                "unavailable": err.original_message,
                "hint": "Use connect(as_='superuser') for settings access.",
            }
        else:
            output["settings"] = {"unavailable": str(err)}
    else:
        raw = settings_result.ok_value
        # Summary only — omit secrets and full config
        output["settings"] = {
            "app_name": raw.get("meta", {}).get("appName"),
            "sender_address": raw.get("smtp", {}).get("senderAddress"),
            "s3_enabled": bool(raw.get("s3", {}).get("enabled")),
        }

    # Cron list — superuser only
    cron_result = await pb.crons.list()
    if isinstance(cron_result, Err):
        output["crons"] = {
            "unavailable": cron_result.err_value.original_message,
            "hint": "Use connect(as_='superuser') for cron access.",
        }
    else:
        output["crons"] = cron_result.ok_value

    # Log stats — superuser only
    stats_result = await pb.logs.stats()
    if isinstance(stats_result, Err):
        output["log_stats"] = {
            "unavailable": stats_result.err_value.original_message,
            "hint": "Use connect(as_='superuser') for log access.",
        }
    else:
        output["log_stats"] = {
            "daily_stats": stats_result.ok_value,
            "total_days": len(stats_result.ok_value),
        }

    return ok_response(output, hint="Use read_logs for detailed request log entries.")




async def read_logs(
    ctx: Context,
    log_id: Annotated[str | None, "Fetch a single log entry by id. Mutually exclusive with filter."] = None,
    filter_template: Annotated[str | None, "PocketBase filter for log entries, e.g. 'level = {:l}'"] = None,
    filter_params: Annotated[dict[str, Any] | None, "Values for filter placeholders."] = None,
    page: Annotated[int, "Page number."] = 1,
    per_page: Annotated[int, "Entries per page. Clamped to the server max."] = 50,
) -> dict[str, Any]:
    """USE WHEN you need to inspect request log entries. Superuser access required.

    EXAMPLES:
    - Latest logs: read_logs()
    - Single entry: read_logs(log_id="xyz")
    - Filter by level: read_logs(filter_template="level >= {:l}", filter_params={"l": 4})

    NEXT STEPS: inspect_server for aggregate stats; connect(as_='superuser') if unauthorized.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Clamp page size
    clamped = min(per_page, settings.log_page_size_max)

    if log_id is not None:
        result = await pb.logs.get_one(log_id)
        if isinstance(result, Err):
            err = result.err_value
            if hasattr(err, "type"):
                from pocketbase.utils.errors import ErrorType
                if err.type == ErrorType.UNAUTHORIZED_ERROR:
                    return {
                        "ok": False,
                        "error_type": "UNAUTHORIZED_ERROR",
                        "message": err.original_message,
                        "hint": "Use connect(as_='superuser') to access logs.",
                    }
            return to_agent_error(err)
        return ok_response(result.ok_value.model_dump())

    from ..domain.filters import build_filter
    from ..domain.params import params_list

    filter_str: str | None = None
    if filter_template:
        try:
            filter_str = build_filter(pb, filter_template, filter_params or {})
        except ValueError as e:
            return {"ok": False, "error_type": "FILTER_ERROR", "message": str(e), "hint": "Provide all {:placeholder} values in filter_params."}

    params = params_list(filter=filter_str, page=page, per_page=clamped)
    result = await pb.logs.list(params_list=params)
    if isinstance(result, Err):
        err = result.err_value
        if hasattr(err, "type"):
            from pocketbase.utils.errors import ErrorType
            if err.type == ErrorType.UNAUTHORIZED_ERROR:
                return {
                    "ok": False,
                    "error_type": "UNAUTHORIZED_ERROR",
                    "message": err.original_message,
                    "hint": "Use connect(as_='superuser') to access logs.",
                }
        return to_agent_error(err)

    lr = result.ok_value
    return ok_response(
        {
            "items": [e.model_dump() for e in lr.items],
            "page": lr.page,
            "per_page": clamped,
            "clamped": clamped != per_page,
            "total_items": lr.total_items,
            "total_pages": lr.total_pages,
        }
    )


