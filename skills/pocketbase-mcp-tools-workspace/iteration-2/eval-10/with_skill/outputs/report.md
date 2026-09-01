# Challenges: web/pwn, dynamic, score 300-549

## Final answer

Filter: category in (web, pwn) AND `is_dynamic = true` AND `score >= 300` AND `score < 550`.
Sort: score descending, then name A-Z. 7 matches.

| # | Name | Category | Score |
|---|------|----------|-------|
| 1 | CEO | web | 500 |
| 2 | Cyber Cafe | web | 500 |
| 3 | I Own You | pwn | 500 |
| 4 | The Great Pivot | pwn | 500 |
| 5 | The Last Resolver | pwn | 500 |
| 6 | The Matrix | pwn | 500 |
| 7 | Broke guy | web | 498 |

Note: `category` is a relation to `challenge_categories`; the category record ids are `web` (display name "Web") and `pwn` (display name "Pwn").

## MCP calls made

1. `mcp__pocketbase__connect(as_="status")`
   -> ok; identity `superuser:mrrtou@protonmail.com`, no startup auth error.

2. `mcp__pocketbase__describe_collection(collection="challenges")`
   -> ok; fields include `name` (text), `score` (number), `is_dynamic` (bool), `category` (relation -> pbc_1473151097 / challenge_categories). Unique index on `name`.

3. `mcp__pocketbase__describe_collection(collection="pbc_1473151097")`
   -> ok; collection `challenge_categories` with fields `id`, `name`.

4. `mcp__pocketbase__find_records(collection="challenge_categories", filter_template="name = {:web} || name = {:pwn}", filter_params={"web": "web", "pwn": "pwn"})`
   -> ok; 0 records (stored names are capitalized "Web"/"Pwn").

5. `mcp__pocketbase__find_records(collection="challenge_categories", fetch_all=True)`
   -> ok; 7 categories. Relevant ids: `web` (name "Web"), `pwn` (name "Pwn").

6. `mcp__pocketbase__find_records(collection="challenges", filter_template="(category = {:web} || category = {:pwn}) && is_dynamic = {:dyn} && score >= {:lo} && score < {:hi}", filter_params={"web": "web", "pwn": "pwn", "dyn": true, "lo": 300, "hi": 550}, sort="-score,name", fields="name,category,score", fetch_all=True)`
   -> error; validation error (projection without `id` broke result parsing).

7. `mcp__pocketbase__find_records(collection="challenges", filter_template="(category = {:web} || category = {:pwn}) && is_dynamic = {:dyn} && score >= {:lo} && score < {:hi}", filter_params={"web": "web", "pwn": "pwn", "dyn": true, "lo": 300, "hi": 550}, sort="-score,name", fields="id,name,category,score", fetch_all=True)`
   -> ok; 7 records in final order: CEO, Cyber Cafe, I Own You, The Great Pivot, The Last Resolver, The Matrix (all 500), Broke guy (498).
