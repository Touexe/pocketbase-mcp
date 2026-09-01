# team_challenges — solved hard first bloods before 2026-08-16 03:00 UTC

## (a) Final answer

Filter: `is_solved = true && is_first_blood = true && challenge.difficulty = "hard" && solved_at != "" && solved_at < "2026-08-16 03:00:00"`, ordered by `solved_at` ascending. 10 matching entries.

| # | Solve time (UTC) | Team name | Challenge name |
|---|------------------|-----------|----------------|
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

## (b) mcp__pocketbase__* calls

1. `mcp__pocketbase__connect(as_="status")`
   -> ok; identity `superuser:mrrtou@protonmail.com`, no startup auth error.

2. `mcp__pocketbase__describe_schema()`
   -> ok; 29 collections listed, including `team_challenges`, `challenges`, `teams`.

3. `mcp__pocketbase__describe_collection(collection="team_challenges")`
   -> ok; fields include `is_solved` (bool), `is_first_blood` (bool), `solved_at` (date), `challenge` (relation -> challenges), `team` (relation -> teams).

4. `mcp__pocketbase__describe_collection(collection="challenges")`
   -> ok; fields include `name` (text), `difficulty` (select: very_easy/easy/medium/hard).

5. `mcp__pocketbase__describe_collection(collection="teams")`
   -> ok; fields include `name` (text).

6. `mcp__pocketbase__find_records(collection="team_challenges", filter_template="is_solved = {:s} && is_first_blood = {:s} && challenge.difficulty = {:d} && solved_at != {:e} && solved_at < {:t}", filter_params={"s": true, "d": "hard", "e": "", "t": "2026-08-16 03:00:00"}, expand="challenge,team", sort="solved_at", fields="id,solved_at,is_solved,is_first_blood,expand.challenge.name,expand.challenge.difficulty,expand.team.name", fetch_all=true)`
   -> ok; 10 records returned, ordered earliest-first (2026-08-16 01:48:49 to 02:53:06), all challenge difficulty `hard`.
