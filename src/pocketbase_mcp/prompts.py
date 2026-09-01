"""MCP prompt definitions."""

from __future__ import annotations

try:
    from fastmcp.prompts.prompt import Message
except ImportError:  # pragma: no cover
    from fastmcp import Message  # type: ignore[no-redef]


async def inspect_then_query(collection: str | None = None) -> list[Message]:
    """Guide an agent through schema inspection then record querying."""
    if collection is None:
        return [
            Message(
                role="user",
                content=(
                    "You need to query a PocketBase collection but are unsure which one to use.\n\n"
                    "Step 1: Call describe_schema to list all available collections.\n"
                    "Step 2: Choose the target collection from the results.\n"
                    "Step 3: Call describe_collection(collection=<name>) to learn the fields and types.\n"
                    "Step 4: Call find_records with an appropriate filter_template and filter_params "
                    "using only the field names returned in step 3."
                ),
            )
        ]
    return [
        Message(
            role="user",
            content=(
                f"You need to query records from the '{collection}' collection.\n\n"
                f"Step 1: Call describe_collection(collection='{collection}') to learn the fields and types.\n"
                "Step 2: Build your filter using only field names from step 1. "
                "Use filter_template with {:placeholder} syntax and pass values via filter_params.\n"
                f"Step 3: Call find_records(collection='{collection}', filter_template=..., filter_params=...) "
                "to retrieve matching records."
            ),
        )
    ]


async def safe_delete(collection: str, filter_description: str) -> list[Message]:
    """Guide an agent through count-verify-then-delete flow."""
    return [
        Message(
            role="user",
            content=(
                f"You need to delete records from '{collection}' matching: {filter_description}\n\n"
                "IMPORTANT: Deleting records is irreversible. Follow these steps exactly.\n\n"
                f"Step 1: Call describe_collection(collection='{collection}') to get the field names.\n"
                "Step 2: Call find_records with fetch_all=True and a filter matching your intent. "
                "Count the records returned — this is your confirm_count.\n"
                "Step 3: Review the list. Confirm the count and records match your intent before proceeding.\n"
                f"Step 4: Call delete_records(collection='{collection}', filter_template=..., "
                "filter_params=..., confirm_count=<count from step 2>). "
                "The confirm_count must exactly match the resolved count or the call will fail."
            ),
        )
    ]


async def create_with_validation(collection: str) -> list[Message]:
    """Guide an agent through schema-aware record creation."""
    return [
        Message(
            role="user",
            content=(
                f"You need to create a new record in '{collection}'.\n\n"
                f"Step 1: Call describe_collection(collection='{collection}') to get the field names, "
                "types, and which fields are required.\n"
                "Step 2: Build a data dict using ONLY field names returned in step 1. "
                "Do not include fields that were not in the schema — the call will fail validation.\n"
                "Step 3: Ensure all required fields are present in your data dict.\n"
                f"Step 4: Call write_record(collection='{collection}', action='create', data={{...}}) "
                "with the validated payload."
            ),
        )
    ]
