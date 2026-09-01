# Submissions analysis report

## (a) Final answer

- **Correct submissions:** 539 (14.56%)
- **Incorrect submissions:** 3164 (85.44%)
- **Total submissions:** 3703
- **Player with the most incorrect flags:** **ANG OUSA** (player id `hg2u4hwlcs8d3d9`, email `angousa168@gmail.com`)
- **Their incorrect count:** **156**

Top 5 incorrect submitters for context:

| Rank | Player id | Incorrect count |
|---|---|---|
| 1 | hg2u4hwlcs8d3d9 (ANG OUSA) | 156 |
| 2 | 881o2k8iclag0yh | 148 |
| 3 | beumc0obomj5y28 | 115 |
| 4 | a2jyq5ccppq95qx | 90 |
| 5 | 7q6q3utfie97z3i | 81 |

## (b) Ordered list of mcp__pocketbase__* calls

1. `connect(as_="status")`
   - Response: identity `superuser:mrrtou@protonmail.com`, no startup auth error. Already authenticated as superuser.

2. `describe_collection(collection="submissions")`
   - Response: base collection `pbc_3482339971`. Fields: `id`, `status` (select: correct|incorrect, required), `submitted_flag`, `team_challenge` (relation), `cheating` (relation), `submitted_by` (relation -> players `pbc_3072146508`), `created`, `updated`.

3. `describe_schema()`
   - Response: 29 collections. Noted `players` (`pbc_3072146508`) and a view `_submission_stats` (`pbc_3757750218`).

4. `describe_collection(collection="_submission_stats")`
   - Response: view with fields `id`, `total_submissions`, `correct_count`, `incorrect_count`, `correct_percent`, `incorrect_percent`, `cheat_linked`.

5. `describe_collection(collection="players")`
   - Response: base collection `pbc_3072146508`. Fields: `id`, `ctfd_id` (number, required, unique), `email` (required), `name` (text, required), `affiliation`, `password`, `created`, `updated`.

6. `find_records(collection="submissions", filter_template="status = {:s}", filter_params={"s": "correct"}, per_page=1, fields="id")`
   - Response: `total_items` = 539.

7. `find_records(collection="submissions", filter_template="status = {:s}", filter_params={"s": "incorrect"}, per_page=1, fields="id")`
   - Response: `total_items` = 3164.

8. `find_records(collection="_submission_stats", fetch_all=True)`
   - Response: single row -> `total_submissions` 3703, `correct_count` 539, `incorrect_count` 3164, `correct_percent` 14.56, `incorrect_percent` 85.44, `cheat_linked` 3. Confirms counts from calls 6-7.

9. `find_records(collection="players", per_page=1, fields="id")`
   - Response: `total_items` = 122 players. (Used to decide against a per-player loop.)

10. `find_records(collection="submissions", filter_template="status = {:s}", filter_params={"s": "incorrect"}, fields="submitted_by", fetch_all=True)`
    - Response: FAILED - 200 pydantic validation errors: the tool requires `id` in the field projection. No usable data returned.

11. `find_records(collection="submissions", filter_template="status = {:s}", filter_params={"s": "incorrect"}, fields="id,submitted_by", fetch_all=True)`
    - Response: TOO MUCH DATA - result was 449,333 characters, exceeded max allowed tokens, and was spilled to a tool-results file. Aggregated offline with jq: 3164 records, 0 empty `submitted_by`. Top submitter `hg2u4hwlcs8d3d9` with 156, then `881o2k8iclag0yh` 148, `beumc0obomj5y28` 115, `a2jyq5ccppq95qx` 90, `7q6q3utfie97z3i` 81.

12. `find_records(collection="players", record_id="hg2u4hwlcs8d3d9", fields="id,name,email,affiliation")`
    - Response: `name` = "ANG OUSA", `email` = "angousa168@gmail.com", `affiliation` empty.

## Notes on oversized responses

- Call 10 failed validation (missing `id` in projection) - not a data-size issue but the projection must always include `id`.
- Call 11 returned too much data (449,333 chars) and was written to `tool-results/mcp-pocketbase-find_records-1788246545348.txt`. The per-player incorrect tally was computed from that file with `jq | sort | uniq -c`, and all 3164 rows were accounted for (no null/empty `submitted_by`).
