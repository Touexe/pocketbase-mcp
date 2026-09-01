# Active Challenges in `mcpskill_read` (active = true), sorted by points (high to low)

## Final Answer

| Title | Points |
|-------|-------:|
| Buffer Overflow | 500 |
| Crypto Basics | 300 |
| XSS Warmup | 150 |
| SQL Injection 101 | 100 |

4 active challenges total.

## MCP Tool Calls Made

1. `mcp__pocketbase__connect(as_="status")`
   - Response: OK. Already authenticated as `superuser:mrrtou@protonmail.com`; no startup auth error.

2. `mcp__pocketbase__find_records(collection="mcpskill_read", filter_template="active = {:a}", filter_params={"a": true}, sort="-points", fetch_all=true)`
   - Response: OK. Returned 4 records: Buffer Overflow (500, hard), Crypto Basics (300, medium), XSS Warmup (150, easy), SQL Injection 101 (100, easy).
