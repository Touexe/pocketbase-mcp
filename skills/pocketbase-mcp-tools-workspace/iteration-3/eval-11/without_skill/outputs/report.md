# Submissions Collection Analysis

## (a) Final Answer

- **Total submissions:** 3,703
  - **Correct:** 539
  - **Incorrect:** 3,164
- **Player with the most incorrect flags:** **ANG OUSA** (player id `hg2u4hwlcs8d3d9`, ctfd_id 197, angousa168@gmail.com)
  - **Incorrect count:** **156**

Runners-up for context: `881o2k8iclag0yh` (148), `beumc0obomj5y28` (115), `a2jyq5ccppq95qx` (90).
All 3,164 incorrect submissions had a non-empty `submitted_by` value.

## (b) Ordered list of mcp__pocketbase__* calls

1. **mcp__pocketbase__connect** - args: `{as_: "status"}`
   Response: OK. Already authenticated as `superuser:mrrtou@protonmail.com`.

2. **mcp__pocketbase__describe_collection** - args: `{collection: "submissions"}`
   Response: OK. Base collection `pbc_3482339971`; fields include `status` (select: correct/incorrect), `submitted_flag`, `submitted_by` (relation -> players `pbc_3072146508`), `team_challenge`, `cheating`, `created`, `updated`.

3. **mcp__pocketbase__find_records** - args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "correct"}, per_page: 1}`
   Response: OK. `total_items: 539` (correct submissions).

4. **mcp__pocketbase__find_records** - args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "incorrect"}, per_page: 1}`
   Response: OK. `total_items: 3164` (incorrect submissions).

5. **mcp__pocketbase__find_records** - args: `{collection: "pbc_3072146508", per_page: 1}`
   Response: OK. `players` collection, `total_items: 122`.

6. **mcp__pocketbase__find_records** - args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "incorrect"}, fields: "submitted_by", fetch_all: true}`
   Response: ERROR (validation) - projection without `id` failed pydantic validation (`items.N.id Field required`). No usable data. Returned a large truncated error payload (~27k chars of repeated validation errors).

7. **mcp__pocketbase__find_records** - args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "incorrect"}, fields: "id,submitted_by", per_page: 800, page: 1}`
   Response: TOO MUCH DATA - 113,752 characters, exceeded max tokens; output saved to a tool-results file. Not used directly.

8. **mcp__pocketbase__find_records** - args: `{collection: "submissions", filter_template: "status = {:s}", filter_params: {s: "incorrect"}, fields: "id,submitted_by", fetch_all: true}`
   Response: TOO MUCH DATA - 449,333 characters, exceeded max tokens; output saved to tool-results file `mcp-pocketbase-find_records-1788247487178.txt`. Processed offline with `jq` + `sort | uniq -c`: 3,164 records, 0 empty `submitted_by`. Top counts: `hg2u4hwlcs8d3d9`=156, `881o2k8iclag0yh`=148, `beumc0obomj5y28`=115, `a2jyq5ccppq95qx`=90, `7q6q3utfie97z3i`=81.

9. **mcp__pocketbase__find_records** - args: `{collection: "pbc_3072146508", record_id: "hg2u4hwlcs8d3d9", fields: "id,name,email,ctfd_id"}`
   Response: OK. `name: "ANG OUSA"`, `ctfd_id: 197`, `email: angousa168@gmail.com`.

### Notes on oversized calls
- Call 6 returned a large truncated validation-error payload.
- Call 7 returned 113,752 chars (saved to file, exceeded token limit).
- Call 8 returned 449,333 chars (saved to file, exceeded token limit); aggregation was done locally via `jq` against the saved file.
