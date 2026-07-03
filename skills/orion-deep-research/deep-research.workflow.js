export const meta = {
  name: 'orion-deep-research',
  description: 'Fork of native deep-research: complexity-scaled scope, fan-out web search, batched first-hand source-reader verification with honest abstention accounting, a bounded reflect/knowledge-gap loop, and tier-graded cited synthesis. Returns a structured report OBJECT; the orion-deep-research SKILL wrapper persists it durably (quality-gated) to a research vault.',
  whenToUse: 'Invoked by the orion-deep-research skill. Pass the refined question via args. The wrapper (main loop) judge-gates and persists the durable vault artifact after this returns - this script has NO filesystem access.',
  phases: [
    { title: 'Scope', detail: 'Decompose question into sub-questions + complexity-scaled search angles' },
    { title: 'Search', detail: 'One WebSearch agent per angle; URL-dedup; fetch under a reserved round-1 budget' },
    { title: 'Verify', detail: 'Batched source-reader (one reader per source) + adversarial spot-check on CENTRAL claims; abstention-honest' },
    { title: 'Reflect', detail: 'Bounded knowledge-gap round on unanswered CENTRAL sub-questions, reserved fetch budget' },
    { title: 'Synthesize', detail: 'Tier-grade, merge dupes, number citations, cite sources' },
  ],
}

// ─────────────────────────────────────────────────────────────────────────────
// orion-deep-research - forked from native /deep-research (compiled into the CC
// binary, unforkable in place). Estate additions over native:
//   1. Honest verification accounting - an unverifiable claim (abstained /
//      rate-limited / dead-search) is NEVER folded into `refuted`. (SPEC S1/S2)
//   2. Batched source-reader verify (one reader per SOURCE, capped) replacing the
//      per-claim x lens refuter fan-out that tripped the shared throttle; plus a
//      diverse-lens adversarial spot-check on CENTRAL claims only. (SPEC S7)
//   3. A bounded reflect/knowledge-gap loop with a RESERVED fetch budget so it
//      actually fires (never armed-but-never-fires). (SPEC S3)
//   4. TIER1/TIER2 claim grading. (SPEC S4)
//
// The pure logic below is INLINED from the TDD-tested lib/*.mjs (the Workflow
// sandbox cannot import). KEEP IN SYNC with lib/ + `npm test`. Sandbox limits: no
// filesystem, no Date.now()/Math.random(). This script only RETURNS the report
// object; the SKILL wrapper judge-gates + persists it.
// ─────────────────────────────────────────────────────────────────────────────

const REFUTATIONS_REQUIRED = 2      // vote quorum, matches native
const MAX_FETCH = 20                // per-RUN source cap (spans all rounds)
const MAX_VERIFY_CLAIMS = 25
const MAX_REFLECT_ROUNDS = 1
const REFLECT_RESERVE_RATIO = 0.3
const SOURCE_READER_CAP = 16        // throttle-safe: readers per round
const CENTRAL_SPOTCHECK_LENSES = ['contradiction-search', 'primary-source-existence']
const qualRank = { primary: 0, secondary: 1, blog: 2, forum: 3, unreliable: 4 }

// ─── Inlined tested pure logic (sync with lib/verify.mjs, lib/budget.mjs, lib/tiers.mjs).
// DRIFT IS TESTED: lib/drift.test.mjs extracts this block from the source and runs both
// copies against shared vectors - a divergence is a red test, not a silent lie. ───
function classifyClaim({ votes = [], refutationsRequired = 2 } = {}) {
  const degraded = votes.filter(v => v && v.searchDegraded).length
  const valid = votes.filter(v => v && !v.searchDegraded)
  const refutingVotes = valid.filter(v => v.refuted).length
  const supportingVotes = valid.length - refutingVotes
  const abstained = votes.length - valid.length
  let status
  if (refutingVotes >= refutationsRequired) status = 'refuted'
  else if (valid.length >= refutationsRequired && refutingVotes < refutationsRequired) status = 'confirmed'
  else status = 'unverified'
  return { status, validVotes: valid.length, refutingVotes, supportingVotes, abstained, degraded }
}
function voteFromReaderVerdict({ verdict, searchDegraded = false, fetchFailed = false } = {}) {
  if (fetchFailed) return null
  if (searchDegraded) return { refuted: false, searchDegraded: true }
  if (verdict === 'refuted') return { refuted: true }
  if (verdict === 'supported') return { refuted: false }
  return null
}
function summarizeRun(claims = []) {
  const counts = { confirmed: 0, refuted: 0, unverified: 0 }
  for (const c of claims) {
    if (c.status === 'confirmed') counts.confirmed++
    else if (c.status === 'refuted') counts.refuted++
    else counts.unverified++
  }
  const { confirmed: nc, refuted: nr, unverified: nu } = counts
  let verdict
  if (nc) verdict = `${nc} confirmed, ${nr} refuted, ${nu} unverified`
  else if (nu && !nr) verdict = `INCONCLUSIVE: ${nu} unverified (abstained/rate-limited), 0 refuted - re-run verification before reporting`
  else if (nu && nr) verdict = `INCONCLUSIVE: 0 confirmed, ${nr} refuted, ${nu} unverified (abstained/rate-limited) - ${nu} still need verification`
  else if (nr && !nu) verdict = `All ${nr} claims refuted`
  else verdict = 'no claims'
  return { counts, verdict, inconclusive: nc === 0 && nu > 0, incomplete: nu > 0 }
}
function planBudget({ maxFetch = 20, maxRounds = 1, reflectReserveRatio = 0.3 } = {}) {
  maxRounds = Math.max(0, Math.floor(maxRounds))
  if (maxRounds === 0 || maxFetch < 2) return { round1Slots: maxFetch, reflectSlotsPerRound: 0, reflectReserveTotal: 0, maxRounds: 0 }
  let reserve = Math.max(maxRounds, Math.ceil(maxFetch * reflectReserveRatio))
  reserve = Math.min(reserve, Math.floor((maxFetch - 1) / 2))
  reserve = Math.max(reserve, 1)
  const effRounds = Math.min(maxRounds, reserve)
  const reflectSlotsPerRound = Math.max(1, Math.floor(reserve / effRounds))
  return { round1Slots: maxFetch - reserve, reflectSlotsPerRound, reflectReserveTotal: reserve, maxRounds: effRounds }
}
function shouldReflect({ round, maxRounds, centralGaps = [], reflectSlotsRemaining = 0 } = {}) {
  return round < maxRounds && centralGaps.length > 0 && reflectSlotsRemaining >= 1
}
function gradeClaims(claims = []) {
  const tier1 = [], tier2 = [], refuted = [], dropped = []
  for (const c of claims) {
    if (c.status === 'confirmed') tier1.push(c)
    else if (c.status === 'refuted') refuted.push(c)
    else if (c.quote && String(c.quote).trim()) tier2.push(c)
    else dropped.push(c)
  }
  return { tier1, tier2, refuted, dropped, counts: { tier1: tier1.length, tier2: tier2.length, refuted: refuted.length, dropped: dropped.length } }
}
// Dedup key keeps CONTENT-BEARING query params (video ids, arxiv ids, pages) and
// strips only tracking noise - review: hostname+pathname-only collapsed genuinely
// distinct sources (youtube?v=A vs ?v=B) into one, silently dropping evidence.
const normURL = u => {
  try {
    const p = new URL(u)
    const params = [...p.searchParams]
      .filter(([k]) => !/^(utm_|fbclid|gclid|ref$|ref_|mc_)/i.test(k))
      .map(([k, v]) => k + '=' + v).sort().join('&')
    return (p.hostname.replace(/^www\./, '') + p.pathname.replace(/\/$/, '') + (params ? '?' + params : '')).toLowerCase()
  } catch { return String(u).toLowerCase() }
}
const hostOf = u => { try { return new URL(u).hostname.replace(/^www\./, '') } catch { return 'src' } }

// ─── Schemas ───
const SCOPE_SCHEMA = {
  type: 'object', required: ['question', 'complexity', 'subQuestions', 'angles'],
  properties: {
    question: { type: 'string' },
    complexity: { enum: ['simple', 'moderate', 'complex'] },
    subQuestions: { type: 'array', minItems: 1, maxItems: 8, items: { type: 'string' } },
    angles: { type: 'array', minItems: 2, maxItems: 8, items: {
      type: 'object', required: ['label', 'query'],
      properties: { label: { type: 'string' }, query: { type: 'string' }, rationale: { type: 'string' } },
    }},
  },
}
const SEARCH_SCHEMA = {
  type: 'object', required: ['results'],
  properties: { results: { type: 'array', maxItems: 6, items: {
    type: 'object', required: ['url', 'title', 'relevance'],
    properties: { url: { type: 'string' }, title: { type: 'string' }, snippet: { type: 'string' }, relevance: { enum: ['high', 'medium', 'low'] } },
  }}},
}
const EXTRACT_SCHEMA = {
  type: 'object', required: ['claims', 'sourceQuality'],
  properties: {
    sourceQuality: { enum: ['primary', 'secondary', 'blog', 'forum', 'unreliable'] },
    publishDate: { type: 'string' },
    claims: { type: 'array', maxItems: 5, items: {
      type: 'object', required: ['claim', 'quote', 'importance'],
      properties: { claim: { type: 'string' }, quote: { type: 'string' }, importance: { enum: ['central', 'supporting', 'tangential'] } },
    }},
  },
}
// Batched source-reader: adjudicates ALL of one source's claims first-hand.
const READER_SCHEMA = {
  type: 'object', required: ['verdicts'],
  properties: {
    fetchFailed: { type: 'boolean' },
    verdicts: { type: 'array', items: {
      type: 'object', required: ['claimIndex', 'verdict'],
      properties: {
        claimIndex: { type: 'number' },
        verdict: { enum: ['supported', 'refuted', 'unconfirmed'] }, // does THIS source actually support the claim?
        evidence: { type: 'string' },
      },
    }},
  },
}
// Adversarial cross-source spot-check for CENTRAL claims (diverse lenses).
const SPOTCHECK_SCHEMA = {
  type: 'object', required: ['refuted', 'searchDegraded', 'evidence'],
  properties: {
    refuted: { type: 'boolean' },
    searchDegraded: { type: 'boolean' }, // true if the voter's own search returned nothing (S2)
    evidence: { type: 'string' },
    confidence: { enum: ['high', 'medium', 'low'] },
  },
}
const REFLECT_SCHEMA = {
  type: 'object', required: ['centralGaps', 'followUpQueries'],
  properties: {
    centralGaps: { type: 'array', items: { type: 'string' } }, // CENTRAL sub-questions still unanswered
    followUpQueries: { type: 'array', maxItems: 4, items: {
      type: 'object', required: ['label', 'query'], properties: { label: { type: 'string' }, query: { type: 'string' } },
    }},
  },
}
const REPORT_SCHEMA = {
  type: 'object', required: ['summary', 'findings', 'caveats'],
  properties: {
    summary: { type: 'string' },
    findings: { type: 'array', items: {
      type: 'object', required: ['claim', 'confidence', 'sources', 'evidence'],
      properties: { claim: { type: 'string' }, confidence: { enum: ['high', 'medium', 'low'] }, sources: { type: 'array', items: { type: 'string' } }, evidence: { type: 'string' } },
    }},
    caveats: { type: 'string' },
    openQuestions: { type: 'array', items: { type: 'string' } },
  },
}

// ─── Phase 0: Scope (complexity-scaled) ───
phase('Scope')
const QUESTION = (typeof args === 'string' && args.trim()) || ''
if (!QUESTION) return { error: "No research question provided. Pass it as args." }

// Count every agent dispatch for honest stats (review: the old formula undercounted
// spot-check + reflect calls). All call sites go through callAgent.
let agentCallsMade = 0
const callAgent = (prompt, opts) => { agentCallsMade++; return agent(prompt, opts) }

const scope = await callAgent(
  'Decompose this research question for a multi-source deep-research run.\n\n' +
  '## Question\n' + QUESTION + '\n\n' +
  '## Task\n' +
  '1. Assess complexity: simple (a single fact/definition), moderate (a comparison or a few facets), or complex (multi-part, multi-hop, or contested).\n' +
  '2. List the CENTRAL sub-questions the answer must cover (2-3 for simple, up to ~6-8 for complex). These are what a later step measures coverage against.\n' +
  '3. Generate search angles sized to complexity: ~2-3 for simple, ~4-5 for moderate, ~6-8 for complex. Pick angles that suit the domain (e.g. broad/primary, academic/technical, recent-news, contrarian/skeptical, practitioner). Make queries specific; avoid redundancy.\n\n' +
  'Structured output only.',
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA }
).catch(() => null)
if (!scope) return { error: 'Scope agent returned no result.' }
const budget = planBudget({ maxFetch: MAX_FETCH, maxRounds: MAX_REFLECT_ROUNDS, reflectReserveRatio: REFLECT_RESERVE_RATIO })
log('Q: ' + QUESTION.slice(0, 80) + (QUESTION.length > 80 ? '…' : ''))
log('Complexity=' + scope.complexity + ' · ' + scope.angles.length + ' angles · ' + scope.subQuestions.length + ' sub-questions')
log('Budget: round1=' + budget.round1Slots + ' fetch, reflect=' + budget.reflectSlotsPerRound + '/round x ' + budget.maxRounds)

// ─── Shared state across rounds ───
const seen = new Map()
const dupes = []
const relRank = { high: 0, medium: 1, low: 2 }
const allSources = []          // {url,title,angle,sourceQuality,claims:[...]}
const runFailures = []         // REAL infra failures only (rate-limit, dead search, fetch/reader/spot crash) - the recovery gate keys on this
const runNotes = []            // benign capacity/accounting/quality notes (cap spillover, citation flags) - NOT infra, must not trip recovery
const citationIssues = []      // findings whose cited [n] did not resolve to the registry (S8)

const SEARCH_PROMPT = (angle) =>
  '## Web Searcher: ' + angle.label + '\n\nResearch question: "' + QUESTION + '"\n\n' +
  'Your angle: **' + angle.label + '** - ' + (angle.rationale || '') + '\nSearch query: `' + angle.query + '`\n\n' +
  '## Task\nUse WebSearch (searxng if available). Return the top 4-6 results most relevant to the ORIGINAL question. Skip SEO spam. Short snippet each.\n\nStructured output only.'

const FETCH_PROMPT = (source, angle) =>
  '## Source Extractor\n\nResearch question: "' + QUESTION + '"\n\n' +
  'Fetch and extract key claims from:\n**URL:** ' + source.url + '\n**Title:** ' + source.title + '\n**Found via:** ' + angle + '\n\n' +
  '## Task\n1. WebFetch the page.\n2. Assess source quality (primary/secondary/blog/forum/unreliable).\n3. Extract 2-5 FALSIFIABLE claims bearing on the question, each with a direct supporting quote and importance (central/supporting/tangential). Mark a claim central ONLY if it directly answers a core sub-question.\n4. Note publish date.\nIf fetch fails/paywalled/irrelevant: claims:[] sourceQuality:"unreliable".\n\nStructured output only.'

// Run one search->dedup->fetch/extract round under a fetch-slot budget; append to allSources.
async function runSearchRound(queries, slots, phaseName) {
  let remaining = slots
  const roundSources = []
  await pipeline(
    queries,
    q => callAgent(SEARCH_PROMPT(q), { label: 'search:' + q.label, phase: phaseName, schema: SEARCH_SCHEMA })
      .then(r => { if (!r) { runFailures.push('search returned nothing for angle "' + q.label + '"'); return null } return { angle: q.label, results: r.results } })
      .catch(() => { runFailures.push('search crashed for angle "' + q.label + '"'); return null }),
    sr => {
      if (!sr) return []
      const sorted = [...sr.results].sort((a, b) => relRank[a.relevance] - relRank[b.relevance])
      const novel = sorted.filter(r => {
        const key = normURL(r.url)
        if (seen.has(key)) { dupes.push({ url: r.url, angle: sr.angle }); return false }
        if (remaining <= 0) return false
        seen.set(key, sr.angle); remaining--; return true
      })
      return parallel(novel.map(src => () =>
        callAgent(FETCH_PROMPT(src, sr.angle), { label: 'fetch:' + hostOf(src.url), phase: phaseName, schema: EXTRACT_SCHEMA })
          .then(ext => {
            if (!ext) { runFailures.push('extract returned nothing for ' + src.url); return null }
            return { url: src.url, title: src.title, angle: sr.angle, sourceQuality: ext.sourceQuality, publishDate: ext.publishDate,
              claims: (ext.claims || []).map(c => ({ ...c, sourceUrl: src.url, sourceQuality: ext.sourceQuality })) }
          })
          .catch(e => { runFailures.push('fetch failed: ' + src.url); return { url: src.url, title: src.title, angle: sr.angle, sourceQuality: 'unreliable', claims: [] } })
      ))
    }
  ).then(results => { for (const s of results.flat().filter(Boolean)) { roundSources.push(s); allSources.push(s) } })
  return roundSources
}

// Batched verification of one round's sources. One reader per source (capped) does
// a first-hand faithfulness check of ALL that source's claims; CENTRAL claims also
// get diverse-lens adversarial spot-checks. Returns classified claims (with status).
async function verifyRound(sources) {
  const withClaims = sources.filter(s => s.claims && s.claims.length)
  const capped = withClaims.slice(0, SOURCE_READER_CAP)
  if (withClaims.length > capped.length) runNotes.push((withClaims.length - capped.length) + ' sources exceeded reader cap ' + SOURCE_READER_CAP + '; their claims default to unverified')

  const READER_PROMPT = (s) =>
    '## Source Reader (first-hand faithfulness check)\n\nResearch question: "' + QUESTION + '"\n\n' +
    'Re-read this ONE source and judge, for EACH listed claim, whether THIS SOURCE actually supports it (not whether it is true in general).\n' +
    '**URL:** ' + s.url + '\n\n## Claims (adjudicate every one by claimIndex)\n' +
    s.claims.map((c, i) => i + '. "' + c.claim + '"  [extractor quote: "' + c.quote + '"]').join('\n') + '\n\n' +
    '## Task\nWebFetch the URL. For each claimIndex return verdict: "supported" (the source states/backs it), "refuted" (the source contradicts it), or "unconfirmed" (the source does not actually say this / quote is an overreach / fetch failed). Set fetchFailed:true if the page could not be read (then every verdict is unconfirmed).\n\nStructured output only.'

  const readers = await parallel(capped.map(s => () =>
    callAgent(READER_PROMPT(s), { label: 'read:' + hostOf(s.url), phase: 'Verify', schema: READER_SCHEMA })
      .then(r => ({ url: s.url, ok: !!r && !r.fetchFailed, verdicts: (r && r.verdicts) || [] }))
      .catch(() => { runFailures.push('reader crashed for ' + s.url); return { url: s.url, ok: false, verdicts: [] } })
  ))
  const readerByUrl = new Map(readers.map(r => [r.url, r]))

  // Flatten claims, attach reader verdict + a stable index.
  const roundClaims = []
  for (const s of sources) {
    const rd = readerByUrl.get(s.url)
    ;(s.claims || []).forEach((c, i) => {
      let rv = { fetchFailed: true } // capped-out or missing reader → abstain (unverified), never refuted
      if (rd && rd.ok) {
        const match = rd.verdicts.find(v => v.claimIndex === i)
        rv = match ? { verdict: match.verdict } : { verdict: 'unconfirmed' }
      }
      roundClaims.push({ ...c, sourceUrl: s.url, _idx: roundClaims.length, _readerVote: voteFromReaderVerdict(rv) })
    })
  }

  // Diverse-lens adversarial spot-check on CENTRAL claims only (throttle-safe: bounded
  // to the top MAX_VERIFY_CLAIMS by source quality; the rest stay reader-only → TIER 2).
  const centralAll = roundClaims.filter(c => c.importance === 'central')
  const central = [...centralAll].sort((a, b) => (qualRank[a.sourceQuality] ?? 9) - (qualRank[b.sourceQuality] ?? 9)).slice(0, MAX_VERIFY_CLAIMS)
  if (centralAll.length > central.length) runNotes.push((centralAll.length - central.length) + ' central claims over spot-check cap ' + MAX_VERIFY_CLAIMS + ' (reader-only → TIER 2)')
  const spotByIdx = new Map()
  if (central.length) {
    const SPOT_PROMPT = (c, lens) =>
      '## Adversarial spot-check (lens: ' + lens + ')\n\nBe SKEPTICAL. Try to REFUTE this CENTRAL claim using evidence OUTSIDE its source.\n\n' +
      '## Research question\n' + QUESTION + '\n## Claim\n"' + c.claim + '"\n**Its source:** ' + c.sourceUrl + '\n\n' +
      '## Task\n' + (lens === 'contradiction-search'
        ? 'WebSearch for CREDIBLE contradicting evidence. refuted=true if any credible source disputes/heavily qualifies it.'
        : 'Verify the underlying primary source EXISTS and actually says this (fetch it / gh api / official docs). refuted=true if the primary source is missing or does not support the claim.') + '\n' +
      'CRITICAL: if your search returns ZERO results (engine degraded), set searchDegraded=true - do NOT report "not refuted" on an un-searched sweep. Default refuted=true only on real contradicting evidence, otherwise refuted=false with searchDegraded reflecting whether you could actually check.\n\nStructured output only.'
    await parallel(central.flatMap(c =>
      CENTRAL_SPOTCHECK_LENSES.map(lens => () =>
        callAgent(SPOT_PROMPT(c, lens), { label: 'spot:' + lens.slice(0, 7) + ':' + c._idx, phase: 'Verify', schema: SPOTCHECK_SCHEMA })
          .then(v => {
            const arr = spotByIdx.get(c._idx) || []
            if (!v) { runFailures.push('spot-check abstained (' + lens + ') for central claim'); arr.push(null) }
            else { if (v.searchDegraded) runFailures.push('spot-check search degraded (' + lens + ')'); arr.push({ refuted: !!v.refuted, searchDegraded: !!v.searchDegraded }) }
            spotByIdx.set(c._idx, arr)
          })
          // review-convergent fix: a THROWN spot-check (rate-limit) must be a recorded
          // abstention - not a run-crash, and not a silently-missing vote that lets the
          // recovery gate sleep through a degraded run.
          .catch(() => {
            runFailures.push('spot-check crashed (' + lens + ') - treated as abstention')
            const arr = spotByIdx.get(c._idx) || []
            arr.push(null)
            spotByIdx.set(c._idx, arr)
          })
      )
    ))
  }

  // Classify: reader vote + any central spot-check votes → status.
  return roundClaims.map(c => {
    const votes = [c._readerVote, ...(spotByIdx.get(c._idx) || [])]
    const cl = classifyClaim({ votes, refutationsRequired: REFUTATIONS_REQUIRED })
    log('"' + c.claim.slice(0, 46) + '…": ' + cl.status + ' (' + cl.validVotes + 'v/' + cl.refutingVotes + 'r' + (cl.degraded ? '/' + cl.degraded + 'deg' : '') + ')')
    return { claim: c.claim, quote: c.quote, importance: c.importance, sourceUrl: c.sourceUrl, sourceQuality: c.sourceQuality, ...cl }
  })
}

// ─── Round 0 ───
phase('Search')
await runSearchRound(scope.angles, budget.round1Slots, 'Search')
log('Round 0: ' + allSources.length + ' sources, ' + allSources.flatMap(s => s.claims).length + ' claims')

phase('Verify')
const claimPool = []
const seenClaimKey = new Set()
const mergeClaims = (classified) => {
  for (const c of classified) {
    const k = (c.claim || '').toLowerCase().trim() + '|' + normURL(c.sourceUrl)
    if (seenClaimKey.has(k)) continue
    seenClaimKey.add(k); claimPool.push(c)
  }
}
mergeClaims(await verifyRound(allSources))

// ─── Reflect rounds (bounded, reserved budget) ───
let round = 0
let reflectFired = false
while (round < budget.maxRounds) {
  const confirmedSoFar = claimPool.filter(c => c.status === 'confirmed')
  const reflect = await callAgent(
    '## Reflect: find remaining CENTRAL knowledge gaps\n\nResearch question: "' + QUESTION + '"\n\n' +
    '## Central sub-questions\n' + scope.subQuestions.map((q, i) => i + '. ' + q).join('\n') + '\n\n' +
    '## Confirmed so far (' + confirmedSoFar.length + ')\n' + (confirmedSoFar.slice(0, 20).map(c => '- ' + c.claim).join('\n') || '(none confirmed yet)') + '\n\n' +
    '## Task\nName the CENTRAL sub-questions that still have NO confirmed support (or whose central claim was refuted). For each real gap, emit ONE targeted follow-up search query re-anchored to the ORIGINAL question. If every central sub-question is answered, return empty arrays.\n\nStructured output only.',
    { label: 'reflect:' + round, phase: 'Reflect', schema: REFLECT_SCHEMA }
  ).catch(() => { runFailures.push('reflect crashed (round ' + round + ') - loop closes without a reflect round'); return null })
  const gaps = (reflect && reflect.centralGaps) || []
  if (!shouldReflect({ round, maxRounds: budget.maxRounds, centralGaps: gaps, reflectSlotsRemaining: budget.reflectSlotsPerRound })) {
    log('Reflect gate closed (round ' + round + ', gaps=' + gaps.length + '): stopping')
    break
  }
  log('Reflect round ' + (round + 1) + ': ' + gaps.length + ' central gaps → ' + (reflect.followUpQueries || []).length + ' queries')
  const before = allSources.length
  await runSearchRound(reflect.followUpQueries, budget.reflectSlotsPerRound, 'Reflect')
  const newSources = allSources.slice(before)
  if (newSources.length) { mergeClaims(await verifyRound(newSources)); reflectFired = true }
  round++
}

// ─── Synthesize (tier-graded, cited) ───
phase('Synthesize')
const graded = gradeClaims(claimPool)
const runSummary = summarizeRun(claimPool)
log('Verify complete: ' + runSummary.verdict)

// numbered source registry (S8)
const citedUrls = [...new Set([...graded.tier1, ...graded.tier2].map(c => c.sourceUrl))]
const registry = citedUrls.map((u, i) => ({ n: i + 1, url: u }))
const regByUrl = new Map(registry.map(r => [r.url, r.n]))

if (graded.tier1.length === 0) {
  // No vote-confirmed finding. Do NOT synthesize confident findings; return the honest
  // tier-2 surface + the verdict so the wrapper can quarantine/label it.
  return {
    question: QUESTION, complexity: scope.complexity,
    summary: runSummary.inconclusive
      ? 'INCONCLUSIVE - no claim reached the verification quorum. ' + runSummary.verdict + '. ' + (runFailures.length ? runFailures.length + ' infra failure(s) - likely recoverable via resume/reclassify.' : '')
      : runSummary.verdict,
    findings: [],
    tier2: graded.tier2.map(c => ({ claim: c.claim, quote: c.quote, source: c.sourceUrl, sourceRef: regByUrl.get(c.sourceUrl) || null, status: c.status })),
    refuted: graded.refuted.map(c => ({ claim: c.claim, source: c.sourceUrl })),
    citationIssues,
    sources: registry,
    verification: { verdict: runSummary.verdict, counts: runSummary.counts, inconclusive: runSummary.inconclusive, incomplete: runSummary.incomplete, failures: runFailures, notes: runNotes },
    stats: roundStats(),
  }
}

// NOTE: claim headers deliberately avoid [brackets] - bracketed [n] numbers are
// RESERVED for the 1-based source registry, so the synthesizer cannot confuse a
// claim index with a citation ref.
const tier1Block = graded.tier1.map((c, i) =>
  '### Claim ' + (i + 1) + ': ' + c.claim + '\nStatus: confirmed (' + c.validVotes + 'v/' + c.refutingVotes + 'r) · Source: ' + c.sourceUrl + ' [' + (regByUrl.get(c.sourceUrl) || '?') + '] (' + c.sourceQuality + ')\nQuote: "' + c.quote + '"'
).join('\n')
const tier2Block = graded.tier2.length
  ? '\n\n## TIER 2 (extracted, single-source / UNVERIFIED - surface with a caveat, do not present as confirmed)\n' +
    graded.tier2.map(c => '- "' + c.claim + '" (' + c.sourceUrl + ' [' + (regByUrl.get(c.sourceUrl) || '?') + '])').join('\n')
  : ''

const report = await callAgent(
  '## Synthesis: tier-graded research report\n\n**Question:** ' + QUESTION + '\n\n' +
  graded.tier1.length + ' claims are TIER 1 (passed adversarial verification). Merge semantic duplicates and synthesize FINDINGS from TIER 1 only.\n\n' +
  '## TIER 1 confirmed claims\n' + tier1Block + tier2Block + '\n\n' +
  '## Instructions\n' +
  '1. Merge claims that say the same thing; combine their sources (cite the bracketed [n] source numbers).\n' +
  '2. Group into findings, each directly answering the question. Every finding rests on TIER 1 claims.\n' +
  '3. Per-finding confidence: high (multiple primary sources / corroborated), medium (secondary or single primary), low (single blog-quality).\n' +
  '4. In `sources`, list the [n] numbers backing each finding.\n' +
  '5. 3-5 sentence executive summary. Note caveats (weak sources, time-sensitivity, and that TIER 2 items are UNVERIFIED). 2-4 open questions.\n' +
  'Do NOT present any TIER 2 item as an established finding.\n\nStructured output only.',
  { label: 'synthesize', phase: 'Synthesize', schema: REPORT_SCHEMA }
).catch(() => { runFailures.push('synthesize crashed - salvaging verified claims unmerged'); return null })
if (!report) {
  return {
    question: QUESTION, complexity: scope.complexity,
    summary: 'Synthesis skipped/failed - returning ' + graded.tier1.length + ' TIER 1 claims unmerged.',
    findings: [], tier1Raw: graded.tier1.map(c => ({ claim: c.claim, source: c.sourceUrl, quote: c.quote })),
    // shape kept consistent with the other exit paths (review: this branch diverged)
    tier2: graded.tier2.map(c => ({ claim: c.claim, quote: c.quote, source: c.sourceUrl, sourceRef: regByUrl.get(c.sourceUrl) || null, status: c.status })),
    refuted: graded.refuted.map(c => ({ claim: c.claim, source: c.sourceUrl })),
    citationIssues,
    sources: registry,
    verification: { verdict: runSummary.verdict, counts: runSummary.counts, inconclusive: runSummary.inconclusive, incomplete: runSummary.incomplete, failures: runFailures, notes: runNotes },
    stats: roundStats(),
  }
}

function roundStats() {
  return {
    complexity: scope.complexity,
    angles: scope.angles.length,
    subQuestions: scope.subQuestions.length,
    reflectRoundsRun: round,
    reflectFired,
    sourcesFetched: allSources.length,
    urlDupes: dupes.length,
    claimsPooled: claimPool.length,
    tier: graded.counts,
    verification: runSummary.counts,
    budget,
    failures: runFailures.length,
    notes: runNotes.length,
    citationIssues: citationIssues.length,
    agentCalls: agentCallsMade, // exact count via callAgent (old formula undercounted)
  }
}

// S8 enforced in CODE, not just prompt: every cited [n] must resolve to the numbered
// registry; unresolved refs are flagged (citationIssues + an advisory NOTE), never shipped
// silently. Findings are stamped TIER 1 (S4) - synthesis draws from TIER 1 claims only.
// A source is a citation "[3] https://..." OR a bare "3"; read the LEADING [n] ref - never
// strip all digits (that grabs digits out of the URL, e.g. 2606.26300, false-flagging every
// finding whose source carries a URL).
const validNs = new Set(registry.map(r => String(r.n)))
const refNum = s => { const m = String(s).match(/\[(\d+)\]/) || String(s).match(/^\s*(\d+)\b/); return m ? m[1] : null }
const stampedFindings = (report.findings || []).map(f => {
  const unresolved = (f.sources || []).filter(c => { const n = refNum(c); return !n || !validNs.has(n) })
  if (unresolved.length) citationIssues.push({ finding: (f.claim || '').slice(0, 80), sources: f.sources })
  return { ...f, tier: 'TIER 1' }
})
if (citationIssues.length) runNotes.push(citationIssues.length + ' finding(s) cite source number(s) that do not resolve to the registry')

return {
  question: QUESTION,
  complexity: scope.complexity,
  ...report,
  findings: stampedFindings,
  citationIssues,
  tier2: graded.tier2.map(c => ({ claim: c.claim, quote: c.quote, source: c.sourceUrl, sourceRef: regByUrl.get(c.sourceUrl) || null, status: c.status })),
  refuted: graded.refuted.map(c => ({ claim: c.claim, source: c.sourceUrl })),
  sources: registry,
  verification: { verdict: runSummary.verdict, counts: runSummary.counts, inconclusive: runSummary.inconclusive, incomplete: runSummary.incomplete, failures: runFailures, notes: runNotes },
  stats: roundStats(),
}
