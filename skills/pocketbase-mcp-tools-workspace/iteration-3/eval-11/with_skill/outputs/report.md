# Submissions analysis — correct vs incorrect, top incorrect submitter

## (a) Final answer

Across the whole `submissions` collection (3,703 records total):

- **Correct: 539**
- **Incorrect: 3,164**

Single player with the most incorrect flag submissions:

- **Name: ANG OUSA** (player id `hg2u4hwlcs8d3d9`, email `angousa168@gmail.com`)
- **Incorrect count: 156**

Runner-up for context: player id `881o2k8iclag0yh` with 148 incorrect.

Method: fetched every incorrect submission projected to `id,submitted_by`
(3,164 rows, 0 with an empty/null `submitted_by`, 108 distinct players),
tallied per player client-side, then resolved the winning id to a name.
Correct/incorrect totals cross-checked against the `_submission_stats` view
(correct_count 539, incorrect_count 3164, total 3703).

## (b) Ordered list of mcp__pocketbase__* calls

1. **mcp__pocketbase__describe_schema** `{}`
   - OK. 29 collections. Noted `submissions` (base) and a `_submission_stats` view.

2. **mcp__pocketbase__describe_collection** `{"collection": "submissions"}`
   - OK. Fields: `id`, `status` (select: correct/incorrect), `submitted_flag`,
     `team_challenge` (rel), `cheating` (rel), `submitted_by` (rel -> players),
     `created`, `updated`.

3. **mcp__pocketbase__describe_collection** `{"collection": "_submission_stats"}`
   - OK. View fields: `total_submissions`, `correct_count`, `incorrect_count`,
     `correct_percent`, `incorrect_percent`, `cheat_linked`.

4. **mcp__pocketbase__find_records** `{"collection": "_submission_stats", "fetch_all": true}`
   - OK. 1 row: correct_count 539, incorrect_count 3164, total_submissions 3703,
     cheat_linked 3, incorrect_percent 85.44.

5. **mcp__pocketbase__find_records** `{"collection": "submissions", "filter_template": "status = {:s}", "filter_params": {"s": "correct"}, "per_page": 1, "fields": "id"}`
   - OK. `total_items` = 539 (confirms correct count).

6. **mcp__pocketbase__find_records** `{"collection": "submissions", "filter_template": "status = {:s}", "filter_params": {"s": "incorrect"}, "per_page": 1, "fields": "id"}`
   - OK. `total_items` = 3164 (confirms incorrect count).

7. **mcp__pocketbase__describe_collection** `{"collection": "_players_attempts"}`
   - OK. View with per-player/per-challenge `attempts`; not used (semantics ambiguous, went to raw submissions instead).

8. **mcp__pocketbase__describe_collection** `{"collection": "players"}`
   - OK. Fields: `id`, `ctfd_id`, `email`, `name`, `affiliation`, ...

9. **mcp__pocketbase__find_records** `{"collection": "submissions", "filter_template": "status = {:s}", "filter_params": {"s": "incorrect"}, "fields": "id,submitted_by", "per_page": 500, "page": 1}`
   - **RETURNED TOO MUCH DATA** — 71,152 chars, exceeded the tool's max token limit; output saved to a file. Retried with smaller pages.

10. **mcp__pocketbase__find_records** `{"collection": "submissions", "filter_template": "status = {:s}", "filter_params": {"s": "incorrect"}, "fields": "id,submitted_by", "per_page": 200, "page": 1}`
    - OK (partial). 200 of 3164 rows, 16 total pages. Used to sanity-check shape; full tally done via next call.

11. **mcp__pocketbase__find_records** `{"collection": "submissions", "filter_template": "status = {:s}", "filter_params": {"s": "incorrect"}, "fields": "id,submitted_by", "fetch_all": true}`
    - **RETURNED TOO MUCH DATA** — 449,333 chars, exceeded max tokens; output saved to
      `tool-results/mcp-pocketbase-find_records-1788247522211.txt` (3,164 records).
      Processed offline with `jq`: tallied `submitted_by`, top = `hg2u4hwlcs8d3d9` (156),
      then `881o2k8iclag0yh` (148); 0 empty `submitted_by`; counts sum to 3164; 108 distinct players.

12. **mcp__pocketbase__find_records** `{"collection": "players", "record_id": "hg2u4hwlcs8d3d9", "fields": "id,name,email,affiliation"}`
    - OK. name = "ANG OUSA", email = "angousa168@gmail.com", affiliation = "".

### Calls that returned too much data
- Call 9 (`per_page: 500`) — exceeded max tokens, saved to file.
- Call 11 (`fetch_all: true`) — exceeded max tokens, saved to file; used for the client-side tally.
