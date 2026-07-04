// TDD for orion-deep-research fetch-budget reservation + reflect gate (SPEC S3).
// The load-bearing invariant: a reflect round NEVER gets zero fetch slots while
// gaps remain (the "armed but never fires" no-op trap the OSS sweep flagged).
// Run: node --test lib/budget.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { planBudget, shouldReflect } from './budget.mjs'

// ─── planBudget: reserve a real, spanning second-round allotment ───

test('reflect reserve is non-empty and round1 keeps the bulk', () => {
  const p = planBudget({ maxFetch: 20, maxRounds: 1, reflectReserveRatio: 0.3 })
  assert.ok(p.reflectSlotsPerRound >= 1, 'reflect must get >=1 slot')
  assert.ok(p.round1Slots >= 1, 'round1 must keep >=1 slot')
  assert.ok(p.round1Slots > p.reflectReserveTotal, 'round1 keeps the bulk')
})

test('total reserved never exceeds the run cap (spanning accounting)', () => {
  const p = planBudget({ maxFetch: 20, maxRounds: 2, reflectReserveRatio: 0.3 })
  const worstCaseFetched = p.round1Slots + p.reflectSlotsPerRound * p.maxRounds
  assert.ok(worstCaseFetched <= 20, `worst-case ${worstCaseFetched} must be <= cap 20`)
})

test('tiny cap still yields >=1 reflect slot (never a zero-budget no-op)', () => {
  // the trap: a naive "reuse MAX_FETCH" gives round-2 zero slots
  const p = planBudget({ maxFetch: 2, maxRounds: 1, reflectReserveRatio: 0.3 })
  assert.ok(p.reflectSlotsPerRound >= 1)
  assert.ok(p.round1Slots >= 1)
})

test('more rounds than reserve slots caps effective rounds, never zero-slot rounds', () => {
  // maxRounds=5 but only room for a few reflect slots → effective rounds shrink,
  // each surviving round still gets >=1 slot
  const p = planBudget({ maxFetch: 6, maxRounds: 5, reflectReserveRatio: 0.3 })
  assert.ok(p.reflectSlotsPerRound >= 1)
  assert.ok(p.maxRounds >= 1 && p.maxRounds <= 5)
})

test('maxRounds 0 disables reflect and hands the whole cap to round 1', () => {
  const p = planBudget({ maxFetch: 15, maxRounds: 0 })
  assert.equal(p.reflectSlotsPerRound, 0)
  assert.equal(p.maxRounds, 0)
  assert.equal(p.round1Slots, 15)
})

// ─── shouldReflect: fires on real gaps, never on a satisfied or exhausted run ───

test('fires when a central gap remains, under the round cap, with budget left', () => {
  assert.equal(shouldReflect({ round: 0, maxRounds: 1, centralGaps: ['g'], reflectSlotsRemaining: 6 }), true)
})

test('does NOT fire when there are no central gaps (satisfied question)', () => {
  assert.equal(shouldReflect({ round: 0, maxRounds: 1, centralGaps: [], reflectSlotsRemaining: 6 }), false)
})

test('does NOT fire once the round cap is reached', () => {
  assert.equal(shouldReflect({ round: 1, maxRounds: 1, centralGaps: ['g'], reflectSlotsRemaining: 6 }), false)
})

test('does NOT fire when reflect budget is exhausted, even with gaps (no-op guard)', () => {
  assert.equal(shouldReflect({ round: 0, maxRounds: 1, centralGaps: ['g'], reflectSlotsRemaining: 0 }), false)
})
