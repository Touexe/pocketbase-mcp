"""Collection management tools: manage_collection, destroy_collection."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from fastmcp.exceptions import ToolError
from result import Err

from ..errors import ok_response, to_agent_error
from ..server import ServerState


async def manage_collection(
    ctx: Context,
    action: Annotated[Literal["create", "update"], "Whether to create a new collection or update an existing one."],
    name: Annotated[str, "Collection name."],
    collection_type: Annotated[Literal["base", "auth", "view"], "Collection type (for create only)."] = "base",
    fields: Annotated[list[dict[str, Any]] | None, "Field definitions. See PocketBase schema for field shapes."] = None,
    view_query: Annotated[str | None, "SQL query (for type='view' only). Validated before creation."] = None,
    api_rules: Annotated[dict[str, str | None] | None, "API rules: {list, view, create, update, delete}."] = None,
    indexes: Annotated[list[str] | None, "Index definitions."] = None,
) -> dict[str, Any]:
    """USE WHEN you need to create or modify a collection schema.

    EXAMPLES:
    - Create base: manage_collection(action="create", name="posts", fields=[{"name": "title", "type": "text", "required": True}])
    - Create view: manage_collection(action="create", name="post_stats", collection_type="view", view_query="SELECT id, title FROM posts")
    - Update rules: manage_collection(action="update", name="posts", api_rules={"list": "@request.auth.id != ''"})

    NEXT STEPS: describe_collection to verify, find_records or write_record to use.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Validate view query before dispatch
    if collection_type == "view" and view_query:
        dry_result = await pb.collections.dry_run_view(view_query)
        if isinstance(dry_result, Err):
            return {
                "ok": False,
                "error_type": "VIEW_QUERY_INVALID",
                "message": dry_result.err_value.original_message,
                "hint": "Fix the SQL query and retry manage_collection.",
            }

    # Validate relation targets against cache
    if fields:
        all_cols_result = await state.schema_cache.all_collections()
        if isinstance(all_cols_result, Err):
            return {"ok": False, "error_type": "CACHE_LOAD_ERROR", "message": all_cols_result.err_value, "hint": "Use describe_schema to refresh the cache."}
        known_ids = {c.id for c in all_cols_result.ok_value if c.id}
        known_names = {c.name for c in all_cols_result.ok_value}
        for f in fields:
            if f.get("type") == "relation":
                target = f.get("collectionId") or f.get("collection_id")
                if target and target not in known_ids and target not in known_names:
                    return {
                        "ok": False,
                        "error_type": "UNKNOWN_RELATION_TARGET",
                        "message": f"Relation field '{f.get('name')}' targets unknown collection '{target}'.",
                        "hint": "Use describe_schema to list available collections and their ids.",
                    }

    if action == "create":
        body: dict[str, Any] = {"name": name, "type": collection_type}
        if fields:
            body["fields"] = fields
        if view_query:
            body["viewQuery"] = view_query
        if api_rules:
            rule_map = {
                "list": "listRule",
                "view": "viewRule",
                "create": "createRule",
                "update": "updateRule",
                "delete": "deleteRule",
            }
            for k, v in api_rules.items():
                body[rule_map.get(k, k)] = v
        if indexes:
            body["indexes"] = indexes

        result = await pb.collections.create(body)
    else:
        body = {}
        if fields is not None:
            body["fields"] = fields
        if api_rules:
            rule_map = {
                "list": "listRule",
                "view": "viewRule",
                "create": "createRule",
                "update": "updateRule",
                "delete": "deleteRule",
            }
            for k, v in api_rules.items():
                body[rule_map.get(k, k)] = v
        if indexes is not None:
            body["indexes"] = indexes

        result = await pb.collections.update(name, body)

    if isinstance(result, Err):
        return to_agent_error(result.err_value)

    state.schema_cache.invalidate()
    col = result.ok_value
    return ok_response(
        {"name": col.name, "id": col.id, "type": col.type, "field_count": len(col.fields)},
        hint="Use describe_collection to see the full schema.",
    )




async def destroy_collection(
    ctx: Context,
    action: Annotated[Literal["delete", "truncate"], "delete removes the collection and all its records; truncate removes all records but keeps the schema."],
    name: Annotated[str, "Collection name."],
    confirm_name: Annotated[str, "Must exactly match the collection name. Safety confirmation."],
) -> dict[str, Any]:
    """USE WHEN you need to permanently delete a collection or all its records. IRREVERSIBLE.

    EXAMPLES:
    - delete_collection: destroy_collection(action="delete", name="temp_data", confirm_name="temp_data")
    - truncate: destroy_collection(action="truncate", name="events", confirm_name="events")

    NEXT STEPS: describe_schema to confirm removal.
    """
    if confirm_name != name:
        raise ToolError(
            f"confirm_name='{confirm_name}' does not match name='{name}'. "
            f"Pass confirm_name='{name}' to confirm this irreversible operation."
        )

    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    if action == "delete":
        result = await pb.collections.delete(name)
    else:
        result = await pb.collections.truncate(name)

    if isinstance(result, Err):
        return to_agent_error(result.err_value)

    state.schema_cache.invalidate()
    return ok_response(
        {"action": action, "collection": name},
        hint="Use describe_schema to verify the change.",
    )


