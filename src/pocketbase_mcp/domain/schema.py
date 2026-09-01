"""Schema cache and payload validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from result import Err, Ok, Result

if TYPE_CHECKING:
    from pocketbase import Client
    from pocketbase.models.collection import Collection


class SchemaCache:
    """Lazy-loaded cache of PocketBase collection schemas."""

    def __init__(self, pb: "Client") -> None:
        self._pb = pb
        self._collections: dict[str, "Collection"] | None = None

    async def _ensure_loaded(self) -> Result[None, str]:
        if self._collections is not None:
            return Ok(None)
        return await self._load()

    async def _load(self) -> Result[None, str]:
        result = await self._pb.collections.get_full_list()
        if isinstance(result, Err):
            return Err(result.err_value.original_message)
        self._collections = {c.name: c for c in result.ok_value}
        # Also index by id for lookups
        for c in result.ok_value:
            if c.id:
                self._collections[c.id] = c
        return Ok(None)

    def invalidate(self) -> None:
        self._collections = None

    async def refresh(self) -> Result[None, str]:
        self._collections = None
        return await self._load()

    async def all_collections(self) -> Result[list["Collection"], str]:
        r = await self._ensure_loaded()
        if isinstance(r, Err):
            return r
        seen: set[str] = set()
        unique: list[Collection] = []
        for c in (self._collections or {}).values():
            if c.name not in seen:
                seen.add(c.name)
                unique.append(c)
        return Ok(unique)

    async def get_collection(self, name_or_id: str) -> Result["Collection", str]:
        r = await self._ensure_loaded()
        if isinstance(r, Err):
            return r
        col = (self._collections or {}).get(name_or_id)
        if col is None:
            return Err(f"Unknown collection '{name_or_id}'.")
        return Ok(col)

    async def get_fields(self, name_or_id: str) -> Result[list[Any], str]:
        r = await self.get_collection(name_or_id)
        if isinstance(r, Err):
            return r
        return Ok(r.ok_value.fields)


def validate_payload(
    fields: list[Any],
    data: dict[str, Any],
    action: Literal["create", "update"],
) -> list[str]:
    """Return validation error messages. Empty list = valid."""
    errors: list[str] = []
    field_map = {f.name: f for f in fields}
    # `id`/`created`/`updated`/`collectionId`/`collectionName` are always-present
    # system columns; `passwordConfirm`/`oldPassword` are write-only inputs that
    # PocketBase requires on auth-collection record writes but never exposes as
    # schema fields, so a strict field check would wrongly reject them.
    system_fields = {
        "id",
        "created",
        "updated",
        "collectionId",
        "collectionName",
        "passwordConfirm",
        "oldPassword",
    }

    unknown = [k for k in data if k not in field_map and k not in system_fields]
    if unknown:
        known = sorted(field_map.keys())
        errors.append(
            f"Unknown field(s): {', '.join(unknown)}. "
            f"Known fields: {', '.join(known)}. "
            f"Use describe_collection for full details."
        )

    if action == "create":
        missing = [
            f.name
            for f in fields
            if getattr(f, "required", False)
            and f.name not in data
            and not getattr(f, "system", False)
        ]
        if missing:
            errors.append(
                f"Missing required field(s) for create: {', '.join(missing)}."
            )

    return errors
