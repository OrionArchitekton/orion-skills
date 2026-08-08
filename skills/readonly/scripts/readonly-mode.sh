#!/usr/bin/env bash
# readonly-mode.sh: set / clear / report the read-only session marker that
# pretooluse-readonly.sh enforces.
#
# The hook is INERT until this marker exists, so this script is the caller half
# of the rail. Do not hand-write the marker JSON; a malformed marker is treated
# as "enforce" by the hook (fail-closed), which will block writes until cleared.
#
# Usage:
#   readonly-mode.sh on  [reason]   enter read-only mode (blocks ALL writes)
#   readonly-mode.sh off            leave read-only mode (allows writes)
#   readonly-mode.sh status         report current mode
#
# ALWAYS clear when done. The marker is a file on disk, not session state, so a
# stranded active marker keeps blocking writes in the NEXT session too.
#
# No secret ever passes through here: `reason` is a free-text label only.
#
# Override the marker path with READONLY_MARKER (the selftest uses this).

set -uo pipefail

MARKER="${READONLY_MARKER:-$HOME/.claude/state/readonly.json}"
mkdir -p "$(dirname "$MARKER")" 2>/dev/null

cmd="${1:-status}"

case "$cmd" in
  on)
    reason="${2:-read-only audit/research mode}"
    if ! command -v python3 >/dev/null 2>&1; then
      echo "readonly: ERROR, python3 is required to write the marker safely" >&2
      exit 1
    fi
    # python for correct JSON escaping of an arbitrary reason string.
    READONLY_REASON="$reason" python3 - "$MARKER" <<'PY'
import json
import os
import sys

with open(sys.argv[1], "w") as fh:
    json.dump({"active": True, "reason": os.environ.get("READONLY_REASON", "")}, fh)
PY
    echo "readonly: ON ($reason) -> $MARKER"
    echo "  REMEMBER: run 'readonly-mode.sh off' when done; a stranded marker blocks all writes."
    ;;
  off)
    rm -f "$MARKER"
    echo "readonly: OFF (marker cleared) -> $MARKER"
    ;;
  status)
    if [ ! -e "$MARKER" ]; then
      echo "readonly: OFF (no marker) -> $MARKER"
    elif python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("active") is True else 1)' "$MARKER" 2>/dev/null; then
      echo "readonly: ON -> $MARKER"
    else
      echo "readonly: ON (marker present but not parseable as inactive; the hook fails CLOSED and will block writes) -> $MARKER"
    fi
    ;;
  *)
    echo "usage: readonly-mode.sh {on [reason]|off|status}" >&2
    exit 2
    ;;
esac
