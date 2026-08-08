#!/usr/bin/env bash
# readonly-mode.sh: set / clear / report the read-only session marker that
# pretooluse-readonly.sh enforces.
#
# The hook is INERT until this marker exists, so this script is the caller half
# of the rail. Do not hand-write the marker JSON; a malformed marker is treated
# as "enforce" by the hook (fail-closed), which blocks writes until cleared.
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
#
# DESIGN NOTE, and it is the whole point of this file:
# every command must report the TRUE post-condition, never its intent. A helper
# that prints "ON" when the marker was not written, or "OFF" when it was not
# removed, is worse than no helper: the operator proceeds believing a control is
# armed (or released) when it is not. So `on` re-reads the marker after writing,
# `off` verifies the marker is gone, and `status` reports what the HOOK will
# actually do rather than a guess.

set -uo pipefail

MARKER="${READONLY_MARKER:-$HOME/.claude/state/readonly.json}"
cmd="${1:-status}"

need_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "readonly: ERROR, python3 is required" >&2
    exit 1
  fi
}

# Report what the hook would do, from the marker itself.
#   0 = ON  (hook denies writes)
#   1 = OFF (hook allows writes: absent, or explicit {"active": false})
#   2 = ON via fail-closed (present but unevaluable, hook denies)
marker_state() {
  if [ ! -e "$MARKER" ] && [ ! -L "$MARKER" ]; then
    return 1
  fi
  python3 - "$MARKER" <<'PY'
import json
import sys

try:
    with open(sys.argv[1]) as fh:
        marker = json.load(fh)
except Exception:
    sys.exit(2)
if not isinstance(marker, dict):
    sys.exit(2)
active = marker.get("active")
if active is True:
    sys.exit(0)
if active is False:
    sys.exit(1)
sys.exit(2)
PY
}

case "$cmd" in
  on)
    need_python
    reason="${2:-read-only audit/research mode}"

    if ! mkdir -p "$(dirname "$MARKER")" 2>/dev/null; then
      echo "readonly: FAILED to create $(dirname "$MARKER"); read-only mode is NOT armed" >&2
      exit 1
    fi

    # python for correct JSON escaping of an arbitrary reason string.
    #
    # Written to a temp file in the same directory and renamed into place, never
    # opened directly with "w". A direct open truncates BEFORE the content is
    # committed, so a failure partway (disk full, quota, interrupt) would leave a
    # present-but-empty marker. That state is not harmless: the hook fails closed
    # on it and blocks every write, while this script would be reporting "NOT
    # armed". Rename is atomic on the same filesystem, so the marker is either
    # the previous state or a complete new one, and never a torn one.
    if ! READONLY_REASON="$reason" python3 - "$MARKER" <<'PY'
import json
import os
import sys
import tempfile

target = sys.argv[1]
directory = os.path.dirname(target) or "."
fd, tmp = tempfile.mkstemp(dir=directory, prefix=".readonly-", suffix=".tmp")
try:
    with os.fdopen(fd, "w") as fh:
        json.dump({"active": True, "reason": os.environ.get("READONLY_REASON", "")}, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
except Exception:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise
PY
    then
      echo "readonly: FAILED to write $MARKER; read-only mode is NOT armed" >&2
      exit 1
    fi

    # Re-read rather than trust the write. This is the difference between
    # "I ran a command" and "the control is armed".
    marker_state
    case $? in
      0) echo "readonly: ON ($reason) -> $MARKER"
         echo "  REMEMBER: run 'readonly-mode.sh off' when done; a stranded marker blocks all writes." ;;
      *) echo "readonly: FAILED, marker at $MARKER did not read back as active; read-only mode is NOT armed" >&2
         exit 1 ;;
    esac
    ;;

  off)
    rm -f "$MARKER" 2>/dev/null
    # Verify the post-condition. rm -f cannot remove a directory and exits 0 on a
    # missing file, so its exit code alone proves nothing about what remains.
    if [ -e "$MARKER" ] || [ -L "$MARKER" ]; then
      echo "readonly: FAILED to clear $MARKER; it still exists, so the hook KEEPS BLOCKING writes" >&2
      if [ -d "$MARKER" ]; then
        echo "  it is a directory; remove it with: rmdir '$MARKER'  (or rm -r if it has contents)" >&2
      fi
      exit 1
    fi
    echo "readonly: OFF (marker cleared) -> $MARKER"
    ;;

  status)
    need_python
    marker_state
    case $? in
      0) echo "readonly: ON -> $MARKER"
         echo "  the hook will DENY Edit/Write/MultiEdit/NotebookEdit" ;;
      1) if [ -e "$MARKER" ] || [ -L "$MARKER" ]; then
           echo "readonly: OFF (marker present with \"active\": false) -> $MARKER"
         else
           echo "readonly: OFF (no marker) -> $MARKER"
         fi
         echo "  the hook will ALLOW writes" ;;
      *) echo "readonly: ON (fail-closed: marker present but not evaluable) -> $MARKER"
         echo "  the hook will DENY writes until this marker is fixed or removed" ;;
    esac
    ;;

  *)
    echo "usage: readonly-mode.sh {on [reason]|off|status}" >&2
    exit 2
    ;;
esac
