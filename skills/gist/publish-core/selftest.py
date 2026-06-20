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
        # last line is a malformed regex (unterminated character set) — it must be
        # SKIPPED (the valid lines still load) but surfaced as a load error, not
        # silently dropped (a silent skip is a hole in a fail-closed guard).
        cfg.write_text("# my org\n\\bACME\\b\nmybox-01\n[unclosed\n")
        orig = redactor.CUSTOM_PATH
        redactor.CUSTOM_PATH = cfg
        try:
            v1, h1 = redactor.decision("we billed ACME this quarter")
            _check("custom-term-acronym", v1 == "ABSTAIN" and any(c == "custom" for c, _ in h1))
            v2, h2 = redactor.decision("deployed to mybox-01 overnight")
            _check("custom-term-host", v2 == "ABSTAIN" and any(c == "custom" for c, _ in h2))
            v3, _ = redactor.decision("we shipped the feature on schedule")
            _check("non-listed-publishes", v3 == "PUBLISH")
            # the malformed line is reported (fail-closed: never a silent skip)
            errs = redactor.custom_load_errors()
            _check("malformed-line-surfaced",
                   len(errs) == 1 and errs[0][1] == "[unclosed",
                   f"errors={errs}")
        finally:
            redactor.CUSTOM_PATH = orig


def test_cap_ledger():
    print("cap_ledger:")
    with tempfile.TemporaryDirectory() as td:
        orig, orig_lock = common.CAPS_PATH, common.CAPS_LOCK_PATH
        common.CAPS_PATH = Path(td) / "caps.json"
        common.CAPS_LOCK_PATH = Path(td) / "caps.lock"  # flock target; don't touch real state
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
            # reserve() is the atomic check-and-increment: None at cap (no over-count).
            _check("reserve-at-cap-returns-none", cap_ledger.reserve("gist") is None)
        finally:
            common.CAPS_PATH, common.CAPS_LOCK_PATH = orig, orig_lock


def test_gist_client():
    print("gist_client:")
    import gist_client

    dirty = {"leak.md": "deployed to 10.1.2.3 with token ghp_AbCdEf0123456789ghIjKlMnOpQrStUv"}
    plan = gist_client.build_plan(dirty, "owner/repo", "main", "d")
    _check("backstop-abstains-on-dirty", plan["clean"] is False,
           f"verdicts={[f['verdict'] for f in plan['files']]}")
    # The plan must carry the MASKED hit snippets (not just classes) so a human
    # can eyeball each matched value before --ack-public-hits — and never the raw.
    hits = plan["files"][0]["hits"]
    masked_vals = [h["masked"] for h in hits]
    _check("plan-keeps-masked-hits", len(hits) >= 1 and all("*" in m for m in masked_vals),
           f"masked={masked_vals}")
    _check("plan-masks-not-raw",
           all("ghp_AbCdEf0123456789ghIjKlMnOpQrStUv" not in m for m in masked_vals)
           and all("10.1.2.3" not in m for m in masked_vals))
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

    # Duplicate basenames must be REFUSED (not silently collapsed/overwritten).
    orig_fetch = gist_client.fetch_public
    gist_client.fetch_public = lambda repo, ref, path, timeout=15: f"content of {path}\n"
    try:
        rc = gist_client.main(["create", "--repo", "owner/repo",
                               "--path", "docs/README.md", "--path", "examples/README.md"])
        _check("dup-basename-refused (exit 2)", rc == 2, f"rc={rc}")
    finally:
        gist_client.fetch_public = orig_fetch

    # The plan carries a sha256 of the exact reviewed bytes.
    import hashlib
    body = "already public content\n"
    plan = gist_client.build_plan({"f.md": body}, "o/r", "main", "d")
    _check("plan-has-sha256",
           plan["files"][0]["sha256"] == hashlib.sha256(body.encode()).hexdigest(),
           f"sha={plan['files'][0]['sha256'][:12]}...")

    # Movable-ref detection (drives the unpinned-send warning): a full commit SHA
    # is immutable; a branch/tag is not.
    _check("immutable-ref-sha1", gist_client.is_immutable_ref("a" * 40) is True)
    _check("immutable-ref-sha256", gist_client.is_immutable_ref("0" * 64) is True)
    _check("movable-ref-branch", gist_client.is_immutable_ref("main") is False)
    _check("movable-ref-shortsha", gist_client.is_immutable_ref("abc1234") is False)


def test_gist_live_cap():
    """The LIVE --send path must enforce + increment the cap (network/gh mocked)."""
    print("gist_client (live cap enforcement):")
    import gist_client
    import importlib
    import cap_ledger

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        orig_caps, orig_lock = common.CAPS_PATH, common.CAPS_LOCK_PATH
        orig_shared, orig_gist = common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH
        orig_receipts, orig_nudge = common.GIST_RECEIPTS_PATH, common.NUDGE_LOG
        orig_fetch, orig_create = gist_client.fetch_public, gist_client.create_gist
        common.CAPS_PATH = tdp / "caps.json"
        common.CAPS_LOCK_PATH = tdp / "caps.lock"  # flock target; don't touch real state
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
            common.CAPS_PATH, common.CAPS_LOCK_PATH = orig_caps, orig_lock
            common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH = orig_shared, orig_gist
            common.GIST_RECEIPTS_PATH, common.NUDGE_LOG = orig_receipts, orig_nudge


def test_gist_expect_sha():
    """--expect-sha256 binds --send to reviewed bytes; drift refuses (exit 3)."""
    print("gist_client (--expect-sha256 binding):")
    import gist_client
    import importlib
    import hashlib
    import cap_ledger

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        orig_caps, orig_lock = common.CAPS_PATH, common.CAPS_LOCK_PATH
        orig_shared, orig_gist = common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH
        orig_receipts, orig_nudge = common.GIST_RECEIPTS_PATH, common.NUDGE_LOG
        orig_fetch, orig_create = gist_client.fetch_public, gist_client.create_gist
        common.CAPS_PATH = tdp / "caps.json"
        common.CAPS_LOCK_PATH = tdp / "caps.lock"  # flock target; don't touch real state
        common.GIST_RECEIPTS_PATH = tdp / "gist-receipts.jsonl"
        common.NUDGE_LOG = tdp / "nudge.log"
        common.ARM_FLAG_PATH = tdp / "publishers-armed"
        common.GIST_ARM_FLAG_PATH = tdp / "gist-publishers-armed"
        common.ARM_FLAG_PATH.touch()
        common.GIST_ARM_FLAG_PATH.touch()
        importlib.reload(cap_ledger)

        body = "reviewed bytes\n"
        good = hashlib.sha256(body.encode()).hexdigest()
        created = []
        gist_client.fetch_public = lambda repo, ref, path, timeout=15: body
        gist_client.create_gist = lambda files, desc: (created.append(1),
                                                       "https://gist.github.com/mock/x")[1]
        try:
            base = ["create", "--repo", "o/r", "--path", "README.md", "--send"]
            # Matching sha -> proceeds.
            rc_ok = gist_client.main(base + ["--expect-sha256", f"README.md={good}"])
            _check("expect-sha-match-sends", rc_ok == 0 and len(created) == 1, f"rc={rc_ok}")
            # Mismatch (ref moved) -> refuse, no new create.
            rc_bad = gist_client.main(base + ["--expect-sha256", "README.md=" + "0" * 64])
            _check("expect-sha-mismatch-refused (exit 3)",
                   rc_bad == 3 and len(created) == 1, f"rc={rc_bad} created={len(created)}")
        finally:
            gist_client.fetch_public, gist_client.create_gist = orig_fetch, orig_create
            common.CAPS_PATH, common.CAPS_LOCK_PATH = orig_caps, orig_lock
            common.ARM_FLAG_PATH, common.GIST_ARM_FLAG_PATH = orig_shared, orig_gist
            common.GIST_RECEIPTS_PATH, common.NUDGE_LOG = orig_receipts, orig_nudge


def main(argv) -> int:
    print("=== publish-core self-test ===")
    test_redactor_builtin()
    test_redactor_custom_loader()
    test_cap_ledger()
    test_gist_client()
    test_gist_live_cap()
    test_gist_expect_sha()
    failed = [n for n, ok in _results if not ok]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
