---
name: author-workflow-fanout
description: "Use when authoring a Claude Code Workflow scriptPath / multi-agent fan-out script: deciding pipeline vs a parallel barrier, wiring per-agent() error handling, choosing schema vs longform output, persisting bulk results, or writing a budget/cap loop. Symptoms this skill exists for: one dead search or rate-limit crashing the whole fan-out because an agent() call had no .catch, a barrier stalling fast agents behind the slowest, a budget loop running to the 1000-agent cap because it was not guarded on budget.total, bulk output stuffed into return values instead of disk."
---

# Authoring Workflow Fan-Out Scripts

## Overview

A fan-out script spends real tokens across many subagents, and its failure
modes are silent: an un-caught reject kills the whole run, an unguarded loop
burns the agent cap, a barrier stalls every fast agent behind the slowest.
Author defensively: every `agent()` call handles its own failure into a ledger
plus abstention, the topology is a pipeline unless a barrier is genuinely
needed, and any budget loop is guarded so it cannot run unbounded. Run the
linter before you launch.

## When to use

- Writing or editing a `Workflow({scriptPath})` script, or any multi-`agent()`
  fan-out.
- NOT for deciding WHETHER to fan out (that is a parallel-dispatch decision),
  and NOT for reading the verdicts a fan-out returns (that is a verdict-triage
  discipline).

## Rules the linter enforces (run it before launch)

`python3 workflow_lint.py <script.js>` (exit 0 clean, 1 findings, 2 error).

| Rule | Why it matters |
|------|----------------|
| `no-catch` | Every `agent()` must carry `.catch` (or a wrapper that does). One rate-limit or dead-search reject otherwise rejects the whole `parallel`/`pipeline`; the failure must become a ledger entry plus abstention, not a crash |
| `budget-unguarded` | `while (budget.remaining() ...)` with no `budget.total` in the condition runs to the 1000-agent cap: with no target, `remaining()` is `Infinity`. Guard: `while (budget.total && budget.remaining() > N)` |
| `meta-missing` | A script with no `export const meta = {` is rejected at load |
| `unbounded-agent-hoard` | A schema-less (longform) `agent()` whose returns are accumulated (`pipeline`/`parallel`/`.push`/`+=`) with NO bound accumulator hoards unbounded bulk in the orchestrator's live context. Fix: pass a `schema` (small structured return), or route returns through a bounded accumulator (see Judgment section below) |

## Judgment the linter cannot check

- **Pipeline by default; barrier only for cross-item need.** `pipeline()` has
  no barrier, so a fast item is not stalled behind the slowest. Use
  `parallel()` between stages ONLY when a stage genuinely needs ALL prior
  results at once (dedup/merge, zero-count early-exit, "compare to the others").
- **schema vs longform.** Structured data (findings, verdicts) takes a
  `schema`. Human or prose output stays plain text; a schema mangles longform.
- **Persist bulk to disk.** Subagents write artifacts to files and return
  pointers or summaries; do not stuff large bodies into `agent()` return values. When you DO
  accumulate many returns, cap and dedupe them in-flight with a small bounded accumulator: budget
  a total byte cap plus a per-item byte cap, and keep an audit manifest of what was kept versus
  dropped so the cap is auditable, not silent. A minimal shape:
  ```js
  const ctx = new BoundContext({ budgetBytes: 60_000, itemCapBytes: 4_000 })
  const results = await pipeline(items, d => agent(d.prompt, { schema: SMALL }).catch(() => null))
  for (const r of results.filter(Boolean)) ctx.add(r.key, JSON.stringify(r))
  // ctx.retainedBytes stays bounded; ctx.manifest() is the audit tail.
  ```
  Build (or reuse) this as a small helper in your own scripts directory (the linter recognizes a
  `BoundContext` in scope as evidence of a bound accumulator); it does not need to be fancy, just
  bounded and auditable.
- **`.filter(Boolean)` before using results.** A failed thunk resolves to
  `null` in `parallel()`/`pipeline()` output; filter before you map.
- **No `Date.now()` / `Math.random()`** in the script body (they throw in the
  sandbox and break resume); vary by index, stamp timestamps after the run.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The agents almost never fail, .catch is noise" | One 429 or dead search rejects the entire parallel()/pipeline(); the run dies at 90% |
| "A barrier is cleaner than a pipeline" | Barrier latency is real: the slowest item blocks every fast one; use pipeline unless a stage needs all prior results |
| "The budget loop is fine, it'll stop eventually" | With no `budget.total`, `remaining()` is Infinity; it stops at the 1000-agent backstop, not where you meant |
| "I'll return the full text and parse it later" | Bulk in return values bloats orchestrator context; persist to disk, return a pointer |

## Red flags

- An `await agent(...)` with no `.catch` anywhere in its statement.
- `parallel()` whose result feeds a transform that feeds another `parallel()`
  (that is a pipeline wearing a barrier).
- A `while` on `budget.remaining()`/`spent()` with no `budget.total` guard.
- `Date.now()` / `Math.random()` / bare `new Date()` in the script body.
- Launching without running the linter.

## Related

Complements a "whether to fan out" parallel-dispatch decision and a
verdict-triage discipline (reading the results a fan-out returns). Note the
name "workflow" collides with unrelated durable-execution frameworks: this is
about the Claude Code Workflow tool's fan-out script, not those.

## Boundary

This is an authoring discipline plus a shipped linter, not a runtime. The
linter (`workflow_lint.py`, co-located here) is a heuristic smell-detector: it
flags an `agent()` call with no `.catch`, an unguarded `budget` loop, and a
missing `meta` block, by blanking string/comment bodies before it tracks paren
depth so a prompt's punctuation cannot fool it. Wire it into your own
pre-launch step. The harness that runs the fan-out, the failure-ledger format,
and where you persist bulk output are your repo's mechanics. The discipline is
invariant: every `agent()` handles its own failure, pipeline unless a barrier
is needed, guard every budget loop. Selftest the linter in your own suite
before trusting it.
