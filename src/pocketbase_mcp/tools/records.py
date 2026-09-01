"""Record operation tools: find_records, write_record, bulk_write, delete_records."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from fastmcp.exceptions import ToolError
from result import Err

from ..config import settings
from ..domain.filters import build_filter
from ..domain.params import params_list, params_one
from ..domain.schema import validate_payload
from ..errors import ok_response, to_agent_error
from ..server import ServerState


async def find_records(
    ctx: Context,
    collection: Annotated[str, "Collection name or id."],
    record_id: Annotated[str | None, "Fetch exactly one record by id. Mutually exclusive with filter_template."] = None,
    filter_template: Annotated[str | None, "PocketBase filter with {:name} placeholders, e.g. 'status = {:s}'"] = None,
    filter_params: Annotated[dict[str, Any] | None, "Values for {:name} placeholders in filter_template."] = None,
    expand: Annotated[str | None, "Comma-separated relation fields to expand."] = None,
    fields: Annotated[str | None, "Comma-separated fields to return (projection)."] = None,
    sort: Annotated[str | None, "Sort expression, e.g. '-created,title'."] = None,
    page: Annotated[int, "Page number (1-based)."] = 1,
    per_page: Annotated[int, "Records per page."] = 30,
    fetch_all: Annotated[bool, "Fetch every matching record across all pages. Caution: may be large."] = False,
) -> dict[str, Any]:
    """USE WHEN you need to query or look up records in a collection.

    EXAMPLES:
    - By id: find_records(collection="posts", record_id="abc123")
    - By filter: find_records(collection="posts", filter_template="status = {:s}", filter_params={"s": "published"})
    - All records: find_records(collection="posts", fetch_all=True)

    NEXT STEPS: write_record to mutate, describe_collection for field names.
    """
    if record_id is not None and filter_template is not None:
        return {"ok": False, "error_type": "INVALID_ARGS", "message": "Provide record_id OR filter_template, not both.", "hint": "Use record_id for a known id, filter_template to search."}

    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    if record_id is not None:
        params = params_one(expand=expand, fields=fields)
        result = await pb.collection(collection).get_one(record_id, params)
        if isinstance(result, Err):
            return to_agent_error(result.err_value)
        return ok_response(result.ok_value.model_dump(), hint="Use write_record to update this record.")

    # Build filter string
    filter_str: str | None = None
    if filter_template is not None:
        try:
            filter_str = build_filter(pb, filter_template, filter_params or {})
        except ValueError as e:
            return {"ok": False, "error_type": "FILTER_ERROR", "message": str(e), "hint": "Provide all {:placeholder} values in filter_params."}

    if fetch_all:
        # First page to discover total_pages
        _batch = 200
        first_params = params_list(
            filter=filter_str,
            expand=expand,
            fields=fields,
            sort=sort,
            page=1,
            per_page=_batch,
        )
        first_result = await pb.collection(collection).list(first_params)
        if isinstance(first_result, Err):
            return to_agent_error(first_result.err_value)
        lr0 = first_result.ok_value
        all_records = list(lr0.items)
        total_pages = lr0.total_pages

        if total_pages > 1:
            await ctx.report_progress(1, total_pages)
            for p in range(2, total_pages + 1):
                page_params = params_list(
                    filter=filter_str,
                    expand=expand,
                    fields=fields,
                    sort=sort,
                    page=p,
                    per_page=_batch,
                )
                page_result = await pb.collection(collection).list(page_params)
                if isinstance(page_result, Err):
                    return to_agent_error(page_result.err_value)
                all_records.extend(page_result.ok_value.items)
                await ctx.report_progress(p, total_pages)

        records = [r.model_dump() for r in all_records]
        return ok_response({"records": records, "total": len(records)})

    params_page = params_list(
        filter=filter_str,
        expand=expand,
        fields=fields,
        sort=sort,
        page=page,
        per_page=per_page,
    )
    result_page = await pb.collection(collection).list(params_page)
    if isinstance(result_page, Err):
        return to_agent_error(result_page.err_value)

    lr = result_page.ok_value
    return ok_response(
        {
            "records": [r.model_dump() for r in lr.items],
            "page": lr.page,
            "per_page": lr.per_page,
            "total_items": lr.total_items,
            "total_pages": lr.total_pages,
        },
        hint="Use fetch_all=True to retrieve all records at once." if lr.total_pages > 1 else None,
    )




async def write_record(
    ctx: Context,
    collection: Annotated[str, "Collection name or id."],
    action: Annotated[Literal["create", "update"], "Whether to create a new record or update an existing one."],
    data: Annotated[dict[str, Any], "Field values to set. For update, include only fields to change."],
    record_id: Annotated[str | None, "Required for action='update'. The id of the record to update."] = None,
    expand: Annotated[str | None, "Comma-separated relation fields to expand in the response."] = None,
) -> dict[str, Any]:
    """USE WHEN you need to create or update a single record.

    EXAMPLES:
    - Create: write_record(collection="posts", action="create", data={"title": "Hi", "body": "..."})
    - Update: write_record(collection="posts", action="update", record_id="abc", data={"title": "New"})

    NEXT STEPS: find_records to verify, describe_collection for field names.
    """
    if action == "update" and not record_id:
        return {"ok": False, "error_type": "INVALID_ARGS", "message": "record_id is required for action='update'.", "hint": "Use find_records to locate the record id."}

    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Schema validation
    fields_result = await state.schema_cache.get_fields(collection)
    if isinstance(fields_result, Err):
        return {"ok": False, "error_type": "COLLECTION_NOT_FOUND", "message": fields_result.err_value, "hint": "Use describe_schema to list collections."}

    errors = validate_payload(fields_result.ok_value, data, action)
    if errors:
        return {"ok": False, "error_type": "VALIDATION_ERROR", "message": "; ".join(errors), "hint": "Use describe_collection for field details."}

    from pocketbase.utils.params import ParamsOne

    params = ParamsOne(expand=expand) if expand else None

    if action == "create":
        result = await pb.collection(collection).create(body=data, params=params)
    else:
        result = await pb.collection(collection).update(record_id, body=data, params=params)  # type: ignore[arg-type]

    if isinstance(result, Err):
        return to_agent_error(result.err_value)

    return ok_response(result.ok_value.model_dump(), hint="Use find_records to query related records.")




async def bulk_write(
    ctx: Context,
    operations: Annotated[
        list[dict[str, Any]],
        "List of operations. Each: {collection, action: create|update|upsert|delete, data?, record_id?}.",
    ],
) -> dict[str, Any]:
    """USE WHEN you need to create/update/delete multiple records atomically.

    EXAMPLES:
    - operations=[
        {"collection": "posts", "action": "create", "data": {"title": "A"}},
        {"collection": "posts", "action": "update", "record_id": "xyz", "data": {"title": "B"}},
      ]

    NEXT STEPS: find_records to verify results.
    """
    if not operations:
        return {"ok": False, "error_type": "INVALID_ARGS", "message": "operations list is empty.", "hint": "Provide at least one operation."}

    if len(operations) > settings.batch_limit:
        return {
            "ok": False,
            "error_type": "BATCH_TOO_LARGE",
            "message": f"Batch has {len(operations)} operations; limit is {settings.batch_limit}.",
            "hint": f"Split into chunks of at most {settings.batch_limit} and call bulk_write for each.",
        }

    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Pre-dispatch schema validation
    for i, op in enumerate(operations):
        col = op.get("collection", "")
        action = op.get("action", "")
        data = op.get("data", {})

        if action in ("create", "update") and data:
            fields_result = await state.schema_cache.get_fields(col)
            if isinstance(fields_result, Err):
                return {
                    "ok": False,
                    "error_type": "COLLECTION_NOT_FOUND",
                    "message": f"Operation {i}: {fields_result.err_value}",
                    "hint": "Use describe_schema to list collections.",
                }
            errors = validate_payload(fields_result.ok_value, data, "create" if action == "create" else "update")
            if errors:
                return {
                    "ok": False,
                    "error_type": "VALIDATION_ERROR",
                    "message": f"Operation {i}: {'; '.join(errors)}",
                    "hint": "Use describe_collection for field details.",
                }

    # Build batch
    batch = pb.create_batch()
    for op in operations:
        col = op["collection"]
        action = op["action"]
        sub = batch.collection(col)
        if action == "create":
            sub.create(op.get("data", {}))
        elif action == "update":
            sub.update(op["record_id"], op.get("data", {}))
        elif action == "upsert":
            sub.upsert(op["record_id"], op.get("data", {}))
        elif action == "delete":
            sub.delete(op["record_id"])

    result = await batch.send()
    if isinstance(result, Err):
        from pocketbase.utils.errors import PocketbaseException

        exc = result.err_value
        if isinstance(exc, PocketbaseException):
            return to_agent_error(exc)
        return {
            "ok": False,
            "error_type": "BATCH_ERROR",
            "message": str(exc),
            "hint": (
                f"Check individual operation data; PocketBase rejects batches larger "
                f"than its configured limit (send at most {settings.batch_limit})."
            ),
        }

    n = len(operations)
    await ctx.report_progress(n, n)

    return ok_response(
        {"results": [r.model_dump() for r in result.ok_value], "count": len(result.ok_value)},
        hint="Use find_records to verify the changes.",
    )


async def delete_records(
    ctx: Context,
    collection: Annotated[str, "Collection name or id."],
    confirm_count: Annotated[int, "Must exactly match the number of records that will be deleted. Obtain with find_records first."],
    record_ids: Annotated[list[str] | None, "Explicit list of record ids to delete. Mutually exclusive with filter_template."] = None,
    filter_template: Annotated[str | None, "Filter to select records for deletion. Mutually exclusive with record_ids."] = None,
    filter_params: Annotated[dict[str, Any] | None, "Values for {:name} placeholders in filter_template."] = None,
) -> dict[str, Any]:
    """USE WHEN you need to permanently delete records. IRREVERSIBLE.

    Always call find_records first to get the exact count, then pass that count as confirm_count.

    EXAMPLES:
    - delete_records(collection="posts", record_ids=["abc"], confirm_count=1)
    - delete_records(collection="posts", filter_template="status = {:s}", filter_params={"s": "draft"}, confirm_count=5)

    NEXT STEPS: find_records to verify deletion.
    """
    if record_ids is not None and filter_template is not None:
        raise ToolError("Provide record_ids OR filter_template, not both.")

    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Resolve target ids
    if record_ids is not None:
        target_ids = record_ids
    elif filter_template is not None:
        try:
            filter_str = build_filter(pb, filter_template, filter_params or {})
        except ValueError as e:
            return {"ok": False, "error_type": "FILTER_ERROR", "message": str(e), "hint": "Provide all {:placeholder} values in filter_params."}

        from pocketbase.utils.params import ParamsList

        all_result = await pb.collection(collection).get_full_list(
            params_list=ParamsList(filter=filter_str, fields="id")
        )
        if isinstance(all_result, Err):
            return to_agent_error(all_result.err_value)
        target_ids = [r.id for r in all_result.ok_value]
    else:
        raise ToolError("Provide either record_ids or filter_template.")

    if len(target_ids) != confirm_count:
        raise ToolError(
            f"confirm_count={confirm_count} does not match the resolved count={len(target_ids)}. "
            f"Use find_records to get the exact count before deleting."
        )

    deleted: list[str] = []
    errors: list[str] = []
    for rid in target_ids:
        result = await pb.collection(collection).delete(rid)
        if isinstance(result, Err):
            errors.append(f"{rid}: {result.err_value.original_message}")
        else:
            deleted.append(rid)

    if errors:
        return {
            "ok": False,
            "error_type": "PARTIAL_DELETE",
            "message": f"Deleted {len(deleted)}/{len(target_ids)}. Errors: {'; '.join(errors)}",
            "hint": "Use find_records to check remaining records.",
            "deleted": deleted,
        }

    return ok_response(
        {"deleted": deleted, "count": len(deleted)},
        hint="Use find_records to verify deletion.",
    )


