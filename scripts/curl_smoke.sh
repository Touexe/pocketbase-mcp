#!/usr/bin/env bash
#
# curl_smoke.sh — black-box smoke test of the pocketbase-mcp HTTP transport.
#
# Drives an ALREADY-RUNNING server (it starts nothing): completes the MCP
# Streamable HTTP handshake, then issues one real `tools/call` per registered
# tool and asserts the answer at three levels — HTTP 200, a clean JSON-RPC
# envelope with a matching id, and a non-error tool result.
#
# Usage:
#   # in one terminal, against a DEVELOPMENT PocketBase instance:
#   POCKETBASE_ENABLE_DESTRUCTIVE=1 \
#   POCKETBASE_ADMIN_EMAIL=... POCKETBASE_ADMIN_PASSWORD=... \
#   uv run pocketbase-mcp --http
#
#   # in another:
#   POCKETBASE_ADMIN_EMAIL=... POCKETBASE_ADMIN_PASSWORD=... \
#   bash scripts/curl_smoke.sh
#
# Requires: bash, curl, jq, sed. No Python interpreter is invoked.
#
# Every collection and record this run writes lives under an ephemeral
# `mcpsmoke_`-prefixed collection it creates and drops again on exit (including
# on failure or Ctrl-C). It never touches a pre-existing collection. A hard
# kill (SIGKILL) can still strand `mcpsmoke_*` collections — drop them by hand.
#
# Exit codes: 0 = every tool passed (or a stated SKIP); 1 = a tool failed.

set -euo pipefail

# --------------------------------------------------------------------------- #
# Config                                                                      #
# --------------------------------------------------------------------------- #
MCP_HOST="${POCKETBASE_MCP_HOST:-127.0.0.1}"
MCP_PORT="${POCKETBASE_MCP_PORT:-8000}"
MCP_PATH="/mcp/"
PREFIX="mcpsmoke"
CLIENT_PROTOCOL_VERSION="2025-06-18"
BASE_URL="http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}"

NOTES_COLLECTION="${PREFIX}_notes"
USERS_COLLECTION="${PREFIX}_users"
SMOKE_USER_EMAIL="smoke_user@example.test"
SMOKE_USER_PASSWORD="smoke-pass-0123456789"

# --------------------------------------------------------------------------- #
# Run state                                                                   #
# --------------------------------------------------------------------------- #
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/curl_smoke.XXXXXX")"
HDR_FILE="$WORKDIR/headers"
BODY_FILE="$WORKDIR/body"
RPC_JSON="$WORKDIR/rpc.json"      # the de-framed JSON-RPC message
LAST_REQ="$WORKDIR/last_req"

RPC_ID=0
LAST_HTTP=""
LAST_PARAMS=""
SESSION_ID=""
SERVER_PROTOCOL_VERSION=""

PASS_COUNT=0
FAIL_COUNT=0
FAILED_TOOLS=""
declare -a CREATED_COLLECTIONS=()

cleanup_workdir() { rm -rf "$WORKDIR" 2>/dev/null || true; }

# --------------------------------------------------------------------------- #
# skip / fail                                                                 #
# --------------------------------------------------------------------------- #
# skip() — a precondition is absent; this is not a failure. Exit 0.
skip() {
  echo "SKIP: $*"
  cleanup_workdir
  exit 0
}

# fail() — a transport / handshake invariant broke and continuing is
# meaningless. Print the reason plus the last request and response, then abort
# (the EXIT trap still tears down anything already created).
fail() {
  echo "FAIL: $*" >&2
  if [ -s "$LAST_REQ" ]; then
    echo "--- last request ---" >&2
    cat "$LAST_REQ" >&2
  fi
  if [ -s "$BODY_FILE" ]; then
    echo "--- last response (HTTP ${LAST_HTTP}) ---" >&2
    cat "$BODY_FILE" >&2
    echo >&2
  fi
  exit 1
}

# --------------------------------------------------------------------------- #
# Transport: rpc / notify / deframe                                           #
# --------------------------------------------------------------------------- #

# deframe — turn whatever came back in $BODY_FILE into a single JSON-RPC object
# in $RPC_JSON. Streamable HTTP answers either `application/json` (use as-is) or
# `text/event-stream` (take the `data:` payload of the message event).
deframe() {
  local ctype
  ctype="$(sed -n 's/\r$//; s/^[Cc]ontent-[Tt]ype:[[:space:]]*//p' "$HDR_FILE" | sed -n '$p')"
  case "$ctype" in
    *text/event-stream*)
      sed -n -E 's/\r$//; s/^data: ?//p' "$BODY_FILE" | sed -n '$p' > "$RPC_JSON"
      ;;
    *)
      cp "$BODY_FILE" "$RPC_JSON"
      ;;
  esac
}

# rpc <method> <params-json> — POST one JSON-RPC request with a monotonic id and
# the session / protocol-version headers once the handshake has set them.
rpc() {
  local method="$1" params="$2" payload
  RPC_ID=$((RPC_ID + 1))
  payload="$(jq -cn --argjson id "$RPC_ID" --arg method "$method" --argjson params "$params" \
    '{jsonrpc:"2.0", id:$id, method:$method, params:$params}')"
  printf '%s\n' "$payload" > "$LAST_REQ"

  local -a hdrs=(
    -H "Content-Type: application/json"
    -H "Accept: application/json, text/event-stream"
  )
  if [ -n "$SESSION_ID" ]; then hdrs+=(-H "Mcp-Session-Id: ${SESSION_ID}"); fi
  if [ -n "$SERVER_PROTOCOL_VERSION" ]; then hdrs+=(-H "MCP-Protocol-Version: ${SERVER_PROTOCOL_VERSION}"); fi

  LAST_HTTP="$(curl -sS -L --max-time 30 -o "$BODY_FILE" -D "$HDR_FILE" -w '%{http_code}' \
    "${hdrs[@]}" -X POST --data-binary "$payload" "$BASE_URL" 2>/dev/null || true)"
  deframe
}

# notify <method> — POST a JSON-RPC notification (no id, no result body).
notify() {
  local method="$1" payload
  payload="$(jq -cn --arg method "$method" '{jsonrpc:"2.0", method:$method}')"
  printf '%s\n' "$payload" > "$LAST_REQ"

  local -a hdrs=(
    -H "Content-Type: application/json"
    -H "Accept: application/json, text/event-stream"
  )
  if [ -n "$SESSION_ID" ]; then hdrs+=(-H "Mcp-Session-Id: ${SESSION_ID}"); fi
  if [ -n "$SERVER_PROTOCOL_VERSION" ]; then hdrs+=(-H "MCP-Protocol-Version: ${SERVER_PROTOCOL_VERSION}"); fi

  LAST_HTTP="$(curl -sS -L --max-time 30 -o "$BODY_FILE" -D "$HDR_FILE" -w '%{http_code}' \
    "${hdrs[@]}" -X POST --data-binary "$payload" "$BASE_URL" 2>/dev/null || true)"
}

# call_tool <name> <arguments-json> — a tools/call wrapper that records the
# arguments for check() to print on failure.
call_tool() {
  local name="$1" args="$2" params
  LAST_PARAMS="$args"
  params="$(jq -cn --arg name "$name" --argjson args "$args" '{name:$name, arguments:$args}')"
  rpc "tools/call" "$params"
}

# envelope — the tool's returned dict (its {ok,...} envelope) as compact JSON.
envelope() {
  jq -c '(.result.structuredContent // (.result.content[0].text | fromjson?)) // {}' "$RPC_JSON"
}

# --------------------------------------------------------------------------- #
# Handshake                                                                   #
# --------------------------------------------------------------------------- #
handshake() {
  local params server_name
  params="$(jq -cn --arg pv "$CLIENT_PROTOCOL_VERSION" \
    '{protocolVersion:$pv, capabilities:{}, clientInfo:{name:"curl-smoke", version:"0"}}')"
  rpc "initialize" "$params"

  [ "$LAST_HTTP" = "200" ] || fail "initialize returned HTTP ${LAST_HTTP}, expected 200"

  SESSION_ID="$(sed -n 's/\r$//; s/^[Mm]cp-[Ss]ession-[Ii]d:[[:space:]]*//p' "$HDR_FILE" | sed -n '$p')"
  [ -n "$SESSION_ID" ] || fail "initialize response carried no Mcp-Session-Id header"

  SERVER_PROTOCOL_VERSION="$(jq -r '.result.protocolVersion // empty' "$RPC_JSON")"
  server_name="$(jq -r '.result.serverInfo.name // empty' "$RPC_JSON")"
  [ "$server_name" = "pocketbase" ] || fail "serverInfo.name is '${server_name}', expected 'pocketbase'"

  echo "handshake: serverInfo.name=${server_name} session=${SESSION_ID} protocolVersion=${SERVER_PROTOCOL_VERSION:-<none>}"

  notify "notifications/initialized"
  case "$LAST_HTTP" in
    202|200) ;;
    *) fail "notifications/initialized returned HTTP ${LAST_HTTP}, expected 202" ;;
  esac
}

# --------------------------------------------------------------------------- #
# Per-tool assertion                                                          #
# --------------------------------------------------------------------------- #
# check <tool-name> — grade the response now in $RPC_JSON against the id in
# $RPC_ID. Records PASS or FAIL; never aborts the run (guards `set -e`).
check() {
  local tool="$1" ok=1 reason="" rid env_ok

  if [ "$LAST_HTTP" != "200" ]; then
    ok=0; reason="HTTP ${LAST_HTTP} (expected 200)"
  fi

  if [ "$ok" = 1 ] && jq -e 'has("error")' "$RPC_JSON" >/dev/null 2>&1; then
    ok=0; reason="JSON-RPC error $(jq -c '.error' "$RPC_JSON")"
  fi

  if [ "$ok" = 1 ]; then
    rid="$(jq -r '.id // empty' "$RPC_JSON" 2>/dev/null || true)"
    if [ "$rid" != "$RPC_ID" ]; then
      ok=0; reason="id mismatch: response id='${rid}', request id='${RPC_ID}'"
    fi
  fi

  if [ "$ok" = 1 ] && [ "$(jq -r '.result.isError // false' "$RPC_JSON" 2>/dev/null || echo true)" = "true" ]; then
    ok=0; reason="result.isError=true"
  fi

  # The tools return {"ok": false, ...} envelopes for handled errors WITHOUT
  # setting result.isError, so grade the envelope too. (jq's `//` treats false
  # as empty, so test membership explicitly rather than `.ok // ...`.)
  if [ "$ok" = 1 ]; then
    env_ok="$(envelope | jq -r 'if has("ok") then (.ok | tostring) else "absent" end' 2>/dev/null || echo absent)"
    if [ "$env_ok" = "false" ]; then
      ok=0; reason="tool envelope ok=false — $(envelope | jq -c '{error_type, message}')"
    fi
  fi

  if [ "$ok" = 1 ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
    echo "PASS  ${tool}"
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    FAILED_TOOLS="${FAILED_TOOLS} ${tool}"
    echo "FAIL  ${tool} — ${reason}"
    echo "      params: ${LAST_PARAMS}"
    echo "      response body:"
    sed 's/^/        /' "$BODY_FILE" || true
  fi
  return 0
}

# extra_fail <label> <reason> — record a failed post-condition that is not a
# transport problem (e.g. wrong record count).
extra_fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  FAILED_TOOLS="${FAILED_TOOLS} $1"
  echo "FAIL  $1 — $2"
  return 0
}

# --------------------------------------------------------------------------- #
# Teardown trap                                                               #
# --------------------------------------------------------------------------- #
register_collection() { CREATED_COLLECTIONS+=("$1"); }

unregister_collection() {
  local keep=() c
  for c in ${CREATED_COLLECTIONS[@]+"${CREATED_COLLECTIONS[@]}"}; do
    [ "$c" = "$1" ] || keep+=("$c")
  done
  CREATED_COLLECTIONS=(${keep[@]+"${keep[@]}"})
}

teardown() {
  local rc=$?
  trap - EXIT INT TERM

  if [ "${#CREATED_COLLECTIONS[@]}" -gt 0 ]; then
    echo
    echo "teardown: dropping ${#CREATED_COLLECTIONS[@]} ephemeral collection(s)"
    # A mid-run failure can leave the process holding the ephemeral user
    # identity, which cannot drop a collection — reconnect as superuser first.
    call_tool connect "$(jq -cn --arg e "${POCKETBASE_ADMIN_EMAIL:-}" --arg p "${POCKETBASE_ADMIN_PASSWORD:-}" \
      '{as_:"superuser", email:$e, password:$p}')" >/dev/null 2>&1 || true
    local c
    for c in "${CREATED_COLLECTIONS[@]}"; do
      call_tool destroy_collection "$(jq -cn --arg n "$c" '{action:"delete", name:$n, confirm_name:$n}')" >/dev/null 2>&1 || true
      echo "  dropped ${c} (HTTP ${LAST_HTTP})"
    done
  fi

  cleanup_workdir
  exit "$rc"
}

# --------------------------------------------------------------------------- #
# Preconditions (skip, never fail)                                            #
# --------------------------------------------------------------------------- #
command -v curl >/dev/null 2>&1 || skip "curl is not on PATH"
command -v jq   >/dev/null 2>&1 || skip "jq is not on PATH"
command -v sed  >/dev/null 2>&1 || skip "sed is not on PATH"
[ -n "${POCKETBASE_ADMIN_EMAIL:-}" ]    || skip "POCKETBASE_ADMIN_EMAIL is not set"
[ -n "${POCKETBASE_ADMIN_PASSWORD:-}" ] || skip "POCKETBASE_ADMIN_PASSWORD is not set"

if ! (exec 3<>"/dev/tcp/${MCP_HOST}/${MCP_PORT}") 2>/dev/null; then
  skip "nothing is listening at ${BASE_URL} — start it with 'uv run pocketbase-mcp --http'"
fi

# --------------------------------------------------------------------------- #
# Run                                                                         #
# --------------------------------------------------------------------------- #
echo "curl MCP smoke → ${BASE_URL}"
trap teardown EXIT INT TERM

handshake

# ---- tool-list gate ------------------------------------------------------- #
EXPECTED_TOOLS='["bulk_write","connect","delete_records","describe_collection","describe_schema","destroy_collection","find_records","inspect_server","manage_auth","manage_collection","manage_files","read_logs","write_record"]'
NONDESTRUCTIVE_TOOLS='["bulk_write","connect","describe_collection","describe_schema","find_records","inspect_server","manage_auth","manage_collection","manage_files","read_logs","write_record"]'

rpc "tools/list" '{}'
[ "$LAST_HTTP" = "200" ] || fail "tools/list returned HTTP ${LAST_HTTP}"
GOT_TOOLS="$(jq -c '[.result.tools[].name] | sort' "$RPC_JSON")"

if [ "$GOT_TOOLS" = "$NONDESTRUCTIVE_TOOLS" ]; then
  skip "server registered 11 tools; set POCKETBASE_ENABLE_DESTRUCTIVE=1 on the server for full coverage"
fi

MISSING="$(jq -cn --argjson e "$EXPECTED_TOOLS" --argjson g "$GOT_TOOLS" '$e - $g')"
UNEXERCISED="$(jq -cn --argjson e "$EXPECTED_TOOLS" --argjson g "$GOT_TOOLS" '$g - $e')"
if [ "$MISSING" != "[]" ] || [ "$UNEXERCISED" != "[]" ]; then
  fail "tools/list disagrees with the harness — expected-but-missing: ${MISSING}, reported-but-unexercised: ${UNEXERCISED}"
fi
echo "tool-list gate: 13 tools, all covered"

# resources/list and prompts/list — handshake sanity only, HTTP 200.
rpc "resources/list" '{}'; [ "$LAST_HTTP" = "200" ] || fail "resources/list returned HTTP ${LAST_HTTP}"
rpc "prompts/list"   '{}'; [ "$LAST_HTTP" = "200" ] || fail "prompts/list returned HTTP ${LAST_HTTP}"
echo

# ---- 5. read-only tools ------------------------------------------------- #
call_tool inspect_server '{}'
check inspect_server

call_tool read_logs '{"per_page": 5}'
check read_logs

call_tool describe_schema '{}'
check describe_schema

# ---- 6. fixture + record tools ---------------------------------------- #
# Register before the create call returns so a partial create is still torn
# down; teardown tolerates an already-gone collection.
register_collection "$NOTES_COLLECTION"
call_tool manage_collection "$(jq -cn --arg n "$NOTES_COLLECTION" \
  '{action:"create", name:$n, collection_type:"base",
    fields:[{name:"title", type:"text"}, {name:"cover", type:"file", maxSelect:1}]}')"
check manage_collection

call_tool describe_collection "$(jq -cn --arg n "$NOTES_COLLECTION" '{collection:$n}')"
check describe_collection

call_tool write_record "$(jq -cn --arg n "$NOTES_COLLECTION" \
  '{collection:$n, action:"create", data:{title:"smoke note"}}')"
check write_record
RECORD_ID="$(envelope | jq -r '.data.id // empty')"

if [ -z "$RECORD_ID" ]; then
  extra_fail "write_record.capture" "could not read a record id from the create response"
else
  call_tool find_records "$(jq -cn --arg n "$NOTES_COLLECTION" --arg id "$RECORD_ID" \
    '{collection:$n, filter_template:"id = {:id}", filter_params:{id:$id}}')"
  check find_records
  FOUND="$(envelope | jq -r '.data.total_items // (.data.records | length) // 0')"
  [ "$FOUND" = "1" ] || extra_fail "find_records.count" "expected exactly 1 record, got ${FOUND}"

  call_tool write_record "$(jq -cn --arg n "$NOTES_COLLECTION" --arg id "$RECORD_ID" \
    '{collection:$n, action:"update", record_id:$id, data:{title:"smoke note (edited)"}}')"
  check write_record
fi

call_tool bulk_write "$(jq -cn --arg n "$NOTES_COLLECTION" \
  '{operations:[
      {collection:$n, action:"create", data:{title:"bulk one"}},
      {collection:$n, action:"create", data:{title:"bulk two"}}
    ]}')"
check bulk_write

# manage_files: upload a small local file into the fixture's file field, then
# ask for its URL. `local_path` is read on the SERVER host; when the harness
# runs under Git Bash on Windows, hand the server a native path.
COVER_LOCAL="${WORKDIR}/cover.txt"
printf 'pocketbase-mcp curl smoke cover %s\n' "$RPC_ID" > "$COVER_LOCAL"
COVER_SERVER_PATH="$COVER_LOCAL"
if command -v cygpath >/dev/null 2>&1; then
  COVER_SERVER_PATH="$(cygpath -w "$COVER_LOCAL")"
fi

if [ -z "${RECORD_ID:-}" ]; then
  extra_fail "manage_files" "skipped — no record id to attach a file to"
else
  call_tool manage_files "$(jq -cn --arg n "$NOTES_COLLECTION" --arg id "$RECORD_ID" --arg p "$COVER_SERVER_PATH" \
    '{action:"upload", collection:$n, record_id:$id, field:"cover", local_path:$p, filename:"cover.txt"}')"
  check manage_files
  STORED_COVER="$(envelope | jq -r '(.data.cover // .data.record.cover) | if type=="array" then .[0] else . end // empty')"
  if [ -z "$STORED_COVER" ]; then
    extra_fail "manage_files.url" "could not read the stored filename from the upload response"
  else
    call_tool manage_files "$(jq -cn --arg n "$NOTES_COLLECTION" --arg id "$RECORD_ID" --arg f "$STORED_COVER" \
      '{action:"url", collection:$n, record_id:$id, field:"cover", filename:$f}')"
    check manage_files
  fi
fi

# ---- 7. auth tools ---------------------------------------------------- #
register_collection "$USERS_COLLECTION"
call_tool manage_collection "$(jq -cn --arg n "$USERS_COLLECTION" \
  '{action:"create", name:$n, collection_type:"auth"}')"
check manage_collection

# NOTE: an auth-collection create needs `passwordConfirm`, which write_record's
# schema validation may reject as an unknown field. If this case FAILs with a
# VALIDATION_ERROR naming passwordConfirm, that is a server-side gap for the
# change's task 10.5 (validate_payload should accept passwordConfirm for auth
# collections), not a harness bug.
call_tool write_record "$(jq -cn --arg n "$USERS_COLLECTION" --arg e "$SMOKE_USER_EMAIL" --arg p "$SMOKE_USER_PASSWORD" \
  '{collection:$n, action:"create", data:{email:$e, password:$p, passwordConfirm:$p}}')"
check write_record

call_tool connect "$(jq -cn --arg n "$USERS_COLLECTION" --arg e "$SMOKE_USER_EMAIL" --arg p "$SMOKE_USER_PASSWORD" \
  '{as_:"user", collection:$n, email:$e, password:$p}')"
check connect

call_tool manage_auth "$(jq -cn --arg n "$USERS_COLLECTION" '{action:"refresh", collection:$n}')"
check manage_auth

# Restore superuser identity before the destructive cases.
call_tool connect "$(jq -cn --arg e "${POCKETBASE_ADMIN_EMAIL}" --arg p "${POCKETBASE_ADMIN_PASSWORD}" \
  '{as_:"superuser", email:$e, password:$p}')"
check connect

# ---- 8. destructive tools ------------------------------------------- #
if [ -n "${RECORD_ID:-}" ]; then
  call_tool delete_records "$(jq -cn --arg n "$NOTES_COLLECTION" --arg id "$RECORD_ID" \
    '{collection:$n, record_ids:[$id], confirm_count:1}')"
  check delete_records
else
  extra_fail "delete_records" "skipped — no record id to delete"
fi

call_tool destroy_collection "$(jq -cn --arg n "$USERS_COLLECTION" \
  '{action:"delete", name:$n, confirm_name:$n}')"
check destroy_collection
unregister_collection "$USERS_COLLECTION"

call_tool destroy_collection "$(jq -cn --arg n "$NOTES_COLLECTION" \
  '{action:"delete", name:$n, confirm_name:$n}')"
check destroy_collection
unregister_collection "$NOTES_COLLECTION"

# ---- 9. tally ------------------------------------------------------- #
echo
echo "${PASS_COUNT} passed, ${FAIL_COUNT} failed"
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "failed:${FAILED_TOOLS}"
  exit 1
fi
exit 0
