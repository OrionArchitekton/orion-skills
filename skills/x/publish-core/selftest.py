#!/usr/bin/env python3
"""publish-core self-test — adversarial checks for the safety primitives.

Run: python3 selftest.py    (exit 0 = all pass, 1 = a check failed)

Covers:
  * redactor BUILT-IN universals: a planted secret + RFC-1918 IP + internal host
    + absolute home path are detected, the verdict is ABSTAIN (fail-closed), and
    redact() removes them. These are always-on and need no customization.
  * redactor CUSTOM loader: a user denylist file (your org's nouns) is loaded and
    applied — proven with a temp file, so this test is stable no matter how you
    customize ~/.claude/config/x-denylist.txt.
  * cap_ledger: increments to the cap then BLOCKS (read-prior-at-entry). Temp
    ledger — never the real one.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import common
import redactor

PASS, FAIL = "PASS", "FAIL"
_results = []


def _check(name, ok, detail=""):
    _results.append((name, ok))
    print(f"  [{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def test_redactor_builtin():
    print("redactor (built-in universals):")
    samples = {
        "internal-ip": "the box answered at 10.1.2.3 over the VPN",
        "internal-host": "the API was on localhost:8080 in dev",
        "internal-path": "stack trace points at /home/alice/project/run.py",
        "secret": "token ghp_AbCdEf0123456789ghIjKlMnOpQrStUv leaked into a log",
    }
    for expected, text in samples.items():
        verdict, hits = redactor.decision(text)
        got = {c for c, _ in hits}
        _check(f"detect[{expected}]", expected in got, f"verdict={verdict} classes={sorted(got)}")
        red = redactor.redact(text)
        _check(f"strip[{expected}]", "[REDACTED:" in red and expected in red, f"-> {red!r}")

    verdict, _ = redactor.decision(" ; ".join(samples.values()))
    _check("abstain-on-dirty", verdict == "ABSTAIN")

    clean = ("Shipped a read-only rail for an autonomous agent: a marker file plus a "
             "PreToolUse hook that denies writes. Enforce at the tool boundary, not the prompt.")
    verdict, hits = redactor.decision(clean)
    _check("publish-on-clean", verdict == "PUBLISH", f"hits={[h[0] for h in hits]}")


def test_redactor_custom_loader():
    print("redactor (custom denylist file):")
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "x-denylist.txt"
        cfg.write_text("# my org\n\\bACME\\b\nmybox-01\n")
        orig = redactor.CUSTOM_PATH
        redactor.CUSTOM_PATH = cfg
        try:
            v1, h1 = redactor.decision("we billed ACME this quarter")
            _check("custom-term-acronym", v1 == "ABSTAIN" and any(c == "custom" for c, _ in h1))
            v2, h2 = redactor.decision("deployed to mybox-01 overnight")
            _check("custom-term-host", v2 == "ABSTAIN" and any(c == "custom" for c, _ in h2))
            # a word NOT in the custom file (and not universal) still publishes
            v3, _ = redactor.decision("we shipped the feature on schedule")
            _check("non-listed-publishes", v3 == "PUBLISH")
        finally:
            redactor.CUSTOM_PATH = orig


def test_cap_ledger():
    print("cap_ledger:")
    with tempfile.TemporaryDirectory() as td:
        orig = common.CAPS_PATH
        common.CAPS_PATH = Path(td) / "caps.json"
        try:
            import importlib
            import cap_ledger
            importlib.reload(cap_ledger)
            cap = common.CAPS["x"]
            _check("starts-empty", cap_ledger.current("x") == 0)
            counts = [cap_ledger.increment("x") for _ in range(cap)]
            _check("increments-monotonic", counts == list(range(1, cap + 1)), f"{counts}")
            _check("at-cap-after-N", cap_ledger.at_cap("x") is True, f"current={cap_ledger.current('x')}/{cap}")
            rc = cap_ledger.main(["incr", "x"])
            _check("blocks-past-cap (exit 4)", rc == 4 and cap_ledger.current("x") == cap, f"rc={rc}")
        finally:
            common.CAPS_PATH = orig


def main(argv) -> int:
    print("=== publish-core self-test ===")
    test_redactor_builtin()
    test_redactor_custom_loader()
    test_cap_ledger()
    failed = [n for n, ok in _results if not ok]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
