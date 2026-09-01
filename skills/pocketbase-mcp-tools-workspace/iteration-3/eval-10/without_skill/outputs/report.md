# Challenges Report — web/pwn, dynamic, score 300–549

## (a) Final answer

Challenges in category **Web** or **Pwn**, `is_dynamic = true`, `score >= 300` and `score < 550`,
sorted by score (high → low) then name (A–Z):

| # | Name | Category | Score |
|---|------|----------|-------|
| 1 | CEO | Web | 500 |
| 2 | Cyber Cafe | Web | 500 |
| 3 | I Own You | Pwn | 500 |
| 4 | The Great Pivot | Pwn | 500 |
| 5 | The Last Resolver | Pwn | 500 |
| 6 | The Matrix | Pwn | 500 |
| 7 | Broke guy | Web | 498 |

7 matching challenges.

Note: `category` is a relation field. The stored relation ids are `web` and `pwn`, which map to
display names `Web` and `Pwn` in the `challenge_categories` collection.

## (b) MCP calls made

1. **mcp__pocketbase__connect**
   - Arguments: `{ "as_": "status" }`
   - Response: OK — already authenticated as `superuser:mrrtou@protonmail.com`.

2. **mcp__pocketbase__describe_collection**
   - Arguments: `{ "collection": "challenges" }`
   - Response: OK — schema returned. Relevant fields: `name` (text), `category` (relation -> `pbc_1473151097`), `is_dynamic` (bool), `score` (number).

3. **mcp__pocketbase__find_records**
   - Arguments: `{ "collection": "pbc_1473151097", "fetch_all": true }`
   - Response: OK — 7 category records. `web` -> "Web", `pwn` -> "Pwn" (plus rev, teamwork, osint, crypto, forensics).

4. **mcp__pocketbase__find_records**
   - Arguments: `{ "collection": "challenges", "filter_template": "(category = {:c1} || category = {:c2}) && is_dynamic = true && score >= {:lo} && score < {:hi}", "filter_params": { "c1": "web", "c2": "pwn", "lo": 300, "hi": 550 }, "sort": "-score,name", "fields": "name,category,score,is_dynamic", "fetch_all": true }`
   - Response: ERROR — validation error: response records missing required `id` field (projection excluded `id`).

5. **mcp__pocketbase__find_records**
   - Arguments: `{ "collection": "challenges", "filter_template": "(category = {:c1} || category = {:c2}) && is_dynamic = true && score >= {:lo} && score < {:hi}", "filter_params": { "c1": "web", "c2": "pwn", "lo": 300, "hi": 550 }, "sort": "-score,name", "fields": "id,name,category,score,is_dynamic", "fetch_all": true }`
   - Response: OK — 7 records returned (CEO, Cyber Cafe, I Own You, The Great Pivot, The Last Resolver, The Matrix @ 500; Broke guy @ 498).
