# mcpskill_read — Active Challenges by Points (desc)

## (a) Final answer

Active challenges in the `mcpskill_read` collection (`active = true`), sorted by points highest to lowest:

1. Buffer Overflow — 500
2. Crypto Basics — 300
3. XSS Warmup — 150
4. SQL Injection 101 — 100

4 active challenges total.

## (b) Ordered list of mcp__pocketbase__* tool calls

1. `mcp__pocketbase__connect`
   - Arguments: `{ "as_": "status" }`
   - Response: `ok:true` — current identity `superuser:mrrtou@protonmail.com`, `startup_auth_error: null`.

2. `mcp__pocketbase__describe_collection`
   - Arguments: `{ "collection": "mcpskill_read" }`
   - Response: `ok:true` — base collection `pbc_854431867`; fields: `id` (text, required), `title` (text, required), `difficulty` (select: easy/medium/hard), `points` (number), `active` (bool); all API rules `null`.

3. `mcp__pocketbase__find_records`
   - Arguments: `{ "collection": "mcpskill_read", "filter_template": "active = {:a}", "filter_params": { "a": true }, "sort": "-points", "fetch_all": true }`
   - Response: `ok:true` — `total: 4`: Buffer Overflow (500, hard), Crypto Basics (300, medium), XSS Warmup (150, easy), SQL Injection 101 (100, easy).
