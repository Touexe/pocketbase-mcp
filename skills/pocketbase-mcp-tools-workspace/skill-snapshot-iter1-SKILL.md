---
name: pocketbase-mcp-tools
description: >-
  How to drive a PocketBase instance through the pocketbase MCP server's 13
  intent-first tools (connect, describe_schema, describe_collection,
  find_records, write_record, bulk_write, delete_records, manage_collection,
  destroy_collection, manage_auth, manage_files, inspect_server, read_logs).
  Use this whenever a task involves calling the mcp__pocketbase__* tools:
  querying or mutating records, inspecting or changing collection schema,
  authenticating, uploading or fetching files, or reading server health and
  logs — even when the user does not name the tools and just says things like
  "add a row to the posts collection", "find all published articles in
  PocketBase", "create a users collection", or "check if PocketBase is up".
  Read this before your first mcp__pocketbase__* call so you follow the
  inspect-then-act order, use filter templating instead of string
  interpolation, and respect the destructive-op confirmation contract.
---

# Using the PocketBase MCP tools

This MCP server wraps a PocketBase instance in **13 tools** instead of ~50 raw
endpoint calls. Each tool is intent-first: its name says what job it does, and
its response carries a `hint` pointing at the next tool. Lean on those hints —
they encode the intended workflow.

## The one rule that prevents most failures: inspect, then act

`write_record` and `bulk_write` validate your payload against the server's
cached schema *before* sending it. A field name that isn't in the collection
fails with `VALIDATION_ERROR`, and a missing required field fails the same way.
Guessing field names wastes a round trip every time.

So the default path for any record work is:

1. `describe_schema()` — list collections, confirm the one you want exists.
2. `describe_collection(collection="<name>")` — get exact field names, types,
   which are `required`, relation targets, `select` values, file fields, and
   the API rules.
3. Then `find_records` / `write_record` / `bulk_write` using only those field
   names.

Skip steps 1–2 only when you already saw the schema earlier in this same
session and nothing has changed it since.

## Tool map

| Job | Tool | Notes |
|---|---|---|
| Check / change who you are | `connect` | `as_="status"` to check; `superuser`/`user`/`impersonate` to switch |
| Auth lifecycle | `manage_auth` | password reset, verification, email change, token refresh |
| List collections | `describe_schema` | `refresh=True` after an out-of-band schema change |
| Inspect one collection | `describe_collection` | fields, types, `required`, relations, API rules |
| Query records | `find_records` | by `record_id`, or `filter_template` + `filter_params`; paged by default |
| Create / update one record | `write_record` | `action="create"` or `"update"` (needs `record_id`) |
| Many writes atomically | `bulk_write` | one transaction; `create`/`update`/`upsert`/`delete`; cap ~200 ops |
| Permanently delete records | `delete_records` | **may be unregistered**; needs `confirm_count` |
| Create / alter a collection | `manage_collection` | base / auth / view; fields, API rules, indexes |
| Drop or empty a collection | `destroy_collection` | **may be unregistered**; needs `confirm_name` |
| Files on a record | `manage_files` | `url` / `download` / `upload` |
| Server health, settings, crons, log stats | `inspect_server` | superuser for the non-health sections |
| Request log entries | `read_logs` | superuser only |

## Identity: one per process

The server holds **exactly one** PocketBase identity at a time. `connect(as_=…)`
changes it for **every** later call in the session, not just the next one.
Start ambiguous tasks with `connect(as_="status")` to see the current identity
and whether startup auth succeeded. If a call returns `UNAUTHORIZED_ERROR` or
`*_PERMISSION_ERROR`, the fix is almost always `connect(as_="superuser", …)`
or `connect(as_="user", collection=…, …)` first.

Superuser is required for: `read_logs`, the settings/crons/log-stats sections
of `inspect_server`, all of `manage_collection` / `destroy_collection`, and
`connect(as_="impersonate")`.

## Filters: template + params, never string interpolation

`find_records`, `delete_records`, and `read_logs` take a `filter_template` with
`{:name}` placeholders and a `filter_params` dict of values. The server binds
them with PocketBase's own escaping.

```
find_records(
  collection="articles",
  filter_template="status = {:s} && author = {:a}",
  filter_params={"s": "published", "a": "user_123"},
)
```

Do **not** build `filter_template="status = 'published'"` by hand — you lose the
escaping and a value with a quote or backslash breaks the query. Every
placeholder in the template must have a matching key in `filter_params` or the
call fails with `FILTER_ERROR`.

Other `find_records` knobs: `sort` (`"-created,title"`), `fields` (projection,
comma-separated), `expand` (relation fields), `page` / `per_page`.

## Pagination: paged by default, `fetch_all` is a deliberate choice

`find_records` returns one page (30 records) unless you pass `fetch_all=True`.
`fetch_all` walks every page and can dump a huge table into your context — only
use it when you genuinely need every row (e.g. to count them before a delete).
When a paged response has `total_pages > 1` the `hint` reminds you `fetch_all`
exists; that's not an instruction to use it.

## Writing records

- **Create:** `write_record(collection, action="create", data={…})` — `data`
  must contain every `required` field and no unknown fields.
- **Update:** `write_record(collection, action="update", record_id="…",
  data={…})` — include only the fields you're changing.
- **`bulk_write`** runs a list of `operations` as **one atomic transaction** —
  all succeed or all roll back. Each op is
  `{"collection", "action", "data"?, "record_id"?}` where `action` is
  `create` | `update` | `upsert` | `delete`. `update`, `upsert`, and `delete`
  need `record_id`. The batch is validated op-by-op before dispatch; the error
  names the failing operation index. Keep batches under ~200 ops (the server's
  `POCKETBASE_BATCH_LIMIT`); split larger jobs and call `bulk_write` per chunk.

Use `bulk_write` when the writes must land together or you have many of them.
Use `write_record` for a single independent change.

## Destructive operations

`delete_records` and `destroy_collection` are **opt-in** — a deployment can
launch without them registered (`POCKETBASE_ENABLE_DESTRUCTIVE` unset). If you
don't see them available, tell the user they're disabled server-side rather
than trying to work around it.

Both use a confirmation argument that must match reality, so you can't fire
them blind:

- **`delete_records`** needs `confirm_count` equal to the exact number of
  records the call will delete. Get that number first:
  `find_records(..., fetch_all=True, fields="id")`, count the results, pass
  that as `confirm_count`. A mismatch is rejected. Select rows by
  `record_ids=[…]` **or** `filter_template`+`filter_params`, not both.
- **`destroy_collection`** needs `confirm_name` exactly equal to `name`.
  `action="delete"` removes the collection and its data; `action="truncate"`
  keeps the schema and drops all rows.

For a filtered delete, show the user what matched (the `find_records` result)
and confirm intent before calling `delete_records` — deletion is irreversible.

## Managing collections

`manage_collection(action="create"|"update", name=…)`:

- `collection_type`: `"base"` (default), `"auth"`, or `"view"` (create only).
- `fields`: list of PocketBase field dicts, e.g.
  `{"name": "title", "type": "text", "required": true}`. A `relation` field's
  target (`collectionId`) is checked against known collections before dispatch —
  an unknown target fails with `UNKNOWN_RELATION_TARGET`, so create the target
  collection first.
- `view_query`: SQL for `type="view"`; it's dry-run-validated before creation,
  and a bad query comes back as `VIEW_QUERY_INVALID`.
- `api_rules`: `{"list", "view", "create", "update", "delete"}`, each a
  PocketBase rule string or `null` for "superuser only". On `update`, only the
  keys you pass change.
- `indexes`: list of `CREATE INDEX …` strings.

The schema cache invalidates automatically after any `manage_collection` or
`destroy_collection`. After an **external** schema change, call
`describe_schema(refresh=True)` yourself.

## Files

`manage_files(action, collection, record_id, field, …)` — `field` must be an
actual file field on the collection (checked against the schema; otherwise
`INVALID_FIELD`).

- `action="url"` — needs `filename`; add `thumb="200x200"` for image
  thumbnails. Protected file fields get a time-limited token URL.
- `action="download"` — needs `filename`; returns the byte count (the server
  fetched it, useful to confirm a file exists / is reachable).
- `action="upload"` — needs `local_path`, an **absolute** path that exists on
  this machine; optional `filename` overrides the stored name. Upload replaces
  the field via a record update.

## The error contract — read the hint

Every tool returns a dict. Success is `{"ok": true, "data": …, "hint"?: …}`.
Failure is `{"ok": false, "error_type": "…", "message": "…", "hint": "…",
"status"?: n}`. The `hint` names the recovery action — follow it instead of
retrying the same call. Common `error_type`s:

| `error_type` | What to do |
|---|---|
| `VALIDATION_ERROR` | `describe_collection`; fix field names / required fields |
| `COLLECTION_NOT_FOUND` | `describe_schema` (add `refresh=True` if just changed) |
| `RECORD_NOT_FOUND` | `find_records` with a filter to get the real id |
| `FILTER_ERROR` | a `{:placeholder}` has no value in `filter_params` |
| `UNAUTHORIZED_ERROR` / `*_PERMISSION_ERROR` | `connect` as superuser or the right user |
| `BATCH_TOO_LARGE` | split `operations` into chunks of ≤ the stated limit |
| `TOO_MANY_REQUESTS_ERROR` | back off before retrying |

## Recipes

**Query with a filter**
```
describe_schema()
describe_collection(collection="articles")
find_records(collection="articles",
             filter_template="published = {:p} && category = {:c}",
             filter_params={"p": true, "c": "eng"},
             sort="-created", per_page=50)
```

**Create a record safely**
```
describe_collection(collection="articles")          # see required fields
write_record(collection="articles", action="create",
             data={"title": "…", "body": "…", "author": "user_123"})
```

**Filtered delete (with confirmation)**
```
connect(as_="superuser", email="…", password="…")   # if not already
matches = find_records(collection="articles", fetch_all=True, fields="id",
                       filter_template="status = {:s}", filter_params={"s": "draft"})
# show matches to the user, confirm intent
delete_records(collection="articles",
               filter_template="status = {:s}", filter_params={"s": "draft"},
               confirm_count=<len(matches)>)
```

**New collection with a relation**
```
describe_schema()                                   # get the users collection id/name
manage_collection(action="create", name="comments", fields=[
  {"name": "body",   "type": "text", "required": true},
  {"name": "author", "type": "relation", "required": true,
   "collectionId": "users", "maxSelect": 1},
])
```

**Check the server is healthy**
```
inspect_server()        # health works unauthenticated; other sections need superuser
```

## Reporting results

Summarize what changed in plain terms — collection and record ids touched,
counts created/updated/deleted, and the filter you used. Paste raw record
dumps only when the user asked to see the data; otherwise a count plus the key
fields is enough to keep the exchange readable.
