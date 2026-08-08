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
import stat
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks", "pretooluse-readonly.sh")

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
    proc = subprocess.run(
        ["bash", HOOK],
        input=event,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if proc.returncode == 2:
        return BLOCK, "exit 2"
    if proc.returncode == 0:
        out = (proc.stdout or "").strip()
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

    def _unreadable(d):
        p = os.path.join(d, "readonly.json")
        with open(p, "w") as fh:
            fh.write('{"active": true}')
        os.chmod(p, 0)
        return p
    if os.geteuid() != 0:  # root ignores the permission bit, so the case proves nothing
        yield ("unreadable-but-present marker denies", BLOCK, _unreadable)

    # ---- Controls: these MUST allow, or the suite is just a blanket blocker ----
    def _absent(d):
        return os.path.join(d, "does-not-exist.json")
    yield ("CONTROL: no marker allows (gate is opt-in)", ALLOW, _absent)
    yield ("CONTROL: active:false allows (explicit clear)", ALLOW, write('{"active": false}'))


def run_all():
    results = []
    for name, expected, setup in cases():
        d = tempfile.mkdtemp(prefix="readonly-selftest-")
        try:
            marker = setup(d)
            actual, detail = fire(marker)
        finally:
            shutil.rmtree(d, ignore_errors=True)
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
