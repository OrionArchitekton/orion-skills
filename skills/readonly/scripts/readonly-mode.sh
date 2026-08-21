#!/usr/bin/env bash
# readonly-mode.sh: set / clear / report the read-only session marker that
# pretooluse-readonly.sh enforces.
#
# The hook is INERT until this marker exists, so this script is the caller half
# of the rail. Do not hand-write the marker JSON; a malformed marker is treated
# as "enforce" by the hook (fail-closed), which blocks writes until cleared.
#
# Usage:
#   readonly-mode.sh on  [reason]   enter read-only mode (the hook denies the
#                                   file-editing tools: Edit, Write, MultiEdit,
#                                   NotebookEdit; Bash is NOT covered, see
#                                   "What this does NOT do" in SKILL.md)
#   readonly-mode.sh off            leave read-only mode (allows file edits)
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

# Report what the hook would do, by ASKING THE HOOK.
#
# An earlier version re-derived this from the marker itself, and review found
# three defects in the gap between the two implementations: with an inaccessible
# parent directory the helper said OFF/ALLOW while the hook denied, and `off`
# reported a clear that had not happened. Any second implementation of a gate's
# logic drifts from it; the fix is to have exactly one, and query it.
#
# Interpreting the hook's PreToolUse contract:
#   exit 0 + deny JSON -> ON (marker active)
#   exit 2             -> ON via fail-closed (present but unevaluable, or unseeable)
#   exit 0, no output  -> OFF (writes allowed)
#
#   0 = ON  (hook denies writes)
#   1 = OFF (hook allows writes: absent, or explicit {"active": false})
#   2 = ON via fail-closed (hook denies without a marker it could read)
HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/pretooluse-readonly.sh"

marker_state() {
  if [ ! -x "$HOOK" ] && [ ! -f "$HOOK" ]; then
    echo "readonly: ERROR, cannot find the enforcement hook at $HOOK" >&2
    return 3
  fi
  local out rc
  out=$(printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"<status probe>"}}' \
        | READONLY_MARKER="$MARKER" bash "$HOOK" 2>/dev/null)
  rc=$?
  if [ "$rc" -eq 2 ]; then
    return 2
  fi
  if [ "$rc" -ne 0 ]; then
    # Any other non-zero is fail-open at the harness, so the hook is NOT denying.
    return 1
  fi
  case "$out" in
    *'"permissionDecision"'*'"deny"'*) return 0 ;;
    *) return 1 ;;
  esac
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
      # The failed write does not prove file edits are allowed: an unwritable or
      # directory marker path is exactly what the hook fail-closes on, so ask
      # the hook which state the operator is actually in.
      marker_state
      case $? in
        0|2) echo "readonly: FAILED to write $MARKER; arming did not complete cleanly," >&2
             echo "  but the hook is DENYING file edits (fail-closed on the existing path)." >&2
             echo "  Inspect the path, or clear it with 'readonly-mode.sh off'." >&2 ;;
        *)   echo "readonly: FAILED to write $MARKER; read-only mode is NOT armed" >&2 ;;
      esac
      exit 1
    fi

    # Re-read rather than trust the write. This is the difference between
    # "I ran a command" and "the control is armed".
    marker_state
    case $? in
      0) echo "readonly: ON ($reason) -> $MARKER"
         echo "  REMEMBER: run 'readonly-mode.sh off' when done; a stranded marker keeps"
         echo "  denying file edits in later sessions too." ;;
      2) echo "readonly: FAILED, marker at $MARKER is present but not evaluable;" >&2
         echo "  the hook is DENYING file edits (fail-closed), not armed as requested." >&2
         echo "  Inspect the marker, or clear it with 'readonly-mode.sh off'." >&2
         exit 1 ;;
      *) echo "readonly: FAILED, marker at $MARKER did not read back as active; read-only mode is NOT armed" >&2
         exit 1 ;;
    esac
    ;;

  off)
    rm -f "$MARKER" 2>/dev/null
    # Verify the post-condition against the hook, not against our own guess.
    # `rm -f` exits 0 on a missing file and cannot unlink a directory, so its
    # exit code proves nothing; and an `-e`/`-L` probe cannot see a marker whose
    # directory is unsearchable, which is precisely the state the hook denies on.
    # Asking the hook is the only check that cannot disagree with enforcement.
    marker_state
    case $? in
      1) echo "readonly: OFF (marker cleared) -> $MARKER" ;;
      0|2)
        echo "readonly: FAILED to clear $MARKER; the hook STILL BLOCKS writes" >&2
        if [ -d "$MARKER" ]; then
          echo "  it is a directory; remove it with: rmdir '$MARKER'  (or rm -r if it has contents)" >&2
        elif [ ! -e "$MARKER" ] && [ ! -L "$MARKER" ]; then
          echo "  the marker is not visible from here, so a directory on its path is likely" >&2
          echo "  unsearchable; fix permissions on $(dirname "$MARKER") and its ancestors, then retry" >&2
        fi
        exit 1 ;;
      *) echo "readonly: could not determine state after clearing; assume writes are still blocked" >&2
         exit 1 ;;
    esac
    ;;

  status)
    # Deliberately no python3 precondition here. If python3 is missing the hook
    # itself denies (exit 2) whenever a marker is present, and reporting that
    # honestly is more useful than refusing to answer.
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
      2) echo "readonly: ON (fail-closed) -> $MARKER"
         echo "  the hook will DENY writes: the marker is present but not evaluable,"
         echo "  or a directory on its path is unsearchable so it cannot be read" ;;
      *) echo "readonly: UNKNOWN, the enforcement hook could not be run" >&2
         echo "  treat writes as unprotected until this is resolved" >&2
         exit 1 ;;
    esac
    ;;

  *)
    echo "usage: readonly-mode.sh {on [reason]|off|status}" >&2
    exit 2
    ;;
esac
