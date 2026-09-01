# team_challenges: solved first-bloods on hard challenges before 2026-08-16 03:00 UTC

## (a) Final answer

Filters applied: `is_solved = true`, `is_first_blood = true`, linked `challenge.difficulty = "hard"`, `solved_at < 2026-08-16 03:00:00 UTC`.
10 entries match, ordered by solve time (earliest first):

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

1. `mcp__pocketbase__connect(as_="status")`
   -> ok; already authenticated as `superuser:mrrtou@protonmail.com`.

2. `mcp__pocketbase__describe_collection(collection="team_challenges")`
   -> ok; fields include `is_solved` (bool), `is_first_blood` (bool), `solved_at` (date), `team` relation -> `pbc_1568971955`, `challenge` relation -> `pbc_4177893232`.

3. `mcp__pocketbase__describe_collection(collection="pbc_4177893232")`
   -> ok; collection `challenges`; has `name` (text) and `difficulty` (select: very_easy/easy/medium/hard).

4. `mcp__pocketbase__describe_collection(collection="pbc_1568971955")`
   -> ok; collection `teams`; has `name` (text).

5. `mcp__pocketbase__find_records(collection="team_challenges", filter_template="is_solved = true && is_first_blood = true && challenge.difficulty = {:d} && solved_at < {:t} && solved_at != \"\"", filter_params={"d": "hard", "t": "2026-08-16 03:00:00.000Z"}, expand="team,challenge", sort="solved_at", fetch_all=true, fields="id,solved_at,is_solved,is_first_blood,expand.team.name,expand.challenge.name,expand.challenge.difficulty")`
   -> ok; total=10 records returned, already sorted ascending by `solved_at` (see table above).
