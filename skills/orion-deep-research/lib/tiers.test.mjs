// TDD for orion-deep-research TIER grading (SPEC S4).
// TIER 1 = adjudicated by a real vote quorum (status confirmed).
// TIER 2 = extracted-with-quote but unverified (surfaced with a caveat, not dropped).
// Refuted claims are neither; they go to a transparency bucket.
// Run: node --test lib/tiers.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { gradeClaims, tierForFinding } from './tiers.mjs'

test('a confirmed claim is TIER 1', () => {
  const g = gradeClaims([{ status: 'confirmed', quote: 'q', claim: 'c' }])
  assert.equal(g.tier1.length, 1)
  assert.equal(g.tier2.length, 0)
})

test('an unverified claim WITH a quote is TIER 2 (surfaced, not dropped)', () => {
  const g = gradeClaims([{ status: 'unverified', quote: 'has a supporting quote', claim: 'c' }])
  assert.equal(g.tier2.length, 1)
  assert.equal(g.tier1.length, 0)
})

test('an unverified claim WITHOUT a quote is dropped, not surfaced as evidence', () => {
  const g = gradeClaims([{ status: 'unverified', quote: '', claim: 'c' }])
  assert.equal(g.tier2.length, 0)
  assert.equal(g.dropped.length, 1)
})

test('a refuted claim goes to the transparency bucket, never TIER 1 or 2', () => {
  const g = gradeClaims([{ status: 'refuted', quote: 'q', claim: 'c' }])
  assert.equal(g.refuted.length, 1)
  assert.equal(g.tier1.length, 0)
  assert.equal(g.tier2.length, 0)
})

test('counts reflect the full split', () => {
  const g = gradeClaims([
    { status: 'confirmed', quote: 'q' },
    { status: 'confirmed', quote: 'q' },
    { status: 'unverified', quote: 'q' },
    { status: 'unverified', quote: '' },
    { status: 'refuted', quote: 'q' },
  ])
  assert.deepEqual(g.counts, { tier1: 2, tier2: 1, refuted: 1, dropped: 1 })
})

// finding-level tier: a finding rests on its supporting claims' statuses
test('a finding resting on any confirmed claim is TIER 1', () => {
  assert.equal(tierForFinding(['unverified', 'confirmed']), 'TIER 1')
})

test('a finding resting only on unverified claims is TIER 2', () => {
  assert.equal(tierForFinding(['unverified', 'unverified']), 'TIER 2')
})

test('a finding with no supporting claims is TIER 2 (never silently TIER 1)', () => {
  assert.equal(tierForFinding([]), 'TIER 2')
})
