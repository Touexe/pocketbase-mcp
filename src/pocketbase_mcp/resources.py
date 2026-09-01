"""FastMCP resource definitions."""

from __future__ import annotations

import json
from typing import Any

from fastmcp import Context
from result import Err

from .server import ServerState


async def schema_resource(ctx: Context) -> str:
    """All PocketBase collections as JSON — id, name, type, field_count."""
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    result = await state.schema_cache.all_collections()
    if isinstance(result, Err):
        payload: dict[str, Any] = {
            "ok": False,
            "error_type": "SCHEMA_LOAD_ERROR",
            "message": result.err_value,
            "hint": "Use connect as='superuser' to authenticate, then retry.",
        }
        return json.dumps(payload)
    collections = [
        {
            "name": c.name,
            "id": c.id,
            "type": getattr(c, "type", "unknown"),
            "field_count": len(c.fields) if c.fields else 0,
        }
        for c in result.ok_value
    ]
    return json.dumps({"ok": True, "data": collections})
