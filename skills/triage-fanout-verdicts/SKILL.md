---
name: triage-fanout-verdicts
description: "Use when reading verdicts from a fan-out of verify/judge/skeptic/reviewer agents (a deep-research verify phase, a workflow adversarial verify, judge panels, refuter votes) before relaying or acting on them, especially when verdicts are unanimous, the fan-out was large, or the run saw rate limits/timeouts. Symptoms: 'all N claims refuted', 'survived the skeptic', 'all resolved' summaries; verdicts with zero completed reads; HTTP 429/timeout in verifier errors; a whole build/no-build decision resting on one verify phase."
---

# Triage Fan-Out Verdicts

## Overview

An abstention is not a verdict. Infrastructure failure masquerades as a
verdict BOTH ways: rate-limited refuters collapse to "all refuted";
a dead search or skeptic reads as "survived the skeptic". A whole
build/no-build call was flipped by 429s reported as refutations.
Unanimity is a mechanism-check trigger, not a confidence boost.

## When to use

- Reading any verify/judge phase output before synthesis or relay.
- Any unanimous or near-unanimous verdict set from a fan-out.
- After a run that logged rate limits, timeouts, or dead fetches.
- NOT for running the verification itself (deep-research and workflow
  harnesses own that); this is the READING discipline.

## Procedure

1. Read the MECHANISM fields before the verdict fields: votes cast,
   reads completed, verifier errors, could_not_verify markers.
2. Bucket every claim:
   - CONFIRMED: supporting votes from completed reads.
   - REFUTED: refute votes from completed reads.
   - PENDING-INFRA: zero completed reads, throttled, fetch dead.
   - PENDING-ABSTAIN: the verifier itself said "cannot determine".
3. PENDING never coerces into refuted or confirmed. Aggregator summary
   fields ("all_refuted", "all_load_bearing_claims_resolved") are the
   aggregator's CLAIM; recompute from per-claim data.
4. Unanimity across a large fan-out: check for a shared-infra artifact
   first; one throttle window poisons every verifier identically.
5. Re-verify PENDING by a DIFFERENT mechanism: deterministic recompute,
   a single source-reader pass over the sources (instead of N refuters
   re-fetching), or an independent re-run after the throttle clears.
   Never manually top up a crashed verify gate.
6. Report survivors / refuted / pending, with PENDING marked BLOCKING
   for any decision it is load-bearing to.

Mechanical helper (selftested): `python3 scripts/triage_verdicts.py
<verify.json>` prints the bucketed triage and exits 3 when pending
verdicts exist, so drivers and goal conditions can gate on it. Run it
from this skill's directory, or point the path at wherever you copied
`scripts/`.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The JSON says refuted" | The JSON records what the verifier RETURNED, including its failure default |
| "10 of 12 refuted; the picture is clear" | 10 of 12 had zero completed reads; the picture is one throttle window |
| "The summary flag says all resolved" | The flag is computed by the same code that defaulted abstentions to refuted |
| "Re-running is expensive" | Wrongly killing (or shipping) the build costs more than one re-verify pass |
| "The skeptic found nothing, so it survived" | A dead skeptic finds nothing; check the skeptic completed its reads |

## Red flags

- Relaying a verdict count without having read a single per-claim
  mechanism field.
- "All refuted" or "all survived" from a fan-out that logged ANY 429s.
- A verdict bucket for every claim and zero pending: real fan-outs have
  stragglers; zero pending under infra errors means coercion happened.

## Related

This consolidates a family of recurring rate-limit/abstention-miscoding
failures seen across verify/judge fan-outs: a throttled refuter
defaulting to "refuted," a dead skeptic reading as "survived," and an
aggregator's summary flag inheriting the same coercion it is supposed
to detect. Siblings: an adversarial self-verification pass that
re-confirms your own report's claims from live disk before you relay
them; `author-workflow-fanout` (authoring the fan-out whose verdicts
you triage; its per-agent `.catch` -> ledger discipline is what
produces the PENDING-INFRA bucket in the first place); `design-fail-closed-gate`
(abstain-as-block is its authoring analog).

## Boundary

This is the verdict-reading discipline, not the verification engine. Wiring the
fan-out itself, running the retrieval/judge harness, and choosing where the
bucketed triage output gets recorded are your own harness's mechanics. The
invariant is the shape: read mechanism fields before verdict labels, and never
let a PENDING claim coerce into a refuted or confirmed bucket.
