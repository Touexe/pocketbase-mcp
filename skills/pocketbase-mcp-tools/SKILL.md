---
name: pocketbase-mcp-tools
description: >-
  Operate a live PocketBase instance through the pocketbase MCP server — the
  mcp__pocketbase__* tools: connect, describe_schema, describe_collection,
  find_records, write_record, bulk_write, delete_records, manage_collection,
  destroy_collection, manage_auth, manage_files, inspect_server, read_logs.
  Use whenever a task acts on real PocketBase data or schema through those
  tools: reading or filtering records (including relation traversal, OR groups,
  ranges, date filters, any-of on multi-value fields, and top-N / count-per-group
  questions), creating/updating/deleting records or whole collections, setting
  API rules, authenticating or impersonating, uploading or fetching files, or
  checking server health, cron jobs, and logs — even when the user never names
  the tools ("add a row to posts", "is PocketBase up?", "who has the most
  solves?", "make the tickets collection public-read"). Read it before the first
  mcp__pocketbase__* call for the inspect-then-act order, filter templating over
  string interpolation, and the destructive-op confirmation contract. Not for
  PocketBase client-library or SDK code (the Python pocketbase package, the
  JS/Dart/Go SDKs), for editing the pb-mcp server's own source, or for pure
  schema-design, product-comparison, self-hosting, or concept questions with no
  instance to act on.
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
escaping and a value with a quote or backslash breaks the query. This holds even
for values you wrote yourself and "know" are safe (a hardcoded status, a date
literal): put every value in `filter_params` so the template stays a pure shape.
Every placeholder in the template must have a matching key in `filter_params` or
the call fails with `FILTER_ERROR`.

Other `find_records` knobs: `sort` (`"-created,title"`), `fields` (projection,
comma-separated), `expand` (relation fields), `page` / `per_page`.

## Pagination: paged by default, `fetch_all` is a deliberate choice

`find_records` returns one page (30 records) unless you pass `fetch_all=True`.
`fetch_all` walks every page and can dump a huge table into your context — only
use it when you genuinely need every row (e.g. to count them before a delete).
When a paged response has `total_pages > 1` the `hint` reminds you `fetch_all`
exists; that's not an instruction to use it.

To **count** without reading rows, ask for one row and read the total:
`find_records(collection, filter_template=…, filter_params=…, per_page=1,
fields="id")` returns `total_items`. That's the right move before a delete, or
any "how many …" question.

## Complex queries

The filter grammar is the same one PocketBase uses for API rules, so it goes
well beyond `field = value`. It still binds through `filter_params` — the
placeholders just sit inside a richer expression.

### Operators

| Kind | Operators | Notes |
|---|---|---|
| Compare | `=` `!=` `>` `>=` `<` `<=` | numbers compare numerically; quote/param strings and dates |
| Text contains | `~` `!~` | `~` wraps the value in `%…%` unless you include your own `%`; `name ~ {:p}` with `{"p": "Get%"}` is prefix match |
| Any-of (multi-value / multi-relation / back-relation) | `?=` `?!=` `?~` `?>` … | prefix a normal operator with `?` to mean "at least one element matches". Use for `select` fields with many values, multi-relations, and relation paths that fan out |
| Logical | `&&` `||` `!( … )` | group with parens: `a && (b || c)` |
| Null / empty | `field != null`, `field != ""` | a bare `date >= {:d}` silently drops null rows — guard with `field != "" && date >= {:d}` when null is possible |

### Relation traversal

Walk a relation with a dot **in the filter path directly** — no `expand.`
prefix (that prefix is only for `fields`):

```
find_records(
  collection="team_challenges",
  filter_template="is_solved = {:s} && is_first_blood = {:s} && challenge.difficulty = {:d} && solved_at < {:t}",
  filter_params={"s": True, "d": "hard", "t": "2026-08-16 03:00:00"},
  expand="challenge,team",
  sort="solved_at",
)
```

`challenge.difficulty` filters on the related record's field. Add `expand` for
the same relations so the response carries names, not just ids. `sort` accepts
the same dotted paths (`sort="challenge.score,-solved_at"`). Dates are compared
as strings in `YYYY-MM-DD HH:MM:SS` form; `@now` is the current server time.

### Relation values: id vs. human label

A relation field stores the target record's **id**. In some schemas that id is
a readable slug (`category = {:c}` with `{"c": "web"}` just works); in others
it's a random string and you need a lookup first —
`find_records("categories", filter_template="name = {:n}", …)` to get the id,
then filter the main collection by it. Check with `describe_collection` /
one sample row before assuming.

### Projections and `expand` size

- **Always keep `id` in a `fields` projection.** `fields="submitted_by"` on its
  own makes the response fail to parse; `fields="id,submitted_by"` is fine.
- `fields` does **not** trim expanded records — `expand` + `fetch_all` returns
  every expanded relation in full and can be enormous. For a big result set,
  page through it (`per_page` up to 500; the server caps higher requests) and
  pull only the id + the one or two fields you need, rather than `fetch_all`
  with `expand`.
- For stable deep paging, sort by a field and walk a cursor:
  `sort="created"`, then next page `filter_template="created > {:c}"` with the
  last row's value.

### No aggregation — tally client-side or use a view

The filter language has no `GROUP BY`, `COUNT(*) … GROUP BY`, `SUM`, or
`DISTINCT`. For "top N by group", "count per category", etc.:

1. First check `describe_schema` for a `view` collection that already
   summarises it (these are often named like `*_stats` / `*_metrics`) — reading
   a view is one cheap call.
2. Otherwise fetch the narrowest projection that answers it (`id` plus the
   grouping field), page through, and count in your own head / a scratch
   script. Resolve any winning id to a name with a follow-up `find_records`.

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
- `api_rules`: `{"list", "view", "create", "update", "delete"}`. On `update`,
  only the keys you pass change. See **API rules** below for what the values mean.
- `indexes`: list of `CREATE INDEX …` strings.

The schema cache invalidates automatically after any `manage_collection` or
`destroy_collection`. After an **external** schema change, call
`describe_schema(refresh=True)` yourself.

### API rules

Each of the five rules is one of three things, and the two "empty-looking" ones
are **opposite extremes** — the single most common mistake here:

| Value | Meaning |
|---|---|
| `null` | locked — only superusers can perform this action |
| `""` (empty string) | fully open — anyone, unauthenticated included |
| a filter expression | the action is allowed only for requests the expression matches |

A rule expression uses the **same grammar as a query filter** (see *Complex
queries* — operators, `&&`/`||`/parens, relation traversal, `?=` for
multi-values), plus request macros:

- `@request.auth.id`, `@request.auth.verified`, `@request.auth.<field>` — the
  caller's auth record; `@request.auth.id != ""` means "any logged-in user".
- `@request.body.<field>` — a value in the incoming write payload.
- `@request.query.<param>` — a query-string parameter.
- `@collection.<name>.<field>` — reference another collection for cross-checks.

`list` is applied as an always-on filter on multi-record queries; `view` gates a
single-record fetch. Keep `view` at least as permissive as `list` or a record
that shows up in a list can't be opened. Common shapes:

- Owner-only: every rule `owner = @request.auth.id` (with `owner` a relation to
  the users collection).
- Public read, authenticated write: `list`/`view` = `""`, `create` =
  `@request.auth.id != ""`, `update`/`delete` = `owner = @request.auth.id`.

Same null pitfall as filters: a rule comparing a nullable field silently
excludes rows where it's null — guard with `field != "" && …` when relevant.
`describe_collection` returns the current rules under `api_rules`.

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
| a parse/validation error mentioning missing `id` on list items | your `fields` projection dropped `id` — add it back |
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

**Complex query — relation traversal, OR group, range, compound sort**
```
describe_collection(collection="challenges")        # confirm field + relation names
find_records(collection="challenges",
             filter_template="(category = {:c1} || category = {:c2}) && is_dynamic = {:d} && score >= {:lo} && score < {:hi}",
             filter_params={"c1": "web", "c2": "pwn", "d": true, "lo": 300, "hi": 550},
             sort="-score,name",
             fields="id,name,category,score")
```

**"Which X has the most Y" — no aggregation in the filter language**
```
describe_schema()                                  # look for a *_stats / *_metrics view first
find_records(collection="submissions", filter_template="status = {:s}",
             filter_params={"s": "incorrect"}, per_page=1, fields="id")   # total_items = the count
# then page id + the grouping field, tally client-side, resolve the winner's id to a name
find_records(collection="players", record_id="<winning id>")
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
