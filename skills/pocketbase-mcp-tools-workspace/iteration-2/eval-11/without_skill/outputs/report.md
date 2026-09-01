# Submissions analysis (PocketBase `submissions` collection)

## Final answer

- **Total submissions:** 3703
- **Correct:** 539
- **Incorrect:** 3164
- **Player with the most incorrect flags:** **ANG OUSA** (player id `hg2u4hwlcs8d3d9`, ctfd_id 197, angousa168@gmail.com)
- **Their incorrect count:** **156**

Top 5 incorrect-flag submitters for context:

| Rank | Player id | Incorrect count |
|---|---|---|
| 1 | hg2u4hwlcs8d3d9 (ANG OUSA) | 156 |
| 2 | 881o2k8iclag0yh | 148 |
| 3 | beumc0obomj5y28 | 115 |
| 4 | a2jyq5ccppq95qx | 90 |
| 5 | 7q6q3utfie97z3i | 81 |

Method: counted `status` totals via `total_items` on filtered queries, then pulled every
incorrect submission's `id` + `submitted_by` (paged, 500/page), de-duplicated by `id`
(3164 unique), grouped by `submitted_by`, and resolved the top id against the `players` collection.

## Ordered list of `mcp__pocketbase__*` calls

1. **`connect`** — args: `{as_: "status"}` — Response: OK; already authenticated as `superuser:mrrtou@protonmail.com`.
2. **`describe_collection`** — args: `{collection: "submissions"}` — Response: OK; base collection, fields include `status` (select: correct/incorrect) and `submitted_by` (relation -> `pbc_3072146508` / players).
3. **`find_records`** — args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "correct"}, per_page: 1}` — Response: OK; `total_items = 539` (correct submissions).
4. **`find_records`** — args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "incorrect"}, per_page: 1}` — Response: OK; `total_items = 3164` (incorrect submissions).
5. **`describe_collection`** — args: `{collection: "pbc_3072146508"}` — Response: OK; collection `players`, fields include `name`, `email`, `ctfd_id`.
6. **`find_records`** — args: `{collection: "players", per_page: 1}` — Response: OK; `total_items = 122` players.
7. **`find_records`** — args: `{collection: "submissions", filter: status=incorrect, fields: "submitted_by", per_page: 500, page: 1, sort: "id"}` — Response: ERROR (client-side validation: records require `id`; projection without `id` rejected). No usable data.
8. **`find_records`** — args: `{collection: "submissions", filter: status=incorrect, fields: "id,submitted_by", per_page: 500, page: 1, sort: "id"}` — Response: **TOO MUCH DATA** — 71,152 chars, exceeded token limit; saved to `tool-results/...-1788246548397.txt` (500 records). Used via jq.
9. **`find_records`** — same as #8, `page: 2` — Response: **TOO MUCH DATA**; saved to `...-1788246557782.txt` (500 records).
10. **`find_records`** — same, `page: 3` — Response: **TOO MUCH DATA**; saved to `...-1788246561043.txt` (500 records).
11. **`find_records`** — same, `page: 4` — Response: **TOO MUCH DATA**; saved to `...-1788246566269.txt` (500 records).
12. **`find_records`** — same, `page: 5` — Response: **TOO MUCH DATA**; saved to `...-1788246569789.txt` (500 records).
13. **`find_records`** — same, `page: 6` — Response: **TOO MUCH DATA**; saved to `...-1788246573079.txt` (500 records).
14. **`find_records`** — same, `page: 7` — Response: returned inline OK (164 records, page 7 of 7 = records 3001-3164).
15. **`find_records`** — args: `{collection: "submissions", filter: status=incorrect, fields: "id,submitted_by", per_page: 3200, page: 1, sort: "id"}` — Response: **TOO MUCH DATA** — 142,153 chars; saved to `...-1788246617203.txt`. Note: server capped `per_page` at 1000, so this file held only 1000 of 3164 records (incomplete on its own; NOT used for the final tally).
16. **`find_records`** — args: `{collection: "submissions", filter: status=incorrect, per_page: 500, page: 7, sort: "id"}` (no field projection, full records) — Response: **TOO MUCH DATA** — 62,467 chars; saved to `...-1788246650731.txt` (164 records). Used to get page 7 into a file for jq.
17. **`find_records`** — args: `{collection: "players", record_id: "hg2u4hwlcs8d3d9"}` — Response: OK; `name = "ANG OUSA"`, ctfd_id 197, email angousa168@gmail.com.
18. **`find_records`** — args: `{collection: "submissions", per_page: 1}` — Response: OK; `total_items = 3703` (sanity check: 539 + 3164 = 3703).

### Local processing (not MCP calls)

- Combined the 6 saved page files (pages 1-6, 500 each) plus the page-7 file (164) with `jq -s`, de-duplicated by record `id` -> exactly **3164** unique incorrect submissions (101 distinct submitters).
- Grouped by `submitted_by`: max is `hg2u4hwlcs8d3d9` with **156**; next `881o2k8iclag0yh` with 148.

### Notes on oversized responses

Every attempt to page the incorrect submissions at 500 records/page (with or without field
projection) exceeded the tool's token limit and was written to a file under `tool-results/`
instead of returned inline (calls #8-13, #16). Only the final 164-record page 7 fit inline
when projected (call #14). The `per_page=3200` request (call #15) was silently capped to
1000 by the server, which would have caused undercounting if used directly; it was discarded
in favour of the complete 7-page set.
