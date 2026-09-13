#!/usr/bin/env python3
"""readonly self-test: prove the PreToolUse hook actually DENIES.

Run:  python3 selftest.py     (exit 0 = every case behaved, 1 = a case failed)

Requires nothing but python3 and bash. It fires the REAL hook script with REAL
PreToolUse payloads against a temporary marker, then classifies what the hook
did from its own exit code and stdout. Nothing here is mocked, and nothing
trusts a description of the hook's behavior.

Why it is shaped this way
-------------------------
A gate is unproven until you have watched it block, and "it did not complain" is
not evidence: a gate that is broken and a gate with nothing to catch produce the
identical silence. So every case below asserts a POSITIVE observation, and the
suite includes allow-cases as a control. Without those, a hook that blocked
everything unconditionally would pass a block-only suite while being useless.

The Claude Code PreToolUse exit contract is what makes this subtle:

    exit 0 + {"permissionDecision": "deny"}   -> BLOCK
    exit 2                                    -> BLOCK
    anything else (exit 1, crash, no JSON)    -> FAIL-OPEN, the tool runs

So "the hook errored" is NOT "the hook blocked". Cases 2 through 10 below are
all malformed-marker shapes, and each one must still land on BLOCK.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks", "pretooluse-readonly.sh")

# Generous for a hook that only reads a tiny marker; a hang must not look like a block.
HOOK_TIMEOUT_SEC = 10

# Descriptors a case must keep open while the hook runs; closed after each case.
_HELD_FDS: list[int] = []

BLOCK = "BLOCK"
ALLOW = "ALLOW"

SAMPLE_EVENT = json.dumps({
    "tool_name": "Write",
    "tool_input": {"file_path": "/tmp/should-never-be-written.txt"},
})


def fire(marker_path: str, event: str = SAMPLE_EVENT) -> tuple[str, str]:
    """Run the hook for real. Return (verdict, detail)."""
    env = dict(os.environ)
    env["READONLY_MARKER"] = marker_path
    # Own session so a hung hook's whole process group (bash AND its python3 child)
    # can be killed; killing only bash would orphan a child blocked on the marker.
    proc = subprocess.Popen(
        ["bash", HOOK],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, _stderr = proc.communicate(event, timeout=HOOK_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        # A hook the harness has to kill produces neither exit 2 nor a deny, so a
        # hang is fail-open, not a slow block.
        return ALLOW, "timed out after %ss (fail-open when the harness kills it)" % HOOK_TIMEOUT_SEC
    if proc.returncode == 2:
        return BLOCK, "exit 2"
    if proc.returncode == 0:
        out = (stdout or "").strip()
        if not out:
            return ALLOW, "exit 0, no output"
        try:
            payload = json.loads(out)
        except Exception:
            # exit 0 with unparseable stdout is NOT a deny; the harness would run the tool.
            return ALLOW, "exit 0, unparseable stdout"
        decision = (payload.get("hookSpecificOutput") or {}).get("permissionDecision")
        if decision == "deny":
            return BLOCK, "exit 0 + permissionDecision deny"
        return ALLOW, "exit 0, decision=%r" % (decision,)
    # Any other non-zero is fail-open under the harness contract.
    return ALLOW, "exit %d (fail-open under the PreToolUse contract)" % proc.returncode


def cases():
    """Yield (name, expected_verdict, setup) where setup(dir) -> marker path."""

    def write(content):
        def _setup(d):
            p = os.path.join(d, "readonly.json")
            with open(p, "w") as fh:
                fh.write(content)
            return p
        return _setup

    yield ("active marker denies the write", BLOCK,
           write('{"active": true, "reason": "audit in progress"}'))
    yield ("malformed JSON denies (cannot evaluate)", BLOCK, write("{not json at all"))
    yield ("empty marker denies", BLOCK, write(""))
    yield ("null active denies", BLOCK, write('{"active": null}'))
    yield ("string \"true\" denies (wrong type)", BLOCK, write('{"active": "true"}'))
    yield ("integer 1 denies (wrong type)", BLOCK, write('{"active": 1}'))
    yield ("JSON array denies (not an object)", BLOCK, write("[]"))
    yield ("missing active key denies", BLOCK, write('{"reason": "no active field"}'))

    def _dir(d):
        p = os.path.join(d, "readonly.json")
        os.mkdir(p)
        return p
    yield ("marker that is a directory denies", BLOCK, _dir)

    def _fifo(d):
        # Opening a FIFO for reading blocks until a writer appears, so a hook that
        # just open()s the marker hangs until the harness kills it: fail-open.
        p = os.path.join(d, "readonly.json")
        os.mkfifo(p)
        return p
    yield ("FIFO marker denies without hanging", BLOCK, _fifo)

    def _pipe_claiming_cleared(d):
        # A FIFO whose buffer already holds a valid "cleared" marker. Opened
        # read-write it needs no separate writer, so the content is there when the
        # hook reads. A hook that parses anything it can open would ALLOW writes
        # through a marker that is not a file at all; only a regular file counts.
        p = os.path.join(d, "readonly.json")
        os.mkfifo(p)
        fd = os.open(p, os.O_RDWR | os.O_NONBLOCK)
        os.write(fd, b'{"active": false}')
        _HELD_FDS.append(fd)
        return p
    yield ("FIFO holding a cleared marker still denies", BLOCK, _pipe_claiming_cleared)

    def _endless_device(d):
        # A marker linked to a character device that never ends: reading it to
        # parse JSON would run until the harness kills the hook.
        p = os.path.join(d, "readonly.json")
        os.symlink("/dev/zero", p)
        return p
    if os.path.exists("/dev/zero"):
        yield ("marker linked to an endless device denies without hanging", BLOCK, _endless_device)

    def _oversized(d):
        # A regular file far larger than any marker (sparse, so it costs no disk):
        # parsing it whole would outlast the harness timeout.
        p = os.path.join(d, "readonly.json")
        with open(p, "wb") as fh:
            fh.truncate(64 * 1024 ** 3)
        return p
    yield ("oversized marker denies without reading it all", BLOCK, _oversized)

    # An oversized marker that parses as a CLEARED marker: json.loads accepts the
    # trailing whitespace, so a hook that read (or parsed a prefix of) the whole
    # file would ALLOW writes. The size cap must deny regardless of content.
    yield ("oversized marker that parses as cleared still denies", BLOCK,
           write('{"active": false}' + " " * (70 * 1024)))

    def _dangling_symlink(d):
        # `test -e` follows symlinks, so a dangling link looks ABSENT to it while
        # obviously being a marker someone placed. Treating it as absent would
        # silently disable the gate, so the hook checks -L as well.
        p = os.path.join(d, "readonly.json")
        os.symlink(os.path.join(d, "no-such-target.json"), p)
        return p
    yield ("dangling symlink marker denies", BLOCK, _dangling_symlink)

    def _unreadable(d):
        p = os.path.join(d, "readonly.json")
        with open(p, "w") as fh:
            fh.write('{"active": true}')
        os.chmod(p, 0)
        return p
    if os.geteuid() != 0:  # root ignores the permission bit, so the case proves nothing
        yield ("unreadable-but-present marker denies", BLOCK, _unreadable)

    def _unsearchable_parent(d):
        # "Not found" and "cannot look" are different answers that `test -e`
        # collapses into one. With the parent dir unsearchable, an ARMED marker
        # inside it is invisible, so treating that as absent would disarm the
        # gate exactly when the filesystem is in a strange state.
        parent = os.path.join(d, "state")
        os.mkdir(parent)
        p = os.path.join(parent, "readonly.json")
        with open(p, "w") as fh:
            fh.write('{"active": true}')
        os.chmod(parent, 0)
        return p
    if os.geteuid() != 0:
        yield ("marker hidden by an unsearchable parent denies", BLOCK, _unsearchable_parent)

    def _unsearchable_ancestor(d):
        # The immediate parent is fine; a GRANDparent is not. Checking only the
        # immediate parent passes here by being equally blind: `-d` on the parent
        # needs search permission on the grandparent, so it also fails, and the
        # guard never fires. The hook walks up to the deepest directory it can
        # actually stat instead.
        top = os.path.join(d, "outer")
        inner = os.path.join(top, "state")
        os.makedirs(inner)
        p = os.path.join(inner, "readonly.json")
        with open(p, "w") as fh:
            fh.write('{"active": true}')
        os.chmod(top, 0)
        return p
    if os.geteuid() != 0:
        yield ("marker hidden by an unsearchable ANCESTOR denies", BLOCK, _unsearchable_ancestor)

    # ---- Controls: these MUST allow, or the suite is just a blanket blocker ----
    def _absent(d):
        return os.path.join(d, "does-not-exist.json")
    yield ("CONTROL: no marker allows (gate is opt-in)", ALLOW, _absent)
    yield ("CONTROL: active:false allows (explicit clear)", ALLOW, write('{"active": false}'))


def _cleanup(root: str) -> None:
    # Two cases deliberately chmod things to 0, and rmtree cannot descend into a
    # mode-0 directory. With ignore_errors it would fail silently and leak temp
    # dirs, so restore permissions on the way out first.
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        for name in dirnames + filenames:
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IRWXU)
            except OSError:
                pass
    shutil.rmtree(root, ignore_errors=True)


def run_all():
    results = []
    for name, expected, setup in cases():
        d = tempfile.mkdtemp(prefix="readonly-selftest-")
        try:
            marker = setup(d)
            actual, detail = fire(marker)
        finally:
            while _HELD_FDS:
                os.close(_HELD_FDS.pop())
            try:
                os.chmod(d, stat.S_IRWXU)
            except OSError:
                pass
            _cleanup(d)
        results.append((name, expected, actual, detail, expected == actual))
    return results


def main() -> int:
    if not os.path.exists(HOOK):
        print("FAIL: hook not found at %s" % HOOK)
        return 1

    results = run_all()
    failed = 0
    for name, expected, actual, detail, ok in results:
        print("%-4s %-52s expected=%-5s got=%-5s (%s)"
              % ("ok" if ok else "FAIL", name, expected, actual, detail))
        if not ok:
            failed += 1

    blocked = sum(1 for _, e, _, _, _ in results if e == BLOCK)
    allowed = sum(1 for _, e, _, _, _ in results if e == ALLOW)
    print("\n%d case(s): %d must block, %d must allow, %d failed"
          % (len(results), blocked, allowed, failed))
    if allowed == 0:
        print("FAIL: suite has no allow-control, so it cannot tell enforcement "
              "apart from a blanket blocker")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
