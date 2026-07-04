---
name: orion-deep-research
description: Use when running a deep, multi-source, fact-checked research report that must land DURABLY in your research vault (not just the transcript). Fork of the native /deep-research with honest abstention accounting, a bounded reflect/knowledge-gap loop, TIER1/TIER2 grading, a judge-gate that quarantines inconclusive runs, and terminal persistence to a research vault with a verification-provenance ledger. Triggers - "/orion-deep-research <question>", "deep research X and save it to the vault", "durable deep research on X", "research X and persist the findings". NOT for a throwaway answer (use native /deep-research) and NOT for building a goal prompt (that is goal-prompt).
---

# orion-deep-research

A durable, quality-gated fork of the native `/deep-research`. The native command is
**compiled into the Claude Code binary** (unforkable in place) and its Workflow sandbox
**cannot write files**, so its report only ever lives in the transcript. This skill owns the
editable copy: the research core is `deep-research.workflow.js` (a Workflow script), and this
wrapper adds the value the sandbox cannot: **honest verification**, a **judge-gate**,
and **durable, disclaimed persistence** to your research vault.

See `SPEC.md` for the behavior contract and `lib/*.mjs` (+ `npm test`, 50 cases) for the
tested pure logic the workflow inlines.

## When to use / not use
- USE for research whose findings must survive `/compact` and be re-findable: a durable dated
  synthesis in your research vault (e.g. `<RESEARCH_VAULT>/research/`).
- Native `/deep-research` is fine for a throwaway in-chat answer. `goal-prompt` BUILDS a
  research prompt; it does not run one. This skill RUNS one and persists it.

## Procedure

### 0. Scope-check (before invoking)
If the question is underspecified (e.g. "what car to buy" with no budget/use-case/region), ask
2-3 clarifying questions and fold the answers into a single refined question. Autonomous callers
(`/goal`, chain-launcher) pass an already-refined question and skip this.

### 1. Run the workflow
```
Workflow({ scriptPath: "<SKILL_DIR>/deep-research.workflow.js",
           args: "<refined question>" })
```
It runs in the background (typically several minutes). It RETURNS a structured object; it writes
nothing. On completion you receive:
`{ question, complexity, summary, findings[] (with confidence + [n] sources), tier2[], refuted[],
   sources[] (numbered registry), verification{ verdict, counts, inconclusive, incomplete,
   failures[] }, stats{ reflectFired, sourcesFetched, tier, budget, ... } }`

### 2. Recovery gate (before you trust or persist anything)
Read `verification` FIRST. It is honest by construction: an abstained/rate-limited claim is
`unverified`, never `refuted`.
- If `verification.inconclusive === true` OR `verification.failures` is non-empty: the run hit
  infra trouble (rate-limit, dead search, fetch fails). Do NOT transcribe "inconclusive" into a
  deliverable. Recover, fastest first:
  1. Reclassify the saved output: `python3 <SKILL_DIR>/scripts/abstention_report.py <output.json>`
     (splits genuinely-refuted from recoverable-unverified).
  2. **Resume, don't re-run:** `Workflow({ scriptPath, resumeFromRunId: "<runId>", args: "<same question>" })`
     re-runs only the abstained calls (you MUST re-pass `args`). For an OSS/library subject,
     prefer rate-limit-independent primary channels for the tail (`gh api`, Context7).
     - **VERIFY THE LIMIT HAS RESET FIRST.** A resume fired while the same rate/session/credit
       limit is still active re-runs the failed calls into the SAME wall and returns a DEGRADED
       result (fewer or zero claims). Never overwrite the good prior run with it: compare the two
       outputs and KEEP THE ONE WITH MORE CONFIRMED CLAIMS. A degraded null must never clobber a
       good partial (a limit-killed run may have finished; the saved run-1 output
       on disk is the recoverable artifact).
     - If the limit will not reset soon and the prior run already has TIER 1 claims, SKIP the
       resume: synthesize + persist from the salvaged TIER 1 claims in the main loop (mark the
       artifact PARTIAL, TIER 2 unverified) rather than chasing a full run you cannot complete.
- Only proceed to persist once the run is either clean or honestly re-graded.

### 3. Judge-gate (protects the durable corpus)
Spawn ONE independent judge (a fresh `Agent`, NOT the run) to score the report against its own
sub-questions, so a weak run is not filed as an authoritative-looking synthesis:
> "Score this research report. For the question and each central sub-question: is it actually
>  answered by a TIER 1 finding? Is every finding quote/source-backed? Are claimed consensuses
>  multi-source? Return {pass:boolean, uncoveredSubQuestions:[], unattributedFindings:[], reasons}."
Advisory + severity-graded, never a fail-open silent block.
- `pass && !inconclusive` -> persist as a normal vault synthesis (step 4, canonical name).
- else -> persist but clearly QUARANTINED: filename `DRAFT-INCONCLUSIVE-<date>-<slug>.md`, a
  `status: draft-inconclusive` header, and the judge reasons + open questions up top. Do NOT let
  it read as a clean finding.

### 4. Persist the durable artifact (the durability contract)
Render the returned object to markdown and Write it to
`<RESEARCH_VAULT>/research/<YYYY-MM-DD>-<slug>.md`
(`<slug>` = kebab-case of the question, ~4-7 words; today's date from the environment).
Hygiene (from security review):
- If the target filename already exists (same-day re-run/slug collision), do NOT overwrite -
  bump with a short suffix (`-2`, or the short runId).
- Before writing, strip token-like query params (`token=`, `sig=`, `key=`, `apikey=`) from any
  persisted source URL; the vault's no-secrets rule is otherwise asserted, not enforced.
Use this house header (a recommended durable-research convention):

```markdown
# <Title>

**Date:** <YYYY-MM-DD>
**Type:** Deep-research synthesis (advisory, non-authoritative)
**Scope:** <one line: what the run covered / excluded>
**Method:** orion-deep-research harness (complexity=<x>, <angles> angles, <sourcesFetched> sources,
  <tier.tier1> TIER 1 / <tier.tier2> TIER 2 claims; reflect rounds run=<reflectRoundsRun>). Run
  id(s): <runId(s)>.

> Confidence: **[high]** primary-source-confirmed · **[medium]** one lens flagged a correction.

## Executive Summary
<the returned summary>

## Findings
<per finding: the claim, confidence tag inline, and its numbered [n] citations>

## TIER 2 (extracted, UNVERIFIED - single-source, treat as leads not facts)
<the tier2 items, clearly labelled unverified>

## Verification Provenance
- Verdict: <verification.verdict>
- Counts: <verification.counts> (confirmed / refuted / unverified)
- Incomplete: <verification.incomplete> · Inconclusive: <verification.inconclusive>
- Infra failures this run: <verification.failures, or "none">
- Citation existence checks / notes: <any arXiv-id or primary-source spot-check notes>

## Refuted (for transparency)
<refuted[] items>

## Sources
<numbered registry: [n] url>

---
*Advisory and non-authoritative (per your repo conventions). Evidence capture, not doctrine;
where it touches a system you operate, verify live before acting.*
```
Vault rules: markdown/JSON only, no secrets. Avoid long
dashes in the artifact (keeps it publish-safe if ever syndicated).

### 5. Operator commit gate (do NOT auto-commit)
Writing the file is reversible and yours to do. Committing/pushing the shared vault repo is the
irreversible gate: it is the operator's. After writing, show
`git -C <RESEARCH_VAULT> status --short` plus a one-line diff stat,
and OFFER to commit/PR. Do not commit or push without explicit approval (shared-state / Rule of
Two). No direct push to the default branch.

## Maintenance
- The workflow inlines the tested `lib/*.mjs` logic (the sandbox cannot import). After changing
  any `lib/*.mjs`, re-copy the function into `deep-research.workflow.js` and run `npm test`
  (verify + budget + tiers + the workflow-sim integration test must stay green).
- Keep the research spine a faithful superset of native so native updates can be re-synced; every
  divergence from native is commented in the workflow header. The bundled recovery tool
  (`scripts/abstention_report.py`) is the tested spec for the abstention semantics and the
  fallback for runs of the still-unforkable native command.
