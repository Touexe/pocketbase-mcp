# mcpskill_bulkmix atomic bulk write

## (a) Final answer

Done. All three changes were applied as a single atomic `bulk_write` transaction
against the `mcpskill_bulkmix` collection (`pbc_2933128039`):

- Created **Batch A** — 20 points, difficulty `easy`, active `true` (id `9htob36ksopad8w`)
- Created **Batch B** — 30 points, difficulty `easy`, active `true` (id `29wm977lf375bz7`)
- Updated **Seed One** (id `cj5acn1uptr565n`) — points changed from 10 to **99**

All operations returned status 200; nothing was left partially applied.

## (b) Ordered list of mcp__pocketbase__* tool calls

1. `mcp__pocketbase__connect` — args: `{ as_: "status" }`
   Response: ok; current identity `superuser:mrrtou@protonmail.com`, no startup auth error.

2. `mcp__pocketbase__describe_collection` — args: `{ collection: "mcpskill_bulkmix" }`
   Response: ok; base collection `pbc_2933128039` with fields `id` (text, required),
   `title` (text, required), `difficulty` (select: easy/medium/hard), `points` (number),
   `active` (bool); all API rules null (superuser-only).

3. `mcp__pocketbase__find_records` — args: `{ collection: "mcpskill_bulkmix",
   filter_template: "title = {:t}", filter_params: { t: "Seed One" } }`
   Response: ok; 1 record — id `cj5acn1uptr565n`, points 10, difficulty easy, active true.

4. `mcp__pocketbase__bulk_write` — args: `{ operations: [
   { collection: "mcpskill_bulkmix", action: "create", data: { title: "Batch A", points: 20, difficulty: "easy", active: true } },
   { collection: "mcpskill_bulkmix", action: "create", data: { title: "Batch B", points: 30, difficulty: "easy", active: true } },
   { collection: "mcpskill_bulkmix", action: "update", record_id: "cj5acn1uptr565n", data: { points: 99 } }
   ] }`
   Response: ok; count 3 — all results status 200. Created Batch A (`9htob36ksopad8w`),
   Batch B (`29wm977lf375bz7`); Seed One (`cj5acn1uptr565n`) now points 99.
