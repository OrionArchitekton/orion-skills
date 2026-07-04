// orion-deep-research - TIER grading (SPEC S4).
//
// TIER 1 = adjudicated by a real vote quorum (status 'confirmed').
// TIER 2 = extracted-with-quote but unverified - surfaced with a caveat rather
//   than silently dropped (TIER1/TIER2 recovery grading).
// Refuted claims go to a transparency bucket. Unverified WITHOUT a quote has no
// evidence to show, so it is dropped. Forked workflow inlines these; keep in sync.

export function gradeClaims(claims = []) {
  const tier1 = [], tier2 = [], refuted = [], dropped = []
  for (const c of claims) {
    if (c.status === 'confirmed') tier1.push(c)
    else if (c.status === 'refuted') refuted.push(c)
    else if (c.quote && String(c.quote).trim()) tier2.push(c) // unverified w/ evidence
    else dropped.push(c) // unverified, no quote → nothing to show
  }
  return {
    tier1, tier2, refuted, dropped,
    counts: { tier1: tier1.length, tier2: tier2.length, refuted: refuted.length, dropped: dropped.length },
  }
}

// A finding is TIER 1 iff at least one of its supporting claims was confirmed;
// otherwise TIER 2 (including a finding with no supporting claims - never a
// silent TIER 1).
export function tierForFinding(supportingStatuses = []) {
  return supportingStatuses.some(s => s === 'confirmed') ? 'TIER 1' : 'TIER 2'
}
