---
name: orion-deep-research
description: Use when a multi-source, fact-checked research report must persist in a research vault with explicit uncertainty and verification provenance. The bundled executable requires a compatible Claude Workflow executor; see prerequisites and the author-attested origin record before use or redistribution.
---

# orion-deep-research

This package contains a research workflow and instructions for judging and
persisting its report. Its portable principles are honest abstention accounting,
bounded follow-up research, explicit TIER 1/TIER 2 claims and evidence-backed
persistence. Those principles can guide research in other harnesses; they do not
make the bundled executable portable to those harnesses.

See `SPEC.md` for the behavior contract and `lib/*.mjs` (`npm test`) for the pure
logic checks. Dan Mercede attests that this is his own workflow, independently
built with Claude's assistance. See the [origin record and its evidence limits](PROVENANCE.md).
Preserve that record and `LICENSE.orion` in standalone copies. Publication still
requires final qualification and approval; local tests cannot establish rights
or native compatibility.

## Execution prerequisites and limits

- The bundled `deep-research.workflow.js` requires the **Claude Workflow tool**
  with `scriptPath`/`args`, its workflow globals (`phase`, `agent`, `log`) and the
  search/source-reading capabilities requested by its agents. A plain Node.js
  process, a skill installer, or another harness's shell cannot supply that tool.
  Confirm the executor's available interface before invocation; support for this
  script and `resumeFromRunId` has not been qualified by the offline tests here.
- The wrapper needs an independent judge-agent facility, file writes to a
  user-selected `<RESEARCH_VAULT>`, and Python 3 for the bundled recovery script.
  Replace `<SKILL_DIR>` with this skill's installed absolute directory. Use only
  research/provider access and output writes already authorized for the task.
- If the Workflow executor is absent or its compatibility is unknown, stop before
  invocation and report the missing prerequisite. There is no bundled executable
  fallback. Separately authorized manual research may use the principles above,
  but must be labeled manual research, without claiming a completed Workflow run.
- Node.js with its built-in test runner executes the local pure-logic, drift and
  simulated orchestration tests. These tests do not fetch live sources, invoke
  the native executor or qualify native support. `package.json` is a private test
  helper at its own version, separate from the collection release version.

## When to use / not use
- USE for research whose findings must survive `/compact` and be re-findable: a durable dated
  synthesis in your research vault (e.g. `<RESEARCH_VAULT>/research/`).
- Native `/deep-research` is fine for a throwaway in-chat answer. `goal-prompt` BUILDS a
  research prompt; it does not run one. This skill RUNS one and persists it.

## Procedure

### 0. Scope-check (before invoking)
If the question is underspecified (e.g. "what car to buy" with no budget/use-case/region), ask
2-3 clarifying questions and fold the answers into a single refined question. Autonomous callers
(for example, a user-authorized goal runner) pass an already-refined question and skip this.

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
Only use the resume form below if the executor explicitly supports it; otherwise
retain the partial output and report recovery unavailable. Read `verification` FIRST. It is honest by construction: an abstained/rate-limited claim is
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
- Preserve the documented research behavior. The workflow header records historical
  native-lineage claims, not proof of native parity or permission to copy updates.
  Resolve provenance before any upstream resynchronization. The bundled recovery tool
  (`scripts/abstention_report.py`) is the tested spec for the abstention semantics and the
  fallback for runs of the still-unforkable native command.
