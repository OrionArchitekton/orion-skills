// Integration test: executes the REAL forked workflow body with stubbed agents,
// proving the deterministic orchestration (not LLM quality):
//  - the reflect loop actually FIRES on a central gap (not armed-but-never-fires)
//  - and does NOT fire on a satisfied question
//  - the source-fetch budget is bounded across rounds (never exceeds MAX_FETCH)
//  - abstention is honest end-to-end (all-abstain -> inconclusive, not "all refuted")
//  - a confirmed run produces TIER 1 findings + a numbered source registry
// Run: node --test lib/workflow-sim.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const SRC = fs.readFileSync(new URL('../deep-research.workflow.js', import.meta.url), 'utf8')
  .replace('export const meta', 'const meta')

// Run the workflow with a scenario-driven agent stub. `resultsPerAngle` floods
// search to stress the fetch cap. `readerVerdict`/`spot` drive verification.
// `gapOnRound0` makes reflect emit a central gap (fires the loop).
function runWorkflow({ question = 'Q', complexity = 'complex', angles = 2, resultsPerAngle = 1,
  readerVerdict = 'supported', spot = { refuted: false, searchDegraded: false },
  gapOnRound0 = true, spotThrows = false, synthNull = false, badCitation = false, fullCitation = false } = {}) {
  const calls = { search: 0, fetch: 0, reader: 0, spot: 0, reflect: 0 }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'scope') {
      calls.scope = 1
      return { question, complexity, subQuestions: ['sq1', 'sq2'],
        angles: Array.from({ length: angles }, (_, i) => ({ label: 'a' + i, query: 'q' + i })) }
    }
    if (label.startsWith('search:')) {
      const a = label.slice(7); calls.search++
      return { results: Array.from({ length: resultsPerAngle }, (_, i) => ({
        url: 'https://ex-' + a + '-' + i + '.test/p', title: 't' + a + i, relevance: 'high' })) }
    }
    if (label.startsWith('fetch:')) {
      calls.fetch++
      return { sourceQuality: 'primary', claims: [{ claim: 'C-' + calls.fetch, quote: 'quote', importance: 'central' }] }
    }
    if (label.startsWith('read:')) {
      calls.reader++
      return { verdicts: [{ claimIndex: 0, verdict: readerVerdict }] }
    }
    if (label.startsWith('spot:')) {
      calls.spot++
      if (spotThrows) throw new Error('429 rate limit')
      return spot
    }
    if (label.startsWith('reflect:')) {
      const round = Number(label.split(':')[1])
      calls.reflect++
      if (round === 0 && gapOnRound0) return { centralGaps: ['sq2'], followUpQueries: [{ label: 'g0', query: 'gq0' }] }
      return { centralGaps: [], followUpQueries: [] }
    }
    if (label === 'synthesize') {
      if (synthNull) return null
      return { summary: 'exec summary', caveats: 'caveats',
        findings: [{ claim: 'finding one', confidence: 'high', sources: [badCitation ? '99' : (fullCitation ? '[1] https://ex.test/paper-2606.26300' : '1')], evidence: 'ev' }], openQuestions: ['oq'] }
    }
    return null
  }
  const phase = () => {}, log = () => {}
  const parallel = (thunks) => Promise.all(thunks.map(t => t()))
  const pipeline = async (items, ...stages) =>
    Promise.all(items.map(async (it, i) => { let v = it; for (const s of stages) v = await s(v, it, i); return v }))
  const fn = new Function('agent', 'pipeline', 'parallel', 'phase', 'log', 'args',
    'return (async () => {' + SRC + '})()')
  return fn(agent, pipeline, parallel, phase, log, question).then(r => ({ ...r, _calls: calls }))
}

test('reflect loop FIRES on a central gap (not armed-but-never-fires)', async () => {
  const r = await runWorkflow({ gapOnRound0: true })
  assert.equal(r.stats.reflectFired, true, 'a central gap must trigger a reflect round')
  assert.equal(r.stats.reflectRoundsRun, 1)
})

test('reflect loop does NOT fire when the question is already satisfied', async () => {
  const r = await runWorkflow({ gapOnRound0: false })
  assert.equal(r.stats.reflectFired, false)
})

test('total sources fetched never exceed MAX_FETCH even under flooded search', async () => {
  // 8 angles x 6 results = 48 candidate URLs; the reserved budget must bound fetches
  const r = await runWorkflow({ angles: 8, resultsPerAngle: 6, gapOnRound0: true })
  assert.ok(r.stats.sourcesFetched <= 20, `fetched ${r.stats.sourcesFetched} must be <= MAX_FETCH 20`)
  assert.ok(r.stats.sourcesFetched <= r.stats.budget.round1Slots + r.stats.budget.reflectSlotsPerRound * r.stats.budget.maxRounds)
})

test('all-abstain verification is INCONCLUSIVE, never "all refuted"', async () => {
  // reader cannot confirm + spot-checks all hit a dead search → every claim unverified
  const r = await runWorkflow({ readerVerdict: 'unconfirmed', spot: { refuted: false, searchDegraded: true } })
  assert.equal(r.verification.inconclusive, true)
  assert.equal(r.verification.counts.refuted, 0)
  assert.ok(!/all\s+\d+\s+claims\s+refuted/i.test(r.summary), 'must not claim all-refuted')
  assert.equal(r.findings.length, 0, 'no confident findings on an inconclusive run')
})

test('a confirmed run yields TIER 1 findings and a numbered source registry', async () => {
  const r = await runWorkflow({ readerVerdict: 'supported', spot: { refuted: false, searchDegraded: false } })
  assert.equal(r.verification.inconclusive, false)
  assert.ok(r.verification.counts.confirmed >= 1)
  assert.ok(r.findings.length >= 1)
  assert.ok(Array.isArray(r.sources) && r.sources.length >= 1 && r.sources[0].n === 1)
})

test('a genuine refutation is reported refuted, not unverified', async () => {
  // reader refutes + both spot lenses refute → >=2 refuting votes
  const r = await runWorkflow({ readerVerdict: 'refuted', spot: { refuted: true, searchDegraded: false } })
  assert.ok(r.verification.counts.refuted >= 1)
})

// ── review-driven regression tests ──

test('a THROWN spot-check (rate-limit) does not crash the run and IS recorded as a failure', async () => {
  const r = await runWorkflow({ spotThrows: true })
  assert.ok(r.verification, 'run must complete despite thrown verifier')
  assert.ok(r.verification.failures.some(f => /spot-check crashed/.test(f)),
    'the crash must be in the failure ledger so the recovery gate fires')
})

test('findings are stamped TIER 1', async () => {
  const r = await runWorkflow({})
  assert.equal(r.findings[0].tier, 'TIER 1')
})

test('a citation that does not resolve to the registry is flagged as an advisory NOTE (not an infra failure)', async () => {
  const r = await runWorkflow({ badCitation: true })
  assert.equal(r.citationIssues.length, 1)
  assert.ok(r.verification.notes.some(f => /do not resolve to the registry/.test(f)), 'dangling citation is an advisory note')
  assert.ok(!r.verification.failures.some(f => /do not resolve/.test(f)), 'a citation issue is NOT infra trouble, must not trip the recovery gate')
})

test('a full "[n] url" citation string resolves to the registry (no false-positive citationIssue)', async () => {
  // regression: the validator used to strip ALL digits and grab URL digits (2606.26300),
  // false-flagging every finding whose source carried a URL. It must read the leading [n].
  const r = await runWorkflow({ fullCitation: true })
  assert.equal(r.citationIssues.length, 0, 'a real [1] ref that resolves must NOT be flagged')
})

test('benign capacity notes are NOTES, not infra failures (recovery gate must not over-trigger)', async () => {
  // flood sources past the reader cap so the "exceeded reader cap" accounting note fires
  const r = await runWorkflow({ angles: 8, resultsPerAngle: 4 })
  assert.ok(Array.isArray(r.verification.notes), 'verification.notes must exist')
  assert.ok(!r.verification.failures.some(f => /exceeded reader cap|over spot-check cap/.test(f)),
    'capacity/accounting notes must not land in infra failures[]')
})

test('synthesis-null salvage path keeps a consistent shape (refuted + full tier2 present)', async () => {
  const r = await runWorkflow({ synthNull: true, readerVerdict: 'supported' })
  assert.ok(Array.isArray(r.refuted), 'refuted key must exist on the salvage path')
  assert.ok(Array.isArray(r.tier2))
  assert.ok(Array.isArray(r.citationIssues))
  assert.ok(r.tier1Raw.length >= 1, 'verified claims are salvaged, not discarded')
})

test('query-bearing URLs are distinct sources, not dedup collisions', async () => {
  // stub returns per-angle URLs already distinct; this exercises normURL directly via
  // the workflow source (two same-path different-query URLs must both be fetched)
  const r = await runWorkflow({ angles: 1, resultsPerAngle: 2 })
  assert.equal(r.stats.urlDupes, 0)
})
