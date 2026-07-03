#!/usr/bin/env python3
"""TDD for R01 deep-research abstention recovery wrapper."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("ar", Path(__file__).with_name("abstention_report.py"))
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)


def test_all_abstained_is_inconclusive_not_all_refuted():
    """The core bug: 0 confirmed because everything abstained must NOT read 'all refuted'."""
    claims = [{"claim": f"c{i}", "state": "abstained"} for i in range(5)]
    out = ar.summarize(claims)
    assert out["inconclusive"] is True
    assert "refuted" not in out["verdict"].lower().split("unverified")[0] or "0 refuted" in out["verdict"]
    assert "All 5 claims refuted" not in out["verdict"]
    assert out["counts"] == {"confirmed": 0, "refuted": 0, "unverified": 5}


def test_genuine_all_refuted_still_reported():
    claims = [{"claim": "x", "state": "refuted"}, {"claim": "y", "state": "refuted"}]
    out = ar.summarize(claims)
    assert out["verdict"] == "All 2 claims refuted"
    assert out["inconclusive"] is False


def test_mixed_confirmed_refuted_unverified():
    claims = [{"state": "confirmed"}, {"state": "refuted"}, {"state": "rate_limited"}]
    out = ar.summarize(claims)
    assert out["counts"] == {"confirmed": 1, "refuted": 1, "unverified": 1}
    assert out["inconclusive"] is False


def test_legacy_buckets_killed_defaults_to_unverified_not_refuted():
    """Legacy shape: killed bucket conflates refuted+abstained; unmarked killed -> unverified."""
    out = ar.from_buckets(confirmed=[], killed=["a", "b", "c"])
    assert out["counts"]["unverified"] == 3
    assert out["counts"]["refuted"] == 0
    assert out["inconclusive"] is True


def test_legacy_buckets_respects_explicit_refuted():
    out = ar.from_buckets(confirmed=[], killed=[{"claim": "a", "state": "refuted"}, {"claim": "b"}])
    assert out["counts"]["refuted"] == 1
    assert out["counts"]["unverified"] == 1


def test_bare_string_claim_is_unverified():
    out = ar.summarize(["just a string"])
    assert out["counts"]["unverified"] == 1


def test_fork_verification_block_is_read_directly():
    """orion-deep-research already emits an honest verification block; the CLI must read it."""
    v = {"counts": {"confirmed": 3, "refuted": 1, "unverified": 2}, "inconclusive": False}
    out = ar.from_verification(v)
    assert out["counts"] == {"confirmed": 3, "refuted": 1, "unverified": 2}
    assert out["inconclusive"] is False


def test_fork_all_unverified_is_inconclusive_not_all_refuted():
    out = ar.from_verification({"counts": {"confirmed": 0, "refuted": 0, "unverified": 4}})
    assert out["inconclusive"] is True
    assert "All 4 claims refuted" not in out["verdict"]
    assert out["incomplete"] is True


def test_fork_malformed_counts_degrade_to_zero_not_crash():
    """The CLI's diet IS degraded output; it must not die on it (security review)."""
    for bad in ({"counts": {"confirmed": "x", "refuted": None, "unverified": 2}},
                {"counts": ["not", "a", "dict"]},
                {"counts": None},
                {}):
        out = ar.from_verification(bad)  # must not raise
        assert set(out["counts"]) == {"confirmed", "refuted", "unverified"}
    out = ar.from_verification({"counts": {"confirmed": "x", "refuted": None, "unverified": 2}})
    assert out["counts"] == {"confirmed": 0, "refuted": 0, "unverified": 2}
    assert out["inconclusive"] is True


def test_dual_nested_verification_prefers_result_block():
    """result.verification is the full runner-emitted ledger; it must win over a
    top-level summary so real refutations are not hidden (security review)."""
    import io, contextlib
    payload = {
        "verification": {"counts": {"confirmed": 0, "refuted": 0, "unverified": 5}},
        "result": {"verification": {"counts": {"confirmed": 0, "refuted": 10, "unverified": 0}}},
    }
    picked = ar.pick_verification(payload)
    out = ar.from_verification(picked)
    assert out["counts"]["refuted"] == 10, "must read the deeper full ledger, not the summary"


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
