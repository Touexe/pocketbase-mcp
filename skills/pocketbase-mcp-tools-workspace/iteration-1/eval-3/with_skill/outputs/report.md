# PocketBase Collection Inventory

## (a) Final answer

Your PocketBase instance has **28 collections**. Grouped by type:

### View collections (5) — these are the "views"

| Collection | ID | Fields |
|---|---|---|
| `team_challenges_flags` | pbc_3302673531 | 2 |
| `_players_attempts` | pbc_826859169 | 6 |
| `_team_players_stats` | pbc_4040147337 | 7 |
| `_dashboard_metrics` | pbc_3864132092 | 7 |
| `_submission_stats` | pbc_3757750218 | 7 |

### Auth collections (2)

| Collection | ID | Fields |
|---|---|---|
| `_superusers` | pbc_3142635823 | 8 |
| `admins` | pbc_3841632486 | 8 |

### Base collections (21)

| Collection | ID | Fields |
|---|---|---|
| `_mfas` | pbc_2279338944 | 6 |
| `_otps` | pbc_1638494021 | 7 |
| `_externalAuths` | pbc_2281828961 | 7 |
| `_authOrigins` | pbc_4275539003 | 6 |
| `challenges` | pbc_4177893232 | 17 |
| `players` | pbc_3072146508 | 8 |
| `players_ips` | pbc_1170593909 | 7 |
| `submissions` | pbc_3482339971 | 8 |
| `teams` | pbc_1568971955 | 8 |
| `team_challenges` | pbc_1461729463 | 23 |
| `challenge_hosts` | pbc_2991784505 | 6 |
| `challenge_opening_events` | pbc_1939645552 | 7 |
| `team_files` | pbc_1065564553 | 11 |
| `cheatings` | pbc_358715054 | 13 |
| `challenge_categories` | pbc_1473151097 | 4 |
| `__event_details` | pbc_3927200278 | 3 |
| `mcpskill_read` | pbc_854431867 | 5 |
| `mcpskill_update` | pbc_2170398959 | 5 |
| `mcpskill_delete` | pbc_594206992 | 5 |
| `mcpskill_bulk` | pbc_1539510088 | 5 |
| `mcpskill_bulkmix` | pbc_2933128039 | 5 |

Note: `_mfas`, `_otps`, `_externalAuths`, `_authOrigins` are PocketBase internal system collections (base type); `_superusers` is the built-in superuser auth collection.

## (b) Ordered list of mcp__pocketbase__* tool calls

1. `mcp__pocketbase__connect(as_="status")`
   - Response: ok. Identity `superuser:mrrtou@protonmail.com`, `startup_auth_error: null`.

2. `mcp__pocketbase__describe_schema()`
   - Response: ok. 28 collections returned with name/id/type/field_count. Types: base x21, auth x2 (`_superusers`, `admins`), view x5 (`team_challenges_flags`, `_players_attempts`, `_team_players_stats`, `_dashboard_metrics`, `_submission_stats`).
