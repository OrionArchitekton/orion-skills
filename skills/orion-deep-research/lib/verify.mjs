// orion-deep-research - verdict aggregation (SPEC S1, S2).
//
// Canonical semantics mirror the tested Python `abstention_report.summarize`
// (see the bundled scripts/abstention_report.py): an UNVERIFIED claim
// (abstained / rate-limited / dead-search) is NEVER folded into `refuted`.
// The forked workflow inlines copies of these functions (the Workflow sandbox
// cannot import); keep the inlined copies in sync with this tested module.

// A single verdict is `{refuted: bool, ...}` or null (the voter abstained:
// rate-limited, errored, skipped). A verdict with `searchDegraded: true` had a
// dead evidence search, so neither its support nor its refutation is trustworthy
// - it is treated as an abstention (S2).
export function classifyClaim({ votes = [], refutationsRequired = 2 } = {}) {
  const degraded = votes.filter(v => v && v.searchDegraded).length
  const valid = votes.filter(v => v && !v.searchDegraded)
  const refutingVotes = valid.filter(v => v.refuted).length
  const supportingVotes = valid.length - refutingVotes
  const abstained = votes.length - valid.length

  let status
  if (refutingVotes >= refutationsRequired) {
    status = 'refuted'
  } else if (valid.length >= refutationsRequired && refutingVotes < refutationsRequired) {
    // adjudicated: a quorum of real votes, not enough refutations to kill it
    status = 'confirmed'
  } else {
    // too few real votes to adjudicate → could not verify, NOT disproven
    status = 'unverified'
  }
  return { status, validVotes: valid.length, refutingVotes, supportingVotes, abstained, degraded }
}

// Map one source-reader's per-claim verdict into the vote shape classifyClaim
// consumes (the batched source-reader seam, S7). A failed fetch or an
// unconfirmed reading is an abstention (null) - NEVER a refutation. A dead
// evidence search flags the vote degraded so it is excluded from valid votes.
export function voteFromReaderVerdict({ verdict, searchDegraded = false, fetchFailed = false } = {}) {
  if (fetchFailed) return null                       // could not read → abstain
  if (searchDegraded) return { refuted: false, searchDegraded: true }
  if (verdict === 'refuted') return { refuted: true }
  if (verdict === 'supported') return { refuted: false }
  return null                                        // 'unconfirmed'/unknown → abstain
}

// Aggregate classified claims into an honest run-level summary. `inconclusive`
// = zero confirmed but some unverified (the abstention-dominated zero). `incomplete`
// = any unverified claim remains (the run still owes verification; it is not done).
export function summarizeRun(claims = []) {
  const counts = { confirmed: 0, refuted: 0, unverified: 0 }
  for (const c of claims) {
    const s = c.status
    if (s === 'confirmed') counts.confirmed++
    else if (s === 'refuted') counts.refuted++
    else counts.unverified++ // anything not affirmatively confirmed/refuted is unverified
  }
  const { confirmed: nc, refuted: nr, unverified: nu } = counts

  let verdict
  if (nc) verdict = `${nc} confirmed, ${nr} refuted, ${nu} unverified`
  else if (nu && !nr) verdict = `INCONCLUSIVE: ${nu} unverified (abstained/rate-limited), 0 refuted - re-run verification before reporting`
  else if (nu && nr) verdict = `INCONCLUSIVE: 0 confirmed, ${nr} refuted, ${nu} unverified (abstained/rate-limited) - ${nu} still need verification`
  else if (nr && !nu) verdict = `All ${nr} claims refuted`
  else verdict = 'no claims'

  return {
    counts,
    verdict,
    inconclusive: nc === 0 && nu > 0,
    incomplete: nu > 0,
  }
}
