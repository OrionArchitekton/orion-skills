// orion-deep-research - fetch-budget reservation + reflect gate (SPEC S3).
//
// The trap the OSS sweep flagged: MAX_FETCH is a per-run SOURCE cap that DEDUP
// saturates in round 1. A reflect round that "reuses MAX_FETCH" therefore gets
// zero slots and silently no-ops (armed-but-never-fires). planBudget carves a
// RESERVED, non-empty reflect allotment out of the cap up front, so a reflect
// round always has real slots, and the total across all rounds never exceeds the
// cap. The forked workflow inlines these; keep in sync with lib/budget.test.mjs.

// Split the run's source-fetch cap into a round-1 allotment plus a reserved
// per-reflect-round allotment. Guarantees: round1 >= 1, and every ALLOWED reflect
// round gets >= 1 slot (if the cap is too small to fund the requested rounds,
// effective maxRounds shrinks rather than handing any round zero slots).
export function planBudget({ maxFetch = 20, maxRounds = 1, reflectReserveRatio = 0.3 } = {}) {
  maxRounds = Math.max(0, Math.floor(maxRounds))
  if (maxRounds === 0 || maxFetch < 2) {
    return { round1Slots: maxFetch, reflectSlotsPerRound: 0, reflectReserveTotal: 0, maxRounds: 0 }
  }
  // reserve at least one slot per round, or the ratio share, but always leave
  // round 1 the majority (>= 1 and strictly more than the reserve).
  let reserve = Math.max(maxRounds, Math.ceil(maxFetch * reflectReserveRatio))
  reserve = Math.min(reserve, Math.floor((maxFetch - 1) / 2)) // round1 keeps the bulk
  reserve = Math.max(reserve, 1)
  // each reflect round needs >= 1 slot; if not enough reserve to fund maxRounds,
  // cap the rounds to what the reserve can fund (never a zero-slot round).
  const effRounds = Math.min(maxRounds, reserve)
  const reflectSlotsPerRound = Math.max(1, Math.floor(reserve / effRounds))
  return {
    round1Slots: maxFetch - reserve,
    reflectSlotsPerRound,
    reflectReserveTotal: reserve,
    maxRounds: effRounds,
  }
}

// Authorize one more reflect round iff: under the round cap, a real central gap
// remains, AND there is at least one reflect fetch slot left. The last clause is
// the no-op guard: never authorize a round that would fetch nothing.
export function shouldReflect({ round, maxRounds, centralGaps = [], reflectSlotsRemaining = 0 } = {}) {
  return round < maxRounds && centralGaps.length > 0 && reflectSlotsRemaining >= 1
}
