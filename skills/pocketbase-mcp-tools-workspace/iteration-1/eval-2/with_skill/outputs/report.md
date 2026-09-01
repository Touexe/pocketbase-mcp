# mcpskill_read — Highest-Point Challenge

## (a) Final answer

The single highest-point challenge in `mcpskill_read` is **"Buffer Overflow"** with **500 points**.

All of its field values:

| Field | Value |
|---|---|
| id | `j2h2tmum8emz9jg` |
| title | Buffer Overflow |
| difficulty | hard |
| points | 500 |
| active | true |
| collection_id | pbc_854431867 |
| collection_name | mcpskill_read |
| created | (empty) |
| updated | (empty) |
| expand | null |

The next highest is "Reversing Rust" at 450 points, so 500 is a clear single top value.

## (b) Ordered list of mcp__pocketbase__* tool calls

1. `mcp__pocketbase__describe_schema` — args: none.
   Response: listed 28 collections; confirmed `mcpskill_read` exists (id `pbc_854431867`, base, 5 fields).

2. `mcp__pocketbase__describe_collection` — args: `{ "collection": "mcpskill_read" }`.
   Response: fields = id (text, required), title (text, required), difficulty (select: easy/medium/hard), points (number), active (bool); all API rules public (null); no indexes.

3. `mcp__pocketbase__find_records` — args: `{ "collection": "mcpskill_read", "sort": "-points", "per_page": 5 }`.
   Response: 6 total items; top record "Buffer Overflow" (id `j2h2tmum8emz9jg`), points 500, difficulty hard, active true; next was "Reversing Rust" at 450.
