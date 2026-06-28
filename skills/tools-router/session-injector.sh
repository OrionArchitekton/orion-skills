#!/usr/bin/env bash
# session-injector.sh — thin, FAIL-OPEN session-start injector for the tools-router
# (illustrative skeleton — adapt the table path + the injection mechanism to your harness).
#
# It does ZERO probing: it reads the PRE-RENDERED table the periodic recon produced and
# emits it as session context. The recon earns "assume authed"; this hook just serves the
# cached artifact cheaply. Any error exits 0 — a session must NEVER block on the index.
trap 'exit 0' EXIT
set +e

TABLE="${TOOLS_TABLE:-$HOME/.config/your-harness/tools-table.md}"
FLAGS="${TOOLS_FLAGS:-$HOME/.config/your-harness/tools-flags.md}"

[ -r "$TABLE" ] || exit 0                       # missing -> inject nothing, fail open
BODY="$(sed '/^<!--/d' "$TABLE")"               # strip the generated-maintenance comment
[ -n "$BODY" ] || exit 0                         # malformed/empty -> fail open

BANNER=""
# Staleness: a table older than (recon interval x a few) means the periodic recon missed.
if [ -n "$(find "$TABLE" -mtime +10 2>/dev/null)" ]; then
  BANNER="NOTE: tools index >10d old — the recon job may not be firing; re-run it. "
fi
# Flags: surface unauthenticated tools / dedup recs the recon recorded.
if [ -r "$FLAGS" ] && [ -s "$FLAGS" ]; then
  BANNER="${BANNER}NOTE: tool flags present — see the flags file. "
fi

# Emit however your harness ingests session context (stdout, a JSON envelope, a file...).
printf '%s\n\n%s\n' "${BANNER}[tools] prefer a WORKING CLI over its MCP; re-probe if a call fails." "$BODY"
exit 0
