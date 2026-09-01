# Report: Add 5 Pwn challenges to `mcpskill_bulk`

## (a) Final answer

All 5 challenges were added to the `mcpskill_bulk` collection in a single atomic batch
via `mcp__pocketbase__bulk_write` (one call, 5 create operations). All returned HTTP 200
and all are `active: true`. Verified afterward with `find_records`.

| Title | Points | Difficulty | Active | Record ID |
|-------|--------|------------|--------|-----------|
| Pwn 1 | 100 | easy   | true | 47735zem81bbeks |
| Pwn 2 | 200 | medium | true | 0ha8p5p5bt9spy4 |
| Pwn 3 | 300 | medium | true | ouqfi2ulevar7z2 |
| Pwn 4 | 400 | hard   | true | zilp0ohf0wljk5j |
| Pwn 5 | 500 | hard   | true | zitxsyw3sc6odxb |

Note: the separate `ctf-pb` MCP server failed to connect (502) this session, but the
`mcp__pocketbase__*` tools were connected (authenticated as superuser:mrrtou@protonmail.com)
and were used for all operations.

## (b) Ordered list of `mcp__pocketbase__*` tool calls

1. `mcp__pocketbase__connect(as_="status")`
   -> ok; identity = `superuser:mrrtou@protonmail.com`, no startup auth error.

2. `mcp__pocketbase__describe_collection(collection="mcpskill_bulk")`
   -> ok; base collection `pbc_1539510088`, fields: `id` (text, req), `title` (text, req),
   `difficulty` (select: easy/medium/hard), `points` (number), `active` (bool). All API rules null (open).

3. `mcp__pocketbase__bulk_write(operations=[`
   `{collection:"mcpskill_bulk", action:"create", data:{title:"Pwn 1", points:100, difficulty:"easy",   active:true}},`
   `{collection:"mcpskill_bulk", action:"create", data:{title:"Pwn 2", points:200, difficulty:"medium", active:true}},`
   `{collection:"mcpskill_bulk", action:"create", data:{title:"Pwn 3", points:300, difficulty:"medium", active:true}},`
   `{collection:"mcpskill_bulk", action:"create", data:{title:"Pwn 4", points:400, difficulty:"hard",   active:true}},`
   `{collection:"mcpskill_bulk", action:"create", data:{title:"Pwn 5", points:500, difficulty:"hard",   active:true}}])`
   -> ok; count=5, all results status 200. IDs: 47735zem81bbeks, 0ha8p5p5bt9spy4, ouqfi2ulevar7z2, zilp0ohf0wljk5j, zitxsyw3sc6odxb.

4. `mcp__pocketbase__find_records(collection="mcpskill_bulk", filter_template="title ~ {:t}", filter_params={t:"Pwn"}, sort="points")`
   -> ok; total_items=5; all 5 Pwn records present with correct points/difficulty and `active:true`.
