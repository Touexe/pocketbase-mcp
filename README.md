# pocketbase-mcp

An MCP server that exposes PocketBase through **13 intent-first tools** rather than ~50 endpoint wrappers.

## Install

Requires Python >=3.11 and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

`uv sync` installs the [`pypocketbase`](https://github.com/Touexe/pypocketbase) client from its Git repository.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POCKETBASE_URL` | `http://127.0.0.1:8090` | PocketBase instance URL |
| `POCKETBASE_ADMIN_EMAIL` | _(none)_ | Superuser email for startup auth |
| `POCKETBASE_ADMIN_PASSWORD` | _(none)_ | Superuser password for startup auth |
| `POCKETBASE_ENABLE_DESTRUCTIVE` | _(unset)_ | Set any truthy value to register `delete_records` and `destroy_collection` |
| `POCKETBASE_MCP_HOST` | `127.0.0.1` | HTTP transport bind host |
| `POCKETBASE_MCP_PORT` | `8000` | HTTP transport bind port |
| `POCKETBASE_LOG_PAGE_SIZE_MAX` | `500` | Max page size for `read_logs` |
| `POCKETBASE_BATCH_LIMIT` | `200` | Max operations per `bulk_write` call |

## Tools

13 intent-first tools. Each one returns `{"ok": true, "data": …, "hint"?: …}` on
success or `{"ok": false, "error_type": …, "message": …, "hint": …}` on failure.
The `hint` names the next tool to call or the step that fixes the error. The
`Kind` column marks each tool **R** read-only, **I** idempotent, or **D**
destructive.

### Always registered (11)

| Tool | Kind | Purpose | Key parameters |
|------|------|---------|----------------|
| `describe_schema` | R | Inventory every collection (name, id, type, field count) | `refresh` |
| `describe_collection` | R | Full field defs, types, `required`, relation targets, `select` values, API rules, indexes for one collection | `collection` |
| `find_records` | R | Query/look up records — by id, or `filter_template` + `filter_params`; paged by default | `collection`, `record_id`, `filter_template`, `filter_params`, `expand`, `fields`, `sort`, `page`, `per_page`, `fetch_all` |
| `write_record` | I | Create or update one record; the server validates the payload against the cached schema first | `collection`, `action` (`create`/`update`), `data`, `record_id`, `expand` |
| `bulk_write` | — | Many writes as one atomic transaction | `operations[]` (`{collection, action: create/update/upsert/delete, data?, record_id?}`) — cap `POCKETBASE_BATCH_LIMIT` |
| `manage_collection` | I | Create or alter a collection (base / auth / view) | `action`, `name`, `collection_type`, `fields`, `view_query`, `api_rules`, `indexes` |
| `connect` | — | Check or switch the process identity | `as_` (`status`/`superuser`/`user`/`impersonate`), `collection`, `email`, `password`, `user_id` |
| `manage_auth` | — | Auth lifecycle: password reset, verification, email change, token refresh | `action`, `collection`, `email`, `token`, `new_email`, `password`, `password_confirm` |
| `manage_files` | — | File on a record: get URL, download bytes, upload local file | `action` (`url`/`download`/`upload`), `collection`, `record_id`, `field`, `filename`, `local_path`, `thumb` |
| `inspect_server` | R | Health, settings summary, cron list, log stats (non-health sections need superuser) | _(none)_ |
| `read_logs` | R | Request log entries (superuser only) | `log_id`, `filter_template`, `filter_params`, `page`, `per_page` |

### Destructive — opt-in only (2)

The server registers these two only when `POCKETBASE_ENABLE_DESTRUCTIVE` is set.
Each one requires a confirmation argument that must match the current state, so
you cannot run the call without first checking what it will affect.

| Tool | Kind | Purpose | Key parameters |
|------|------|---------|----------------|
| `delete_records` | D | Permanently delete records. IRREVERSIBLE | `collection`, `confirm_count` (must equal resolved count), `record_ids` **or** `filter_template` + `filter_params` |
| `destroy_collection` | D | `delete` drops the collection + data; `truncate` keeps schema, drops rows | `action`, `name`, `confirm_name` (must equal `name`) |

### Resource & prompts

- Resource `pocketbase://schema` — all collections (id, name, type, field_count).
- Prompts: `inspect_then_query`, `safe_delete`, `create_with_validation`.

## Skills

`skills/pocketbase-mcp-tools/SKILL.md` is an agent skill that teaches an MCP
client to use these tools correctly. It covers the inspect-then-act order,
filter templates instead of string interpolation, pagination limits, the
complex-query grammar (relation traversal, `?=` any-of, API-rule shapes), and
the confirmation steps for destructive tools. Point your agent at the file, or
copy it into the client's skills directory. It gives better tool use than the
tool docstrings alone.

## Docker

The image runs the **HTTP transport** (`pocketbase-mcp --http`). This is the
only transport that works in a container, because the stdio transport needs the
MCP client to start the process itself. The image binds `0.0.0.0:8000`, runs as
a non-root user, and contains no build tools.

**Pull the published image.** Every GitHub release triggers
`.github/workflows/docker-release.yml`, which builds `linux/amd64` and
`linux/arm64` and pushes to GHCR:
```bash
docker run --rm -p 8000:8000 --env-file .env ghcr.io/touexe/pocketbase-mcp:latest
```
Tags: `latest`, the full version (`1.0.0`), `1.0`, and `1`.

**Build it yourself:**
```bash
docker build -t pocketbase-mcp .
docker run --rm -p 8000:8000 --env-file .env pocketbase-mcp
```

**docker-compose** has two profiles:
```bash
docker compose --profile local up --build      # build from the local Dockerfile
docker compose --profile registry up           # pull ghcr.io/touexe/pocketbase-mcp:latest
```

Both services read the variables from `.env` (`POCKETBASE_URL`,
`POCKETBASE_ADMIN_EMAIL`, `POCKETBASE_ADMIN_PASSWORD`,
`POCKETBASE_ENABLE_DESTRUCTIVE`, and the rest) and set
`POCKETBASE_MCP_HOST=0.0.0.0` and `POCKETBASE_MCP_PORT=8000`.

**To reach a PocketBase server on the host:** inside the container, `127.0.0.1`
points at the container itself, not the host. Set
`POCKETBASE_URL=http://host.docker.internal:8090`. On Linux, also add
`--add-host=host.docker.internal:host-gateway` to `docker run`. Or run
PocketBase in the same compose network and use its service name.

**To override the default flag** (for example, to bind a different port), append
the arguments:
```bash
docker run --rm -p 9000:9000 -e POCKETBASE_MCP_PORT=9000 --env-file .env pocketbase-mcp --http
```

## One Identity Per Process

**This server carries exactly one PocketBase identity.** The `pypocketbase` client writes the auth token into a single shared `aiohttp` session. Calling `connect(as_='user', ...)` changes the identity for **all** subsequent calls in the session.

For multi-tenant use (different identities in parallel), run one server process per identity.

## Destructive Tools Opt-In

`delete_records` and `destroy_collection` are **not registered by default.** Set `POCKETBASE_ENABLE_DESTRUCTIVE=1` to make them available. The opt-in stops a deployment that must never delete data from doing so by accident, whatever the agent requests.

## Running

**stdio (default, for Claude Desktop / MCP clients):**
```bash
uv run pocketbase-mcp
```

**HTTP transport:**
```bash
uv run pocketbase-mcp --http
```

## Client Config Snippet

For Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "pocketbase": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp", "pocketbase-mcp"],
      "env": {
        "POCKETBASE_URL": "http://127.0.0.1:8090",
        "POCKETBASE_ADMIN_EMAIL": "admin@example.com",
        "POCKETBASE_ADMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

## Testing

The default suite is hermetic: no network, no credentials.

```bash
uv run python -m pytest
```

### Live integration suite

`tests/live/` drives the in-memory FastMCP client (the surface an agent sees)
against a **real PocketBase server**. It is marked `live` and excluded from the
default run; opt in with:

```bash
uv run python -m pytest -m live
```

Required environment (names only; never commit a value):

| Variable | Purpose |
|----------|---------|
| `POCKETBASE_URL` | instance the suite runs against (defaults to `http://127.0.0.1:8090`) |
| `POCKETBASE_ADMIN_EMAIL` | superuser identity, established through the `connect` tool |
| `POCKETBASE_ADMIN_PASSWORD` | superuser password |

The suite sets `settings.enable_destructive` for its own session, so
`delete_records` and `destroy_collection` are exercised; you do **not** need to
set `POCKETBASE_ENABLE_DESTRUCTIVE` yourself.

When the server is unreachable or either credential is missing, every live test
**skips with a stated reason**; it never errors.

> **⚠️ Development instances only.** The live suite creates and deletes
> collections. Never point `POCKETBASE_URL` at production or any instance whose
> data you care about.

#### The `mcptest_` prefix rule: the safety contract

Every collection a live test touches must be one it created itself, named
`mcptest_<area>_<hex8>` via the `live_collection` factory. Teardown (both the
per-test finalizer and the session-end sweep) deletes **only** `mcptest_*`
names and **raises rather than deletes** anything else. This, plus the rule that
no test names a collection it did not create, keeps a mis-pointed
`POCKETBASE_URL` from destroying real data. Anyone adding a live test must
honor it: draw collections from the factory, never hard-code a bare name.

#### Resolved design questions

- **Session-end sweep is always on** (no `--no-live-sweep`). The sweep runs at
  the start and end of the next session and removes a crashed run's `mcptest_*`
  leftovers, so a fresh run is always clean; diagnose a failure by rerunning the
  single test.
- **File-upload fixture is a generated temp file**, not a committed binary
  asset. No thumbnail behaviour is exercised, so no real image is needed.

## Smoke-testing over HTTP

`tests/` and `tests/live/` both run in-process; neither builds an HTTP
request. `scripts/curl_smoke.sh` closes that gap: it drives an
**already-running** HTTP server with nothing but `curl`, `jq`, and `sed`,
completing the MCP Streamable HTTP handshake, then issuing one real `tools/call`
against every registered tool. It is an operator/developer
command; it is **not** collected by `pytest` and not wired into CI.

> **⚠️ It writes to a real instance.** Point it only at a **development**
> PocketBase. Every collection and record it creates lives under an ephemeral
> `mcpsmoke_`-prefixed collection that it drops again on exit.

**1. Start the server** (a second terminal), against a development instance,
with the destructive tools registered so all 13 are covered:

```bash
POCKETBASE_URL=http://127.0.0.1:8090 \
POCKETBASE_ADMIN_EMAIL=admin@example.com \
POCKETBASE_ADMIN_PASSWORD=your-password \
POCKETBASE_ENABLE_DESTRUCTIVE=1 \
uv run pocketbase-mcp --http
```

Without `POCKETBASE_ENABLE_DESTRUCTIVE=1` the server registers only 11 tools and
the harness prints a `SKIP:` line saying the flag is required for full coverage.

**2. Run the harness:**

```bash
POCKETBASE_ADMIN_EMAIL=admin@example.com \
POCKETBASE_ADMIN_PASSWORD=your-password \
bash scripts/curl_smoke.sh
```

It reads `POCKETBASE_MCP_HOST` / `POCKETBASE_MCP_PORT` (default
`127.0.0.1:8000`) to find the server. `POCKETBASE_ADMIN_EMAIL` /
`POCKETBASE_ADMIN_PASSWORD` are the superuser credentials it authenticates and
tears down with; the same names the server itself uses.

**Prerequisites:** `bash`, `curl`, `jq`, and `sed` on `PATH`. Missing any of
them, missing a credential, or an unreachable MCP port each produce a `SKIP:`
line and exit 0, never a failure. A genuine assertion failure prints the
request and the full response body, still runs the remaining cases, tears down,
and exits 1.

**Cleanup.** A clean run, a failed run, and a Ctrl-C all trigger an EXIT trap
that reconnects as superuser and drops every `mcpsmoke_` collection the run
created. A hard kill (`SIGKILL`) can still strand `mcpsmoke_*` collections;
they are safe to drop by hand. If teardown's own superuser reconnect fails
(the process may be left holding an ephemeral user identity), restart the
server process before retrying.

## Design Decisions (Open Questions Resolved)

### Should `find_records` fall back to `get_full_list` automatically?

**Decision: Explicit `fetch_all=True` required.**

An accidental full-table read floods the context window. An agent that asks for "all records" from a 100,000-row table would silently exhaust its context budget if the fallback were automatic. Passing `fetch_all=True` is a deliberate signal; the default paged behavior is safe.

### Expose the schema as an MCP resource in addition to `describe_schema`?

**Decision: Deferred. Tools only for v1.**

Resources require the client to know when to re-fetch them (cache invalidation). Tools give the agent explicit control: call `describe_schema(refresh=True)` after a schema change. Once real usage shows the schema being re-read every turn, a resource is the right fix. Adding it later is cheap; it doesn't change any tool contracts.
