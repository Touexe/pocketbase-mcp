"""Schema discovery tools: describe_schema and describe_collection."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from result import Err

from ..errors import ok_response, to_agent_error
from ..server import ServerState


async def describe_schema(
    ctx: Context,
    refresh: Annotated[bool, "Force reload of the schema cache before listing."] = False,
) -> dict[str, Any]:
    """USE WHEN you need a quick inventory of all collections before querying or writing.

    EXAMPLES:
    - "What collections exist?" -> describe_schema()
    - "Does a 'posts' collection exist?" -> describe_schema()
    - After adding a collection -> describe_schema(refresh=True)

    NEXT STEPS: describe_collection(collection="<name>") for field details.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    cache = state.schema_cache

    if refresh:
        r = await cache.refresh()
        if isinstance(r, Err):
            return {"ok": False, "error_type": "CACHE_LOAD_ERROR", "message": r.err_value, "hint": "PocketBase may be unreachable. Use connect to verify the server is reachable."}

    result = await cache.all_collections()
    if isinstance(result, Err):
        return {"ok": False, "error_type": "CACHE_LOAD_ERROR", "message": result.err_value, "hint": "PocketBase may be unreachable. Use connect to verify the server is reachable."}

    collections = [
        {
            "name": c.name,
            "id": c.id,
            "type": c.type,
            "field_count": len(c.fields),
        }
        for c in result.ok_value
    ]

    return ok_response(
        {"collections": collections, "count": len(collections)},
        hint="Use describe_collection(collection='<name>') to see fields and API rules.",
    )




async def describe_collection(
    ctx: Context,
    collection: Annotated[str, "Collection name or id."],
) -> dict[str, Any]:
    """USE WHEN you need full field definitions, API rules, or relation targets for one collection.

    EXAMPLES:
    - "What fields does 'posts' have?" -> describe_collection(collection="posts")
    - Before write_record to see required fields -> describe_collection(collection="posts")
    - "What are the auth rules?" -> describe_collection(collection="users")

    NEXT STEPS: find_records or write_record with the correct field names.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    result = await state.schema_cache.get_collection(collection)

    if isinstance(result, Err):
        return {
            "ok": False,
            "error_type": "COLLECTION_NOT_FOUND",
            "message": result.err_value,
            "hint": "Use describe_schema() to list available collections.",
        }

    col = result.ok_value
    fields_out: list[dict[str, Any]] = []
    for f in col.fields:
        fd: dict[str, Any] = {
            "name": f.name,
            "type": f.type,
            "required": getattr(f, "required", False),
        }
        # Relation targets
        if f.type == "relation":
            fd["collection_id"] = getattr(f, "collection_id", None)
        # Select values
        if f.type == "select":
            fd["values"] = getattr(f, "values", [])
        # File field
        if f.type == "file":
            fd["max_select"] = getattr(f, "max_select", 1)
            fd["protected"] = getattr(f, "protected", False)
        fields_out.append(fd)

    return ok_response(
        {
            "name": col.name,
            "id": col.id,
            "type": col.type,
            "fields": fields_out,
            "api_rules": {
                "list": col.list_rule,
                "view": col.view_rule,
                "create": col.create_rule,
                "update": col.update_rule,
                "delete": col.delete_rule,
            },
            "indexes": col.indexes,
        },
        hint="Use write_record or find_records with these field names.",
    )


