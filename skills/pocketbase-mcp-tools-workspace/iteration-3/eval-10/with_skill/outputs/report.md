# Challenges: web/pwn, dynamic, score 300–549

## Final answer

Filter: category in (web, pwn) AND is_dynamic = true AND score >= 300 AND score < 550.
Sorted by score (high to low), then name (A–Z). 7 matches.

| # | Name | Category | Score |
|---|------|----------|-------|
| 1 | CEO | web | 500 |
| 2 | Cyber Cafe | web | 500 |
| 3 | I Own You | pwn | 500 |
| 4 | The Great Pivot | pwn | 500 |
| 5 | The Last Resolver | pwn | 500 |
| 6 | The Matrix | pwn | 500 |
| 7 | Broke guy | web | 498 |

Note: `category` is a relation whose record ids are slugs (`web` = "Web", `pwn` = "Pwn").

## MCP calls made

1. `mcp__pocketbase__connect(as_="status")`
   -> ok; identity `superuser:mrrtou@protonmail.com`, no startup auth error.

2. `mcp__pocketbase__describe_collection(collection="challenges")`
   -> ok; fields include `name` (text), `category` (relation -> pbc_1473151097), `is_dynamic` (bool), `score` (number). List/view API rules are open.

3. `mcp__pocketbase__describe_collection(collection="pbc_1473151097")`
   -> ok; collection `challenge_categories` with fields `id` (text), `name` (text).

4. `mcp__pocketbase__find_records(collection="challenge_categories", filter_template="name = {:a} || name = {:b}", filter_params={"a": "web", "b": "pwn"})`
   -> ok; 0 records (the `name` field holds "Web"/"Pwn", not the slugs).

5. `mcp__pocketbase__find_records(collection="challenge_categories", fetch_all=true)`
   -> ok; 7 categories. Relevant ids: `web` (name "Web"), `pwn` (name "Pwn").

6. `mcp__pocketbase__find_records(collection="challenges", filter_template="(category = {:c1} || category = {:c2}) && is_dynamic = {:d} && score >= {:lo} && score < {:hi}", filter_params={"c1": "web", "c2": "pwn", "d": true, "lo": 300, "hi": 550}, sort="-score,name", fields="id,name,category,score,is_dynamic", fetch_all=true)`
   -> ok; 7 records returned in final sorted order (CEO, Cyber Cafe, I Own You, The Great Pivot, The Last Resolver, The Matrix — all score 500; Broke guy — score 498).
