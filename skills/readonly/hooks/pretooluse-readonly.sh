#!/usr/bin/env bash
# pretooluse-readonly.sh: PreToolUse hook that ENFORCES read-only session mode.
#
# Register it on the file-mutating tools (Edit|Write|MultiEdit|NotebookEdit). While
# the read-only marker is active it returns permissionDecision: deny, so the write
# never happens. This is the enforcement half of the `readonly` skill; the skill
# doc is the contract, this file is the mechanism.
#
# EXIT-CODE CONTRACT (Claude Code PreToolUse, and it is not intuitive):
#   exit 0 + {"permissionDecision":"deny"}   -> BLOCK
#   exit 2                                   -> BLOCK
#   any OTHER non-zero, crash, or no JSON    -> FAIL-OPEN, the tool runs
#
# That last line is the whole design problem. A gate that crashes on weird input
# fails open on exactly the input most likely to be hostile. So the rule here is:
#
#   marker ABSENT   -> exit 0 (inert). Read-only mode was never entered; this is
#                      the opt-in default and allowing writes is correct.
#   marker PRESENT  -> the operator asked for enforcement, so EVERY failure to
#                      evaluate it (unreadable, malformed, empty, wrong type,
#                      missing python3, crash) must DENY, never allow.
#
# Only an explicit, parseable {"active": false} re-allows writes. "I could not
# tell" is treated as "block", which is what fail-closed actually means.
#
# Override the marker path with READONLY_MARKER (the selftest uses this).

set +e

MARKER="${READONLY_MARKER:-$HOME/.claude/state/readonly.json}"

# Opt-in gate: no marker at all means read-only mode is off. Stay inert and cheap.
#
# Note -e, not -r: an EXISTING but unreadable marker must reach the fail-closed
# path below, not be mistaken for an absent one. The -L arm matters for the same
# reason and is easy to miss: -e follows symlinks, so a DANGLING symlink is
# "absent" to -e while plainly being a marker someone put there. Treating it as
# absent would let a broken marker silently disable the gate.
if [ ! -e "$MARKER" ] && [ ! -L "$MARKER" ]; then
  # "Not found" and "cannot look" are different answers, and the test above
  # returns the same result for both. If a directory on the path is not
  # searchable, an armed marker beneath it is invisible to us, and exiting 0
  # here would silently disarm the gate.
  #
  # Checking only the immediate parent is not enough: if an ANCESTOR is
  # unsearchable then `-d` on the parent also fails (the stat needs search
  # permission on ITS parent), so the check would pass by being equally blind.
  # Walk up instead until we reach the deepest directory we can actually stat.
  # Reaching a searchable one proves the path below it genuinely does not exist;
  # reaching an unsearchable one proves only that we cannot see.
  _probe=$(dirname "$MARKER")
  while :; do
    if [ -d "$_probe" ]; then
      [ -x "$_probe" ] || exit 2
      break
    fi
    _parent=$(dirname "$_probe")
    [ "$_parent" = "$_probe" ] && break
    _probe="$_parent"
  done
  exit 0
fi

# Past this point the operator has entered read-only mode. Any non-zero exit,
# including a crash, becomes exit 2 (BLOCK). A blanket `trap exit 0` here would
# reintroduce the fail-open hole this hook exists to close.
trap 'rc=$?; [ "$rc" -eq 0 ] && exit 0; exit 2' EXIT

command -v python3 >/dev/null 2>&1 || exit 2

# Cap the event before it becomes an environment variable. The payload is used
# ONLY to name the tool and path in the deny message, but an oversized env block
# can make execve fail with E2BIG, and the fail-closed trap would then turn that
# into a BLOCK even for a marker that says {"active": false}. Capping keeps the
# decoration useful without letting payload size change the decision.
INPUT=$(head -c 16384 2>/dev/null)

READONLY_EVENT="$INPUT" python3 - "$MARKER" <<'PY'
import json
import os
import sys

marker_path = sys.argv[1]

try:
    with open(marker_path) as fh:
        marker = json.load(fh)
except Exception:
    sys.exit(1)                 # unreadable / malformed / empty -> trap -> exit 2 -> BLOCK

if not isinstance(marker, dict):
    sys.exit(1)                 # JSON that is not an object (list, string, number) -> BLOCK

active = marker.get("active")

if active is False:
    sys.exit(0)                 # explicitly cleared -> allow writes
if active is not True:
    sys.exit(1)                 # missing / null / "true" / 1 / anything else -> BLOCK

# Marker is active: deny the write. The event payload is best-effort decoration
# only; a malformed event must never downgrade the decision.
try:
    event = json.loads(os.environ.get("READONLY_EVENT") or "{}")
except Exception:
    event = {}
if not isinstance(event, dict):
    event = {}

tool = event.get("tool_name") or "a file-mutating tool"
tool_input = event.get("tool_input")
target = None
if isinstance(tool_input, dict):
    target = tool_input.get("file_path")
target = target or "<file>"

reason = marker.get("reason") or "this session is in READ-ONLY mode"

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "[readonly] {tool} on {target} blocked: {reason}. "
            "Clear it with `readonly-mode.sh off` (or remove {path})."
        ).format(tool=tool, target=target, reason=reason, path=marker_path),
    }
}))
sys.exit(0)
PY
