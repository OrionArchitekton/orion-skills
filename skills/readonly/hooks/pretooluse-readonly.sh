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
      [ -x "$_probe" ] || { echo "[readonly] cannot search $_probe, so the marker $MARKER may be armed but unreadable; file edits are blocked (fail-closed). Fix the directory permissions or run readonly-mode.sh status." >&2; exit 2; }
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
# The message goes to stderr, which the harness shows the agent on exit 2, so a
# fail-closed block always says which marker and how to recover.
trap 'rc=$?; [ "$rc" -eq 0 ] && exit 0; echo "[readonly] marker $MARKER is present but could not be evaluated; file edits are blocked (fail-closed). Inspect it with readonly-mode.sh status, clear it with readonly-mode.sh off." >&2; exit 2' EXIT

command -v python3 >/dev/null 2>&1 || exit 2

# The decision never depends on the event payload: it only names the tool and path
# in the deny message. So nothing reads stdin before the marker is judged. A
# blocking read there (even `head -c`) lets a caller that stalls mid-write hold
# the hook until the harness kills it, and a killed hook fails open. The caller's
# stdin reaches python on fd 3 (fd 0 carries the script), where it is read with
# a deadline, only once the answer is already "deny".
#
# -I (isolated): the harness runs hooks from the session cwd, and plain `python3 -`
# puts that directory first on sys.path, so a json.py in an audited repo would
# replace the stdlib, disable the gate, and run on every edit attempt. -I also
# ignores PYTHON* env vars and the user site directory.
python3 -I - "$MARKER" 3<&0 <<'PY'
import json
import os
import select
import stat
import sys
import time

EVENT_FD = 3
EVENT_MAX_BYTES = 16 * 1024     # decoration only; a Write payload can be megabytes
EVENT_READ_SEC = 1.0            # a well-behaved caller has already closed stdin
DRAIN_SEC = 2.0


def read_with_deadline(fd, keep_bytes, seconds):
    """Read fd until EOF, keep_bytes kept, or the deadline; never block past it.
    keep_bytes=0 discards everything read (a drain)."""
    kept = bytearray()
    deadline = time.monotonic() + seconds
    try:
        os.set_blocking(fd, False)
    except OSError:
        return b""              # no usable stdin: nothing to read or drain
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            break
        try:
            ready, _, _ = select.select([fd], [], [], left)
        except (OSError, ValueError):
            break
        if not ready:
            break
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            continue
        except OSError:
            break
        if not chunk:
            break               # EOF
        if keep_bytes:
            kept += chunk[: keep_bytes - len(kept)]
            if len(kept) >= keep_bytes:
                break
    return bytes(kept)

marker_path = sys.argv[1]

# Evaluation must finish, or the harness kills the hook and the write runs anyway.
# A plain open() of a FIFO blocks until a writer appears, and a character device
# such as /dev/zero never ends. Open without blocking, then judge the descriptor
# itself (not the path, which could be swapped in between): only a regular file
# is read; anything else denies.
#
# stat() first, which never opens the node: O_NONBLOCK is not a guarantee for
# every device type, so a pipe or device is denied before any open() can stall.
# The descriptor check below still guards a path swapped between the two calls.
try:
    if not stat.S_ISREG(os.stat(marker_path).st_mode):
        sys.exit(1)             # FIFO, device, socket, directory -> BLOCK without opening
except OSError:
    sys.exit(1)                 # missing target / unsearchable -> BLOCK
try:
    fd = os.open(marker_path, os.O_RDONLY | os.O_NONBLOCK)
except Exception:
    sys.exit(1)                 # missing target / unreadable -> trap -> exit 2 -> BLOCK
try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        sys.exit(1)             # FIFO, device, socket, directory -> BLOCK without reading
    # A real marker is a few bytes. Read one past the cap so an oversized file
    # (even a sparse one that would take minutes to read) denies immediately.
    MARKER_MAX_BYTES = 64 * 1024
    with os.fdopen(fd, "rb") as fh:
        data = fh.read(MARKER_MAX_BYTES + 1)
    if len(data) > MARKER_MAX_BYTES:
        sys.exit(1)             # oversized -> BLOCK without reading the rest
    marker = json.loads(data.decode("utf-8"))
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
# only; a malformed, truncated, or never-finished event must never downgrade the
# decision.
try:
    event = json.loads(read_with_deadline(EVENT_FD, EVENT_MAX_BYTES, EVENT_READ_SEC) or b"{}")
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
}), flush=True)
# Drain what the caller is still writing so a large payload does not meet a closed
# pipe, bounded so a stalled caller cannot keep this process alive.
read_with_deadline(EVENT_FD, 0, DRAIN_SEC)
sys.exit(0)
PY
