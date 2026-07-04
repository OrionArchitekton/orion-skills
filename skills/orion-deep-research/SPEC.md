# orion-deep-research - Spec

## What this is

A fork of the native `/deep-research` harness. Same research spine (decompose a
question into angles, fan out web search, extract falsifiable claims, adversarially verify,
synthesize a cited report), with three additions the native command cannot provide:

1. **Honest verification accounting** - an unverifiable claim is never reported as refuted.
2. **A bounded reflect / knowledge-gap loop** - the run re-steers search on what it actually
   found, instead of committing to its angles once and never looking back.
3. **A durable, quality-gated artifact** - every completed run lands as a dated synthesis in
   your research vault, with a verification-provenance ledger, and a low-quality or
   inconclusive run is quarantined rather than written to the durable recall corpus.

Ubiquitous language (one canonical term per concept):
- **claim** - a falsifiable statement extracted from a source, carrying a supporting quote.
- **verdict** - one adversarial voter's judgment on a claim: *refuting*, *supporting*, or
  *abstained* (the voter could not adjudicate: rate-limited, errored, dead search).
- **status** of a claim after aggregation: **confirmed** / **refuted** / **unverified**
  (replaces the native harness's two-bucket confirmed/killed, which folded abstentions into
  killed). "unverified", "pending", "abstained" are synonyms this spec collapses to
  **unverified**.
- **round** - one full search→extract→verify pass. A run has an initial round and up to
  `MAX_ROUNDS` reflect rounds.
- **tier** of a finding - **TIER 1** (adjudicated by a real vote quorum) vs **TIER 2**
  (single-source or unverified, extracted-with-quote but not vote-confirmed).

## Scenarios (each is a vertical slice, independently demoable)

### S1 - Abstention is never reported as refutation  [the #1 abstention bug]
Given a round where every verifier vote on every claim *abstained* (e.g. a transient
rate-limit crashed all voters),
When the round's verdicts are aggregated,
Then every such claim has status **unverified**, none has status **refuted**, the run summary
reads "inconclusive: N unverified, 0 refuted" (never "all N refuted"), and the run is flagged
**incomplete** (a non-empty pending set means not-done).
And a claim with a genuine refuting quorum (>= REFUTATIONS_REQUIRED real refuting votes) is
still reported **refuted**.
Seam: pure aggregation unit tests (mirrors the tested `abstention_report.summarize` semantics).

### S2 - A dead search does not manufacture a survival
Given a verifier whose own evidence search returned zero results for every query,
When its verdict is aggregated,
Then its "not refuted" vote is treated as **abstained**, not as support - an un-searched sweep
is unverified in both directions, and the claim degrades toward **unverified**, not confirmed.
Seam: pure aggregation unit tests (a verdict carrying a `searchDegraded`/`couldNotVerify` flag).

### S3 - The reflect loop actually fires (no armed-but-never-fires)
Given round 1 leaves a **central** sub-question with no confirmed claim (or a central claim was
refuted),
When the reflect gate is consulted,
Then it authorizes exactly one more round (up to `MAX_ROUNDS`), that round receives a
**reserved, non-empty fetch budget** distinct from round 1's exhausted allotment, and its new
sources are not re-fetches of round-1 URLs.
And given round 1 already answered every central sub-question, the gate authorizes **no** extra
round (does not burn budget on a satisfied question).
Invariant: a reflect round can never receive zero fetch slots while gaps remain (the silent
no-op trap). Total sources fetched across all rounds is bounded and accounted for; it never
exceeds the run cap by re-using a saturated per-round cap.
Seam: pure budget/gate unit tests.

### S4 - Findings are tier-graded
Given a synthesized report drawn from a mix of vote-confirmed and merely-extracted claims,
When findings are graded,
Then each finding is **TIER 1** iff it rests on at least one confirmed (vote-quorum) claim,
else **TIER 2**, and the tier is visible on the finding and in the run stats.
Seam: pure grading unit tests.

### S5 - Every completed run persists a durable, disclaimed artifact
Given a run that reaches synthesis,
When the wrapper finalizes,
Then it writes `<research-vault>/<YYYY-MM-DD>-<slug>.md` carrying the house
header (Title, Date, Type = "Deep-research synthesis (advisory, non-authoritative)", Scope,
Method), a confidence-tag legend, an Executive Summary, inline evidence grading, a
**Verification Provenance** ledger (run id(s), per-claim confirmed/unverified/refuted tally,
any rate-limit or dead-search incident, citation existence checks), and a closing
advisory + non-authoritative disclaimer.
And the file is written but **not committed**: the wrapper shows the vault git status/diff and
leaves the commit/PR to the operator (shared-state gate).
Seam: wrapper procedure + a rendered-artifact shape check.

### S6 - A low-quality or inconclusive run is quarantined, not corpus-written
Given a run whose independent report judge scores it failing (inconclusive, uncovered angles,
or unattributed load-bearing claims),
When the wrapper decides persistence,
Then the artifact is written to a quarantine location (or clearly marked DRAFT/INCONCLUSIVE)
and is **not** filed as an authoritative-looking vault synthesis, and the judge's reasons are
surfaced. The judge is advisory/severity-graded, never a fail-open silent block.
Seam: judge output shape + wrapper decision.

### S7 - Verification reads sources first-hand, throttle-safely
Given the claims to verify,
When verification runs,
Then it is organized as a bounded set of source-grouped readers (one reader per distinct source
URL, capped), each reading the real source and adjudicating all of that source's claims - not an
unbounded per-claim x per-lens refuter fan-out - so agent count stays within a throttle-safe cap
even across reflect rounds.
Seam: workflow structure + agent-count bound (observed / accounted in stats).

### S8 - Load-bearing claims carry numbered citations
Given the final findings,
When the report is assembled,
Then each finding carries numbered `[n]` citations bound to entries in a numbered source
registry, and any load-bearing factual sentence with no attachable source is flagged rather
than shipped silently.
Seam: citation-binding shape check.

### S9 - Angle breadth scales to question complexity
Given a simple factual question vs a complex multi-part one,
When scoping,
Then the number of search angles scales with assessed complexity (small for simple, larger for
complex), drawing from the domain-adaptive archetype pool, rather than a hardcoded constant.
Seam: scope output shape.

## Non-goals / explicitly rejected
- No auto-commit or auto-PR to the vault (operator gate).
- No self-revise loop that lets the same model re-grade and rewrite its own draft unbounded
  (sycophancy risk; the reflect loop is evidence-driven and bounded, the judge is advisory).
- No unbounded recursion - every loop is capped by `MAX_ROUNDS` and a spanning fetch budget.
- The research core stays a faithful superset of native where it can; every divergence is
  documented so native updates can be re-synced.

## Test seams (fewest, highest)
1. **Pure-logic unit tests** (`lib/*.test.mjs`, node): aggregation (S1, S2), budget+gate (S3),
   tiers (S4). These hold the bug-prone, load-bearing logic and are the primary seam.
2. **Recovery-CLI parity** (`abstention_report.py` tests): the saved-output reclassifier
   handles the fork's output shape (S1 post-hoc).
3. **Observed run** (manual, per prove-deploy-is-live): one real invocation writes a
   well-formed artifact and, on a forced abstention, does not report "all refuted" (S1, S5 end
   to end).
