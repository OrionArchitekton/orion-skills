#!/usr/bin/env python3
"""publish-core self-test — adversarial checks for the safety primitives.

Run: python3 selftest.py    (exit 0 = all pass, 1 = a check failed)

Covers:
  * redactor BUILT-IN universals: a planted secret + RFC-1918 IP + internal host
    + absolute home path are detected, the verdict is ABSTAIN (fail-closed), and
    redact() removes them. Always-on; need no customization.
  * redactor CUSTOM loader: a user denylist file is loaded and applied — proven
    with a temp file, so this test is stable no matter how you customize it.
  * cap_ledger: increments to the cap then BLOCKS (read-prior-at-entry). Temp
    ledger — never the real one.
  * gist_client (network-free): the backstop marks dirty content abstained /
    clean content publishable, and the arm gate refuses a live create unless the
    arm flag is present.
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
            cap = common.CAPS["gist"]
            _check("starts-empty", cap_ledger.current("gist") == 0)
            counts = [cap_ledger.increment("gist") for _ in range(cap)]
            _check("increments-monotonic", counts == list(range(1, cap + 1)), f"{counts}")
            _check("at-cap-after-N", cap_ledger.at_cap("gist") is True,
                   f"current={cap_ledger.current('gist')}/{cap}")
            rc = cap_ledger.main(["incr", "gist"])
            _check("blocks-past-cap (exit 4)", rc == 4 and cap_ledger.current("gist") == cap, f"rc={rc}")
        finally:
            common.CAPS_PATH = orig


def test_gist_client():
    print("gist_client:")
    import gist_client

    dirty = {"leak.md": "deployed to 10.1.2.3 with token ghp_AbCdEf0123456789ghIjKlMnOpQrStUv"}
    plan = gist_client.build_plan(dirty, "owner/repo", "main", "d")
    _check("backstop-abstains-on-dirty", plan["clean"] is False,
           f"verdicts={[f['verdict'] for f in plan['files']]}")
    clean = {"NOTE.md": "An embeddable gist of already-public content. Derive-from-public is "
                        "the guard; the redactor is a backstop.\n"}
    plan = gist_client.build_plan(clean, "owner/repo", "main", "d")
    _check("backstop-passes-on-clean", plan["clean"] is True,
           f"verdicts={[f['verdict'] for f in plan['files']]}")

    # Dual-arm gate: a gist (CODE surface) needs BOTH the shared flag AND its own.
    with tempfile.TemporaryDirectory() as td:
        orig_shared, orig_gist = common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH
        shared = Path(td) / "publishers-armed"
        gist_flag = Path(td) / "gist-publishers-armed"
        common.ARM_FLAG_PATH = shared
        common.GIST_ARM_FLAG_PATH = gist_flag
        try:
            _check("gate-disarmed", common.is_gist_armed() is False)
            shared.touch()  # shared armed alone must NOT arm the gist surface
            _check("gate-shared-only-not-armed", common.is_gist_armed() is False)
            gist_flag.touch()
            _check("gate-both-armed", common.is_gist_armed() is True)
        finally:
            common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH = orig_shared, orig_gist

    # Filename sanitization: traversal / absolute / path components are rejected.
    _check("filename-ok-basename", gist_client.gist_filename("a/b/c.md", None) == "c.md")
    for bad in ("../escape.md", "/etc/passwd", "sub/dir.md", ".", ".."):
        try:
            gist_client.gist_filename("x.md", bad)
            _check(f"filename-rejects[{bad}]", False, "did not raise")
        except ValueError:
            _check(f"filename-rejects[{bad}]", True)


def test_gist_live_cap():
    """The LIVE --send path must enforce + increment the cap (network/gh mocked)."""
    print("gist_client (live cap enforcement):")
    import gist_client
    import importlib
    import cap_ledger

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        orig_caps = common.CAPS_PATH
        orig_shared, orig_gist = common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH
        orig_receipts, orig_nudge = common.GIST_RECEIPTS_PATH, common.NUDGE_LOG
        orig_fetch, orig_create = gist_client.fetch_public, gist_client.create_gist
        common.CAPS_PATH = tdp / "caps.json"
        common.GIST_RECEIPTS_PATH = tdp / "gist-receipts.jsonl"
        common.NUDGE_LOG = tdp / "nudge.log"
        common.ARM_FLAG_PATH = tdp / "publishers-armed"
        common.GIST_ARM_FLAG_PATH = tdp / "gist-publishers-armed"
        common.ARM_FLAG_PATH.touch()
        common.GIST_ARM_FLAG_PATH.touch()
        importlib.reload(cap_ledger)  # rebind cap_ledger to the temp CAPS_PATH

        created = []
        gist_client.fetch_public = lambda repo, ref, path, timeout=15: "already public content\n"
        gist_client.create_gist = lambda files, desc: (created.append(1),
                                                       f"https://gist.github.com/mock/{len(created)}")[1]
        try:
            cap = common.CAPS["gist"]
            args = ["create", "--repo", "owner/repo", "--path", "README.md", "--send"]
            rcs = [gist_client.main(args) for _ in range(cap)]
            _check("live-send-under-cap-ok", all(rc == 0 for rc in rcs) and len(created) == cap,
                   f"rcs={rcs} created={len(created)}")
            _check("live-send-recorded-cap", cap_ledger.current("gist") == cap,
                   f"ledger={cap_ledger.current('gist')}/{cap}")
            rc_over = gist_client.main(args)  # the (cap+1)th send
            _check("live-send-at-cap-refused (exit 4)",
                   rc_over == 4 and len(created) == cap,
                   f"rc={rc_over} created={len(created)}")
        finally:
            gist_client.fetch_public, gist_client.create_gist = orig_fetch, orig_create
            common.CAPS_PATH = orig_caps
            common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH = orig_shared, orig_gist
            common.GIST_RECEIPTS_PATH, common.NUDGE_LOG = orig_receipts, orig_nudge


def main(argv) -> int:
    print("=== publish-core self-test ===")
    test_redactor_builtin()
    test_redactor_custom_loader()
    test_cap_ledger()
    test_gist_client()
    test_gist_live_cap()
    failed = [n for n, ok in _results if not ok]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
