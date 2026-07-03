// TDD for orion-deep-research verdict aggregation (SPEC S1, S2).
// Run: node --test lib/verify.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { classifyClaim, summarizeRun, voteFromReaderVerdict } from './verify.mjs'

const R = 2 // REFUTATIONS_REQUIRED / vote quorum, matching the native harness

// ─── S1: abstention is never refutation ───

test('all-abstained claim is unverified, never refuted', () => {
  // every voter crashed on a rate-limit → 3 nulls
  const c = classifyClaim({ votes: [null, null, null], refutationsRequired: R })
  assert.equal(c.status, 'unverified')
  assert.equal(c.refutingVotes, 0)
  assert.equal(c.validVotes, 0)
})

test('genuine refuting quorum is reported refuted', () => {
  const c = classifyClaim({
    votes: [{ refuted: true }, { refuted: true }, { refuted: false }],
    refutationsRequired: R,
  })
  assert.equal(c.status, 'refuted')
  assert.equal(c.refutingVotes, 2)
})

test('a single refuting vote below quorum is unverified, NOT refuted (the exact bug)', () => {
  // 1 real vote that refutes + 2 abstentions: cannot adjudicate on one vote
  const c = classifyClaim({ votes: [{ refuted: true }, null, null], refutationsRequired: R })
  assert.equal(c.status, 'unverified')
  assert.notEqual(c.status, 'refuted')
})

test('clean supporting quorum is confirmed', () => {
  const c = classifyClaim({
    votes: [{ refuted: false }, { refuted: false }, { refuted: false }],
    refutationsRequired: R,
  })
  assert.equal(c.status, 'confirmed')
})

test('quorum met with one refutation below threshold is confirmed', () => {
  const c = classifyClaim({
    votes: [{ refuted: false }, { refuted: false }, { refuted: true }],
    refutationsRequired: R,
  })
  assert.equal(c.status, 'confirmed')
  assert.equal(c.refutingVotes, 1)
})

// ─── S2: a dead search does not manufacture a survival ───

test('a searchDegraded "not refuted" vote is treated as abstained, not support', () => {
  // all three voters had a dead search → their "not refuted" is untrustworthy
  const votes = [
    { refuted: false, searchDegraded: true },
    { refuted: false, searchDegraded: true },
    { refuted: false, searchDegraded: true },
  ]
  const c = classifyClaim({ votes, refutationsRequired: R })
  assert.equal(c.validVotes, 0, 'degraded votes must not count as valid')
  assert.equal(c.status, 'unverified')
  assert.notEqual(c.status, 'confirmed')
})

test('degraded votes are excluded but a real supporting quorum still confirms', () => {
  const votes = [
    { refuted: false },
    { refuted: false },
    { refuted: false, searchDegraded: true }, // dropped
  ]
  const c = classifyClaim({ votes, refutationsRequired: R })
  assert.equal(c.validVotes, 2)
  assert.equal(c.status, 'confirmed')
})

// ─── S1: run-level summary honesty ───

test('run summary of all-abstained is inconclusive, never "all refuted"', () => {
  const claims = [
    { status: 'unverified' }, { status: 'unverified' }, { status: 'unverified' },
  ]
  const s = summarizeRun(claims)
  assert.equal(s.counts.refuted, 0)
  assert.equal(s.counts.unverified, 3)
  assert.equal(s.inconclusive, true)
  assert.equal(s.incomplete, true, 'any unverified claim means the run is not complete')
  assert.ok(!/all\s+3\s+claims\s+refuted/i.test(s.verdict), 'must not say all-refuted')
  assert.match(s.verdict, /inconclusive/i)
})

test('mixed refuted+unverified with zero confirmed names the abstention cause', () => {
  // the branch where the inlined copy drifted (D1) - now pinned
  const s = summarizeRun([{ status: 'refuted' }, { status: 'unverified' }])
  assert.match(s.verdict, /abstained\/rate-limited/)
  assert.equal(s.inconclusive, true)
  assert.equal(s.incomplete, true)
})

test('run summary of genuine all-refuted still says so', () => {
  const s = summarizeRun([{ status: 'refuted' }, { status: 'refuted' }])
  assert.match(s.verdict, /all 2 claims refuted/i)
  assert.equal(s.inconclusive, false)
  assert.equal(s.incomplete, false)
})

test('run with confirmed + unverified is complete=false but not inconclusive', () => {
  const s = summarizeRun([{ status: 'confirmed' }, { status: 'unverified' }])
  assert.equal(s.inconclusive, false)   // has a confirmed finding
  assert.equal(s.incomplete, true)      // but still owes verification on the unverified one
  assert.equal(s.counts.confirmed, 1)
  assert.equal(s.counts.unverified, 1)
})

// ─── reader-verdict → vote mapping (the batched source-reader seam, S7) ───

test('a supported reader verdict becomes a valid supporting vote', () => {
  const v = voteFromReaderVerdict({ verdict: 'supported' })
  const c = classifyClaim({ votes: [v, { refuted: false }], refutationsRequired: 2 })
  assert.equal(c.validVotes, 2)
  assert.equal(c.status, 'confirmed')
})

test('a refuted reader verdict becomes a refuting vote', () => {
  const v = voteFromReaderVerdict({ verdict: 'refuted' })
  assert.equal(v.refuted, true)
})

test('an unconfirmed reader verdict is an abstention (null)', () => {
  assert.equal(voteFromReaderVerdict({ verdict: 'unconfirmed' }), null)
})

test('a failed fetch is an abstention (null), never a refutation', () => {
  assert.equal(voteFromReaderVerdict({ verdict: 'refuted', fetchFailed: true }), null)
})

test('a dead-search supported verdict is flagged degraded, not counted as support', () => {
  const v = voteFromReaderVerdict({ verdict: 'supported', searchDegraded: true })
  const c = classifyClaim({ votes: [v, v, v], refutationsRequired: 2 })
  assert.equal(c.validVotes, 0)
  assert.equal(c.status, 'unverified')
})
