"""FastMCP server bootstrap — lifespan, state, entry point."""

from __future__ import annotations

import argparse
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP

# fastmcp 3.x narrowed add_tool / add_resource / add_prompt to a single object
# arg; wrap callables via these factories. Resolved import paths under fastmcp
# 3.4.7 (the public `fastmcp.tools.tool` name is a runtime shim Pyright cannot
# follow, so import from the real modules):
#   Tool      -> fastmcp.tools.base
#   Resource  -> fastmcp.resources
#   Prompt    -> fastmcp.prompts.base
from fastmcp.prompts.base import Prompt
from fastmcp.resources import Resource
from fastmcp.tools.base import Tool
from mcp.types import ToolAnnotations
from pocketbase import Client

from .config import settings
from .domain.schema import SchemaCache

logger = logging.getLogger(__name__)


@dataclass
class ServerState:
    pb: Client
    schema_cache: SchemaCache
    identity: str = "anonymous"
    startup_auth_error: str | None = None


def build_mcp(lifespan: Any = None) -> FastMCP:
    # fastmcp 3.x only wires a lifespan passed to the constructor into
    # `ctx.request_context.lifespan_context`; assigning `mcp.lifespan` after
    # construction is a no-op. This is the single seam the tests inject a
    # mock `ServerState` through (see tests/conftest.py).
    from . import prompts, resources
    from .tools import (
        auth,
        collection_mgmt,
        files,
        records,
        schema,
        server_ops,
    )

    mcp = FastMCP(name="pocketbase", lifespan=lifespan) if lifespan else FastMCP(name="pocketbase")

    # mcp.types.ToolAnnotations is camelCase-keyed; snake_case kwargs would be
    # silently accepted as extras and the hint dropped.
    _read = ToolAnnotations(readOnlyHint=True)
    _idem = ToolAnnotations(idempotentHint=True)
    _dest = ToolAnnotations(destructiveHint=True)

    # Always-registered tools
    mcp.add_tool(Tool.from_function(schema.describe_schema, annotations=_read))
    mcp.add_tool(Tool.from_function(schema.describe_collection, annotations=_read))
    mcp.add_tool(Tool.from_function(records.find_records, annotations=_read))
    mcp.add_tool(Tool.from_function(records.write_record, annotations=_idem))
    mcp.add_tool(Tool.from_function(records.bulk_write))
    mcp.add_tool(Tool.from_function(collection_mgmt.manage_collection, annotations=_idem))
    mcp.add_tool(Tool.from_function(auth.connect))
    mcp.add_tool(Tool.from_function(auth.manage_auth))
    mcp.add_tool(Tool.from_function(files.manage_files))
    mcp.add_tool(Tool.from_function(server_ops.inspect_server, annotations=_read))
    mcp.add_tool(Tool.from_function(server_ops.read_logs, annotations=_read))

    # Destructive tools — only when explicitly opted in
    if settings.enable_destructive:
        mcp.add_tool(Tool.from_function(records.delete_records, annotations=_dest))
        mcp.add_tool(Tool.from_function(collection_mgmt.destroy_collection, annotations=_dest))

    # Resources
    mcp.add_resource(
        Resource.from_function(
            resources.schema_resource,
            uri="pocketbase://schema",
            name="schema",
            description="All PocketBase collections — id, name, type, field_count.",
        )
    )

    # Prompts — fastmcp 3.x add_prompt also requires a Prompt object, not a bare fn
    mcp.add_prompt(Prompt.from_function(prompts.inspect_then_query))
    mcp.add_prompt(Prompt.from_function(prompts.safe_delete))
    mcp.add_prompt(Prompt.from_function(prompts.create_with_validation))

    return mcp


@asynccontextmanager
async def pb_lifespan(server: Any):
    pb = Client(url=settings.url)
    async with pb:
        schema_cache = SchemaCache(pb)
        state = ServerState(pb=pb, schema_cache=schema_cache)

        if settings.auto_auth:
            from result import Err

            result = await pb.superusers.auth_with_password(
                settings.admin_email,  # type: ignore[arg-type]
                settings.admin_password,  # type: ignore[arg-type]
            )
            if isinstance(result, Err):
                reason = result.err_value.original_message
                logger.error("Startup superuser auth failed: %s", reason)
                state.startup_auth_error = reason
            else:
                state.identity = f"superuser:{settings.admin_email}"
                logger.info("Startup superuser auth succeeded: %s", settings.admin_email)

        yield {"pb": state}


def main() -> None:
    parser = argparse.ArgumentParser(description="PocketBase MCP server")
    parser.add_argument("--http", action="store_true", help="Use HTTP transport")
    args = parser.parse_args()

    mcp = build_mcp(lifespan=pb_lifespan)

    if args.http:
        mcp.run(transport="http", host=settings.http_host, port=settings.http_port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
