"""File operation tool: manage_files."""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

from fastmcp import Context
from result import Err

from ..errors import ok_response, to_agent_error
from ..server import ServerState


async def manage_files(
    ctx: Context,
    action: Annotated[Literal["url", "download", "upload"], "url: get the file URL; download: fetch file bytes; upload: upload a local file."],
    collection: Annotated[str, "Collection name or id."],
    record_id: Annotated[str, "Record id that owns the file."],
    field: Annotated[str, "Field name that holds the file."],
    filename: Annotated[str | None, "Filename as stored in the record (required for url/download)."] = None,
    local_path: Annotated[str | None, "Absolute local path to upload (required for upload action)."] = None,
    thumb: Annotated[str | None, "Thumbnail size for image fields, e.g. '100x100'. Only for url action."] = None,
) -> dict[str, Any]:
    """USE WHEN you need to get a file URL, download a file, or upload a new file to a record.

    EXAMPLES:
    - URL: manage_files(action="url", collection="posts", record_id="abc", field="cover", filename="img.jpg")
    - Thumb: manage_files(action="url", ..., thumb="200x200")
    - Download: manage_files(action="download", ..., filename="doc.pdf")
    - Upload: manage_files(action="upload", ..., field="cover", local_path="/tmp/img.jpg", filename="img.jpg")

    NEXT STEPS: find_records to see the updated file field after upload.
    """
    state: ServerState = ctx.request_context.lifespan_context["pb"]
    pb = state.pb

    # Validate field is a file field
    fields_result = await state.schema_cache.get_fields(collection)
    if isinstance(fields_result, Err):
        return {"ok": False, "error_type": "COLLECTION_NOT_FOUND", "message": fields_result.err_value, "hint": "Use describe_schema to list collections."}

    file_fields = {f.name for f in fields_result.ok_value if getattr(f, "type", None) == "file"}
    if field not in file_fields:
        return {
            "ok": False,
            "error_type": "INVALID_FIELD",
            "message": f"Field '{field}' is not a file field in collection '{collection}'. File fields: {sorted(file_fields) or 'none'}.",
            "hint": "Use describe_collection to see field types.",
        }

    # Validate local path for upload
    if action == "upload":
        if not local_path:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "local_path required for upload action.", "hint": "Provide the absolute path to the file to upload."}
        if not os.path.exists(local_path):
            return {"ok": False, "error_type": "FILE_NOT_FOUND", "message": f"local_path '{local_path}' does not exist.", "hint": "Verify the file path before uploading."}

    if action == "url":
        if not filename:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "filename required for url action.", "hint": "Provide the filename from the record's file field."}

        # Fetch file token for protected fields
        field_obj = next((f for f in fields_result.ok_value if f.name == field), None)
        token: str | None = None
        if field_obj and getattr(field_obj, "protected", False):
            token_result = await pb.files.get_token()
            if isinstance(token_result, Err):
                return to_agent_error(token_result.err_value)
            token = token_result.ok_value

        url = pb.files.get_url(
            record=record_id,
            filename=filename,
            collection_id_or_name=collection,
            thumb=thumb,
            token=token,
        )
        return ok_response({"url": url}, hint="URL may be time-limited for protected files.")

    elif action == "download":
        if not filename:
            return {"ok": False, "error_type": "INVALID_ARGS", "message": "filename required for download action.", "hint": "Provide the filename from the record's file field."}

        field_obj = next((f for f in fields_result.ok_value if f.name == field), None)
        token = None
        if field_obj and getattr(field_obj, "protected", False):
            token_result = await pb.files.get_token()
            if isinstance(token_result, Err):
                return to_agent_error(token_result.err_value)
            token = token_result.ok_value

        dl_result = await pb.files.download(
            record=record_id,
            filename=filename,
            collection_id_or_name=collection,
            token=token,
        )
        if isinstance(dl_result, Err):
            return to_agent_error(dl_result.err_value)

        content = dl_result.ok_value
        return ok_response(
            {"bytes_downloaded": len(content), "filename": filename},
            hint="Use local_path with action='upload' to re-upload modified content.",
        )

    else:  # upload
        # pypocketbase builds a multipart PATCH whenever a body value is a
        # FileUpload (see pocketbase.utils.options.RequestOptions.need_form_data).
        from pocketbase.utils.file_upload import FileUpload

        upload = FileUpload(local_path)  # type: ignore[arg-type]
        if filename:
            upload.file_name = filename

        result = await pb.collection(collection).update(record_id, body={field: upload})
        if isinstance(result, Err):
            return to_agent_error(result.err_value)

        return ok_response(
            result.ok_value.model_dump(),
            hint="Use find_records to verify the updated file field.",
        )
