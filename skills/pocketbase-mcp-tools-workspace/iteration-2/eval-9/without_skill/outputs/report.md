# team_challenges — Hard first-blood solves before 2026-08-16 03:00 UTC

## (a) Final answer

Entries in `team_challenges` where `is_solved = true`, `is_first_blood = true`, the linked
challenge's `difficulty = "hard"`, and `solved_at` is before 2026-08-16 03:00:00 UTC.
Ordered by solve time, earliest first (10 results):

| # | Solve time (UTC) | Team | Challenge |
|---|------------------|------|-----------|
| 1 | 2026-08-16 01:48:49 | ACCD | Never Busy for You |
| 2 | 2026-08-16 01:49:12 | AmbokOps | Behind |
| 3 | 2026-08-16 01:53:24 | NO NAME | Cyber Cafe |
| 4 | 2026-08-16 01:54:10 | Little Cannon | The Machine |
| 5 | 2026-08-16 01:56:24 | NO NAME | Electric cut |
| 6 | 2026-08-16 02:01:23 | R0mdu0l$3nCh3y | Daily |
| 7 | 2026-08-16 02:04:23 | R0mdu0l$3nCh3y | The Great Pivot |
| 8 | 2026-08-16 02:05:31 | Hort Mes | Forged Alliance |
| 9 | 2026-08-16 02:07:42 | DF4 | Three Sessions, One Intruder |
| 10 | 2026-08-16 02:53:06 | យុវជនប្រាក់រៀល | The Matrix |

## (b) MCP calls made

1. `mcp__pocketbase__inspect_server()`
   - Response: server healthy (app "Acme"), 4 cron jobs, log stats returned. Confirmed connectivity.

2. `mcp__pocketbase__describe_collection(collection="team_challenges")`
   - Response: base collection `pbc_1461729463`; relevant fields — `is_solved` (bool), `is_first_blood` (bool), `solved_at` (date), `team` -> `pbc_1568971955`, `challenge` -> `pbc_4177893232`.

3. `mcp__pocketbase__describe_collection(collection="pbc_4177893232")`
   - Response: collection `challenges`; has `name` (text) and `difficulty` (select: very_easy, easy, medium, hard).

4. `mcp__pocketbase__describe_collection(collection="pbc_1568971955")`
   - Response: collection `teams`; has `name` (text).

5. `mcp__pocketbase__find_records(collection="team_challenges", filter_template='is_solved = true && is_first_blood = true && challenge.difficulty = {:d} && solved_at < {:t} && solved_at != ""', filter_params={"d": "hard", "t": "2026-08-16 03:00:00.000Z"}, sort="solved_at", expand="team,challenge", fetch_all=true)`
   - Response: 10 matching records (total=10), each expanded with team + challenge; used to build the table above.
