#!/usr/bin/env python3
"""Triage fan-out verify/judge verdicts: abstention is not a verdict.

Reads a verify-phase JSON (list of per-claim verdict records) and
re-buckets every claim from its MECHANISM fields, not its verdict label:

    CONFIRMED       supporting votes from completed reads
    REFUTED         refute votes from completed reads
    PENDING_INFRA   zero completed reads / verifier errors present
    PENDING_ABSTAIN verifier said it could not determine

A rate-limited refuter that defaulted to "refuted" (or a dead skeptic
that read as "survived") lands in PENDING_INFRA, never in a real bucket.
Aggregator summary fields are ignored by design: they are the
aggregator's claim, and the whole point is to recompute from per-claim
data.

Exit codes:
    0  no pending claims (every verdict is backed by completed reads)
    3  pending claims exist: BLOCKING for any decision they carry
    2  input unreadable / no claims found (fail closed, never "clean")

Schema tolerance: claims list under "claims", "verdicts", or "results";
per-claim fields looked up under common aliases (verdict/result/outcome,
reads_completed/completed_reads/sources_read, verifier_errors/errors,
could_not_verify/abstained, votes.{refute,support} or flat
refute_votes/support_votes).

Companion of the triage-fanout-verdicts skill.
"""

from __future__ import annotations

import json
import sys


def _first(d: dict, keys: tuple, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _votes(claim: dict) -> tuple[int, int]:
    votes = claim.get("votes")
    if isinstance(votes, dict):
        return int(votes.get("refute", 0) or 0), int(votes.get("support", 0) or 0)
    return (
        int(_first(claim, ("refute_votes",), 0) or 0),
        int(_first(claim, ("support_votes",), 0) or 0),
    )


def bucket_claim(claim: dict) -> str:
    """Bucket one claim from mechanism fields; the verdict label decides
    only the direction of an otherwise-substantiated verdict."""
    reads = int(_first(claim, ("reads_completed", "completed_reads", "sources_read"), 0) or 0)
    errors = _first(claim, ("verifier_errors", "errors"), []) or []
    abstained = bool(_first(claim, ("could_not_verify", "abstained"), False))
    refute, support = _votes(claim)
    verdict = str(_first(claim, ("verdict", "result", "outcome"), "")).lower()

    if abstained:
        return "PENDING_ABSTAIN"
    if reads <= 0 or (refute + support) <= 0:
        # No completed evidence behind the label. Errors make the infra
        # cause explicit, but absence of evidence alone is already
        # disqualifying: a verdict with no reads is a default, not a verdict.
        return "PENDING_INFRA"
    if verdict in ("confirmed", "supported", "survived", "verified") and support > 0:
        return "CONFIRMED"
    if verdict in ("refuted", "rejected", "failed") and refute > 0:
        return "REFUTED"
    # Label and evidence disagree (e.g. "refuted" with only support votes):
    # never guess a direction from a contradictory record.
    return "PENDING_INFRA" if errors else "PENDING_ABSTAIN"


def triage(data: dict) -> dict:
    claims = _first(data, ("claims", "verdicts", "results"), [])
    if not isinstance(claims, list) or not claims:
        raise ValueError("no claims list found (looked for claims/verdicts/results)")
    buckets: dict[str, list[str]] = {
        "CONFIRMED": [], "REFUTED": [], "PENDING_INFRA": [], "PENDING_ABSTAIN": [],
    }
    for i, claim in enumerate(claims):
        cid = str(_first(claim, ("claim_id", "id", "name"), f"claim-{i}"))
        buckets[bucket_claim(claim)].append(cid)
    pending = len(buckets["PENDING_INFRA"]) + len(buckets["PENDING_ABSTAIN"])
    return {
        "total": len(claims),
        "buckets": buckets,
        "pending": pending,
        "clean": pending == 0,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print(f"usage: {argv[0]} <verify_results.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            data = json.load(fh)
        result = triage(data)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"triage_verdicts: cannot triage: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if not result["clean"]:
        print(
            f"BLOCKING: {result['pending']}/{result['total']} claims are PENDING "
            "(abstention/infra-failure is not a verdict); re-verify before any "
            "decision they are load-bearing for.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
