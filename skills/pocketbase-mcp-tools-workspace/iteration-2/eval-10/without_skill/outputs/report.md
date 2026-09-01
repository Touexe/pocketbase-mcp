# Challenges Report: web/pwn, dynamic, score 300–549

## Final Answer

Filter: category in {web, pwn}, `is_dynamic = true`, `300 <= score < 550`.
Sorted by score (high to low), then name (A–Z).

| # | Name | Category | Score |
|---|------|----------|-------|
| 1 | CEO | web | 500 |
| 2 | Cyber Cafe | web | 500 |
| 3 | I Own You | pwn | 500 |
| 4 | The Great Pivot | pwn | 500 |
| 5 | The Last Resolver | pwn | 500 |
| 6 | The Matrix | pwn | 500 |
| 7 | Broke guy | web | 498 |

7 challenges total.

Note: the `category` field is a relation; values shown are the category record IDs
(`web`, `pwn`), whose display names are "Web" and "Pwn".

## MCP Calls

1. **mcp__pocketbase__connect**
   - Arguments: `{ "as_": "status" }`
   - Response: Already authenticated as `superuser:mrrtou@protonmail.com`; no startup auth error.

2. **mcp__pocketbase__describe_collection**
   - Arguments: `{ "collection": "challenges" }`
   - Response: Base collection `challenges`. Relevant fields: `name` (text), `category`
     (relation -> pbc_1473151097), `is_dynamic` (bool), `score` (number).

3. **mcp__pocketbase__find_records**
   - Arguments: `{ "collection": "pbc_1473151097", "fetch_all": true }`
   - Response: 7 category records; relevant IDs -> names: `web` = "Web", `pwn` = "Pwn".

4. **mcp__pocketbase__find_records**
   - Arguments: `{ "collection": "challenges", "filter_template": "(category = {:c1} || category = {:c2}) && is_dynamic = {:dyn} && score >= {:lo} && score < {:hi}", "filter_params": { "c1": "web", "c2": "pwn", "dyn": true, "lo": 300, "hi": 550 }, "sort": "-score,name", "fetch_all": true, "fields": "name,category,score,is_dynamic" }`
   - Response: Validation error — projection omitted required `id` field; no data returned.

5. **mcp__pocketbase__find_records**
   - Arguments: `{ "collection": "challenges", "filter_template": "(category = {:c1} || category = {:c2}) && is_dynamic = {:dyn} && score >= {:lo} && score < {:hi}", "filter_params": { "c1": "web", "c2": "pwn", "dyn": true, "lo": 300, "hi": 550 }, "sort": "-score,name", "fetch_all": true, "fields": "id,name,category,score,is_dynamic" }`
   - Response: 7 records — CEO (web, 500), Cyber Cafe (web, 500), I Own You (pwn, 500), The Great Pivot (pwn, 500), The Last Resolver (pwn, 500), The Matrix (pwn, 500), Broke guy (web, 498).
