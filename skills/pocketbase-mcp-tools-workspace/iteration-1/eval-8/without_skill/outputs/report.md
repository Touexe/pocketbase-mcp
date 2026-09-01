# mcpskill_bulkmix atomic bulk write

## (a) Final answer

The atomic operation succeeded. Using a single `mcp__pocketbase__bulk_write` call
(one PocketBase batch transaction), these three operations were committed
together against the `mcpskill_bulkmix` collection:

1. Created **Batch A** - id `9pu0vxipky0e3rt`, points 20, difficulty `easy`, active `true`.
2. Created **Batch B** - id `07kpo8wkno86f0d`, points 30, difficulty `easy`, active `true`.
3. Updated **Seed One** - id `cj5acn1uptr565n`, points changed from 10 to **99**
   (difficulty `easy` and active `true` unchanged).

Note: the collection's name field is `title` (not `name`). Post-write
verification confirms 3 rows: Batch A (20), Batch B (30), Seed One (99).

## (b) Ordered list of mcp__pocketbase__* tool calls

1. `mcp__pocketbase__connect(as_="status")`
   - ok; identity `superuser:mrrtou@protonmail.com`, no startup auth error.

2. `mcp__pocketbase__describe_collection(collection="mcpskill_bulkmix")`
   - ok; base collection `pbc_2933128039`; fields: `id` (text), `title` (text, required),
     `difficulty` (select: easy/medium/hard), `points` (number), `active` (bool). API rules all null.

3. `mcp__pocketbase__find_records(collection="mcpskill_bulkmix", filter_template="name = {:n}", filter_params={"n":"Seed One"})`
   - failed - BAD_REQUEST_ERROR (400); `name` is not a valid field.

4. `mcp__pocketbase__find_records(collection="mcpskill_bulkmix", filter_template="title = {:n}", filter_params={"n":"Seed One"})`
   - ok; 1 record - id `cj5acn1uptr565n`, title "Seed One", points 10, difficulty easy, active true.

5. `mcp__pocketbase__bulk_write(operations=[
     {collection:"mcpskill_bulkmix", action:"create", data:{title:"Batch A", points:20, difficulty:"easy", active:true}},
     {collection:"mcpskill_bulkmix", action:"create", data:{title:"Batch B", points:30, difficulty:"easy", active:true}},
     {collection:"mcpskill_bulkmix", action:"update", record_id:"cj5acn1uptr565n", data:{points:99}}
   ])`
   - ok; count 3, all results status 200 - Batch A id `9pu0vxipky0e3rt` (20), Batch B id `07kpo8wkno86f0d` (30), Seed One id `cj5acn1uptr565n` (99).

6. `mcp__pocketbase__find_records(collection="mcpskill_bulkmix", sort="title")`
   - ok; 3 records total - Batch A (20, easy, active), Batch B (30, easy, active), Seed One (99, easy, active). Verification passed.
