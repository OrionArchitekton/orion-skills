// DRIFT GUARD: the Workflow sandbox cannot import, so deep-research.workflow.js
// INLINES copies of the tested lib functions. This test extracts that inlined block
// from the workflow SOURCE and runs both copies against shared vectors - any
// behavioral divergence (including verdict strings) is a red test, not a silent lie.
// (Motivated by review finding D1: the inlined summarizeRun had already drifted.)
// Run: node --test lib/drift.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import * as vlib from './verify.mjs'
import * as blib from './budget.mjs'
import * as tlib from './tiers.mjs'

const src = fs.readFileSync(new URL('../deep-research.workflow.js', import.meta.url), 'utf8')
const start = src.indexOf('function classifyClaim')
const end = src.indexOf('// ─── Schemas')
assert.ok(start > 0 && end > start, 'inlined-logic block markers must exist in the workflow source')
const inlined = new Function(src.slice(start, end) +
  '\nreturn { classifyClaim, voteFromReaderVerdict, summarizeRun, planBudget, shouldReflect, gradeClaims }')()

const libFns = {
  classifyClaim: vlib.classifyClaim,
  voteFromReaderVerdict: vlib.voteFromReaderVerdict,
  summarizeRun: vlib.summarizeRun,
  planBudget: blib.planBudget,
  shouldReflect: blib.shouldReflect,
  gradeClaims: tlib.gradeClaims,
}

const VECTORS = {
  classifyClaim: [
    { votes: [null, null, null], refutationsRequired: 2 },
    { votes: [{ refuted: true }, { refuted: true }, { refuted: false }], refutationsRequired: 2 },
    { votes: [{ refuted: true }, null, null], refutationsRequired: 2 },
    { votes: [{ refuted: false }, { refuted: false }], refutationsRequired: 2 },
    { votes: [{ refuted: false, searchDegraded: true }, { refuted: false }, { refuted: false }], refutationsRequired: 2 },
    {},
  ],
  voteFromReaderVerdict: [
    { verdict: 'supported' }, { verdict: 'refuted' }, { verdict: 'unconfirmed' },
    { verdict: 'supported', fetchFailed: true }, { verdict: 'supported', searchDegraded: true }, {},
  ],
  summarizeRun: [
    [{ status: 'confirmed' }, { status: 'unverified' }],
    [{ status: 'unverified' }, { status: 'unverified' }, { status: 'unverified' }],
    [{ status: 'refuted' }, { status: 'unverified' }],          // the branch that drifted (D1)
    [{ status: 'refuted' }, { status: 'refuted' }],
    [],
  ],
  planBudget: [
    { maxFetch: 20, maxRounds: 1, reflectReserveRatio: 0.3 },
    { maxFetch: 2, maxRounds: 1, reflectReserveRatio: 0.3 },
    { maxFetch: 15, maxRounds: 0 },
    { maxFetch: 6, maxRounds: 5, reflectReserveRatio: 0.3 },
    {},
  ],
  shouldReflect: [
    { round: 0, maxRounds: 1, centralGaps: ['g'], reflectSlotsRemaining: 6 },
    { round: 0, maxRounds: 1, centralGaps: [], reflectSlotsRemaining: 6 },
    { round: 1, maxRounds: 1, centralGaps: ['g'], reflectSlotsRemaining: 6 },
    { round: 0, maxRounds: 1, centralGaps: ['g'], reflectSlotsRemaining: 0 },
  ],
  gradeClaims: [
    [{ status: 'confirmed', quote: 'q' }, { status: 'unverified', quote: 'q' },
     { status: 'unverified', quote: '' }, { status: 'refuted', quote: 'q' }],
    [],
  ],
}

for (const [name, vectors] of Object.entries(VECTORS)) {
  test(`inlined ${name} is behaviorally identical to lib`, () => {
    assert.equal(typeof inlined[name], 'function', `workflow must inline ${name}`)
    for (const v of vectors) {
      assert.deepEqual(inlined[name](v), libFns[name](v),
        `${name} drifted for vector ${JSON.stringify(v).slice(0, 100)}`)
    }
  })
}
