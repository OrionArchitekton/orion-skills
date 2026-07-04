#!/usr/bin/env python3
"""R01 deep-research abstention-reporting recovery wrapper.

WHY THIS EXISTS (F1 fallback): `/deep-research` is a built-in harness command whose
verification/report logic is emitted INLINE into an ephemeral per-session Workflow
script (no durable template or shared lib to edit). The recurring bug: when the
verify stage is rate-limited / abstains, every claim lands in a `killed` bucket and
the report emits "All N claims refuted" even though nothing was actually refuted -
a confident-but-false negative (observed twice; see
loop-engineering-self-apply-MAP-20260627 finding C1).

This module is the durable, testable RECOVERY WRAPPER the MAP named as the fallback:
feed it the per-claim verdicts (or raw buckets) a deep-research run produced and it
re-derives an HONEST summary that splits `refuted` from `unverified` (abstained /
rate-limited / pending) and NEVER reports "all refuted" on an abstention-driven zero.

Import `summarize()` in a deep-research workflow's report stage, or run as a CLI over
a results JSON.
"""
from __future__ import annotations
import json
import sys

# states that mean "we could not verify", NOT "we disproved it"
UNVERIFIED_STATES = {"abstained", "pending", "rate_limited", "ratelimited", "unverified", "error", "timeout", "skipped"}
CONFIRMED_STATES = {"confirmed", "supported", "verified", "ship"}
REFUTED_STATES = {"refuted", "disproven", "contradicted", "false"}


def _state_of(claim) -> str:
    if isinstance(claim, str):
        return "unverified"
    s = (claim.get("state") or claim.get("verdict") or claim.get("status") or "").strip().lower()
    return s


def summarize(claims: list) -> dict:
    """Return an honest split + verdict line from a list of per-claim verdicts.

    Each claim is a dict with a state/verdict/status field (or a bare string -> unverified).
    """
    confirmed, refuted, unverified = [], [], []
    for c in claims:
        s = _state_of(c)
        if s in CONFIRMED_STATES:
            confirmed.append(c)
        elif s in REFUTED_STATES:
            refuted.append(c)
        else:  # anything not affirmatively confirmed/refuted is UNVERIFIED, never "refuted"
            unverified.append(c)

    nc, nr, nu = len(confirmed), len(refuted), len(unverified)
    return {
        "verdict": _verdict_line(nc, nr, nu),
        "confirmed": confirmed,
        "refuted": refuted,
        "unverified": unverified,
        "counts": {"confirmed": nc, "refuted": nr, "unverified": nu},
        "inconclusive": nc == 0 and nu > 0,
        "incomplete": nu > 0,
    }


def _verdict_line(nc: int, nr: int, nu: int) -> str:
    if nc:
        return f"{nc} confirmed, {nr} refuted, {nu} unverified"
    if nu and not nr:
        return f"INCONCLUSIVE: {nu} unverified (abstained/rate-limited), 0 refuted - re-run verification before reporting"
    if nu and nr:
        return f"INCONCLUSIVE: 0 confirmed, {nr} refuted, {nu} unverified (abstained/rate-limited) - {nu} still need verification"
    if nr and not nu:
        return f"All {nr} claims refuted"
    return "no claims"


def _n(x) -> int:
    """Defensive count coercion: the CLI's expected diet is DEGRADED output, so a
    garbled count degrades to 0 instead of crashing the recovery path."""
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def from_verification(v) -> dict:
    """Read the honest verification block orion-deep-research already emits.

    `v` is `{counts: {confirmed, refuted, unverified}, ...}`. Re-derives the verdict
    line + flags from the counts so the CLI reports identically on fork output and
    on legacy claim lists. Malformed/missing counts degrade to 0 (never crash).
    """
    counts = (v or {}).get("counts") if isinstance(v, dict) else {}
    if not isinstance(counts, dict):
        counts = {}
    nc = _n(counts.get("confirmed", 0))
    nr = _n(counts.get("refuted", 0))
    nu = _n(counts.get("unverified", 0))
    return {
        "verdict": _verdict_line(nc, nr, nu),
        "counts": {"confirmed": nc, "refuted": nr, "unverified": nu},
        "inconclusive": nc == 0 and nu > 0,
        "incomplete": nu > 0,
    }


def pick_verification(data):
    """Locate the fork's verification block. `result.verification` (the full
    runner-emitted ledger) WINS over a top-level summary block, so a partial
    top-level copy can never hide real refutations recorded in the ledger."""
    if not isinstance(data, dict):
        return None
    result = data.get("result")
    if isinstance(result, dict) and isinstance(result.get("verification"), dict):
        return result["verification"]
    if isinstance(data.get("verification"), dict):
        return data["verification"]
    return None


def from_buckets(confirmed: list, killed: list) -> dict:
    """Adapter for the legacy deep-research shape that conflates refuted+abstained in `killed`.

    Each killed item keeps its own state if present; items with no affirmative `refuted`
    state default to UNVERIFIED (the fix - legacy code defaulted them to refuted).
    """
    claims = []
    for c in (confirmed or []):
        d = c if isinstance(c, dict) else {"claim": c}
        d = {**d, "state": "confirmed"}
        claims.append(d)
    for c in (killed or []):
        if isinstance(c, dict) and _state_of(c) in REFUTED_STATES:
            claims.append(c)
        elif isinstance(c, dict):
            claims.append({**c, "state": c.get("state") or "unverified"})
        else:
            claims.append({"claim": c, "state": "unverified"})
    return summarize(claims)


def main(argv) -> int:
    data = json.load(open(argv[1])) if len(argv) > 1 else json.load(sys.stdin)
    # orion-deep-research (fork) output already carries an honest verification block,
    # possibly nested under the Workflow runner's `result`. The deeper ledger wins.
    fork_v = pick_verification(data)
    if fork_v is not None:
        out = from_verification(fork_v)
    elif isinstance(data, dict) and ("confirmed" in data or "killed" in data) and "claims" not in data:
        out = from_buckets(data.get("confirmed", []), data.get("killed", []))
    else:
        claims = data.get("claims", data) if isinstance(data, dict) else data
        out = summarize(claims)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
