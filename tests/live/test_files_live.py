"""Section 8 — live file operations: manage_files upload / url / download.

Open question from design.md, resolved here: the upload fixture is a
**generated temp file** (a few bytes written at test time), not a committed
binary asset. No thumbnail behaviour is exercised, so a real image is not
needed; if thumbnail coverage is ever added, commit a small PNG under
``tests/live/assets/`` and load it instead.
"""

from __future__ import annotations

import urllib.request

import pytest

from pocketbase_mcp.config import settings

from .helpers import err_payload, ok_data, serialize

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FILE_FIELDS = [
    {"name": "title", "type": "text", "required": False},
    {"name": "doc", "type": "file", "maxSelect": 1},
]
_PAYLOAD = b"live-suite file body \x00\x01\x02 the quick brown fox"


async def _record_with_file(live_client, live_collection, tmp_path):
    name = await live_collection("file", _FILE_FIELDS)
    rid = ok_data(
        await live_client.call_tool(
            "write_record", {"collection": name, "action": "create", "data": {"title": "f"}}
        )
    )["id"]

    local = tmp_path / "blob.bin"
    local.write_bytes(_PAYLOAD)

    uploaded = ok_data(
        await live_client.call_tool(
            "manage_files",
            {
                "action": "upload",
                "collection": name,
                "record_id": rid,
                "field": "doc",
                "local_path": str(local),
                "filename": "blob.bin",
            },
        )
    )
    stored_name = uploaded["doc"]
    return name, rid, stored_name


async def test_upload_then_download_same_bytes(live_client, live_collection, tmp_path) -> None:
    """8.1 — upload through manage_files, download it back, assert byte-length equality
    (the tool surfaces ``bytes_downloaded``, not the bytes themselves) and confirm the
    real bytes match by fetching the file URL."""
    name, rid, stored = await _record_with_file(live_client, live_collection, tmp_path)

    dl = ok_data(
        await live_client.call_tool(
            "manage_files",
            {
                "action": "download",
                "collection": name,
                "record_id": rid,
                "field": "doc",
                "filename": stored,
            },
        )
    )
    assert dl["bytes_downloaded"] == len(_PAYLOAD)

    url = ok_data(
        await live_client.call_tool(
            "manage_files",
            {
                "action": "url",
                "collection": name,
                "record_id": rid,
                "field": "doc",
                "filename": stored,
            },
        )
    )["url"]
    with urllib.request.urlopen(url) as resp:  # noqa: S310 — local dev instance
        assert resp.read() == _PAYLOAD


async def test_url_resolves_against_instance(live_client, live_collection, tmp_path) -> None:
    """8.2 — manage_files(action='url') returns a URL that resolves against the live instance."""
    name, rid, stored = await _record_with_file(live_client, live_collection, tmp_path)

    url = ok_data(
        await live_client.call_tool(
            "manage_files",
            {
                "action": "url",
                "collection": name,
                "record_id": rid,
                "field": "doc",
                "filename": stored,
            },
        )
    )["url"]
    assert url.startswith(settings.url)
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        assert resp.status == 200


async def test_no_file_token_in_any_response(live_client, live_collection, tmp_path) -> None:
    """8.3 — no manage_files response contains a file token."""
    name, rid, stored = await _record_with_file(live_client, live_collection, tmp_path)

    for action in ("url", "download"):
        result = await live_client.call_tool(
            "manage_files",
            {
                "action": action,
                "collection": name,
                "record_id": rid,
                "field": "doc",
                "filename": stored,
            },
        )
        blob = serialize(result.data)
        assert "token=" not in blob
        assert '"token"' not in blob


async def test_non_file_field_and_missing_path_short_circuit(
    live_client, live_collection, tmp_path
) -> None:
    """8.4 — a non-file field and a missing local path each short-circuit with a structured error."""
    name, rid, _ = await _record_with_file(live_client, live_collection, tmp_path)

    bad_field = await live_client.call_tool(
        "manage_files",
        {
            "action": "url",
            "collection": name,
            "record_id": rid,
            "field": "title",
            "filename": "x",
        },
        raise_on_error=False,
    )
    assert err_payload(bad_field)["error_type"] == "INVALID_FIELD"

    no_path = await live_client.call_tool(
        "manage_files",
        {"action": "upload", "collection": name, "record_id": rid, "field": "doc"},
        raise_on_error=False,
    )
    assert err_payload(no_path)["error_type"] == "INVALID_ARGS"
