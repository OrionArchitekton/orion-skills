---
name: investigate
description: |
  Systematic debugging with root cause investigation. Four phases: investigate,
  analyze, hypothesize, implement. Iron Law: no fixes without root cause.
  Use when asked to "debug this", "fix this bug", "why is this broken",
  "investigate this error", or "root cause analysis".
  Proactively invoke this skill (do NOT debug directly) when the user reports
  errors, 500 errors, stack traces, unexpected behavior, "it was working
  yesterday", or is troubleshooting why something stopped working.
---
## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Fixing symptoms creates whack-a-mole debugging. Every fix that doesn't address root cause makes the next bug harder to find. Find the root cause, then fix it.

---



## Phase 1: Root Cause Investigation

Gather context before forming any hypothesis.

1. **Collect symptoms:** Read the error messages, stack traces, and reproduction steps. If the user hasn't provided enough context, ask ONE question at a time via AskUserQuestion.

2. **Read the code:** Trace the code path from the symptom back to potential causes. Use Grep to find all references, Read to understand the logic.

3. **Check recent changes:**
   ```bash
   git log --oneline -20 -- <affected-files>
   ```
   Was this working before? What changed? A regression means the root cause is in the diff.

4. **Build a red-capable reproduction: this is the GATE, not a soft step.** Before forming ANY hypothesis (Phase 3), you must be able to name ONE command (a failing test, curl/HTTP script, CLI invocation, replayed trace, or throwaway harness) that you have **already run at least once** (paste the invocation + its output) and that is:
   - **Red-capable**: drives the actual bug code path and asserts the user's *exact* symptom, so it goes red on this bug and green once fixed (not merely "runs without erroring").
   - **Deterministic**: same verdict every run. For non-deterministic bugs the goal is not a clean repro but a **high reproduction rate**: loop the trigger 100 times, parallelise, add stress/sleeps/narrow timing (a 50%-flake bug is debuggable, a 1% one is not, so keep raising the rate until it is).
   - **Fast**: seconds, not minutes (cache setup, skip unrelated init, narrow scope).
   - **Agent-runnable**: runnable unattended; only put a human in the loop via the structured HITL script `${CLAUDE_SKILL_DIR}/scripts/hitl-loop.template.sh`.

   If you catch yourself reading code to build a theory before this command exists, **STOP: jumping straight to a hypothesis is the exact failure this skill prevents. No red-capable command, no Phase 3.** If you genuinely cannot build one, say so explicitly, list what you tried, and ask the user for repro access / a captured artifact (HAR, log dump, core dump, timestamped recording) / permission to add temporary instrumentation; do not proceed to hypothesise without a loop. (Adapted from mattpocock/skills diagnosing-bugs.)

5. **Check investigation history:** Search prior learnings for investigations on the same files. Recurring bugs in the same area are an architectural smell. If prior investigations exist, note patterns and check if the root cause was structural.

## Scope Lock

After forming your root cause hypothesis, identify the narrowest directory containing the affected files and stay within it for the rest of the investigation, to prevent scope creep. If the bug spans the entire repo or the scope is genuinely unclear, skip the lock and note why.

---

## Phase 2: Pattern Analysis

Check if this bug matches a known pattern:

| Pattern | Signature | Where to look |
|---------|-----------|---------------|
| Race condition | Intermittent, timing-dependent | Concurrent access to shared state |
| Nil/null propagation | NoMethodError, TypeError | Missing guards on optional values |
| State corruption | Inconsistent data, partial updates | Transactions, callbacks, hooks |
| Integration failure | Timeout, unexpected response | External API calls, service boundaries |
| Configuration drift | Works locally, fails in staging/prod | Env vars, feature flags, DB state |
| Stale cache | Shows old data, fixes on cache clear | Redis, CDN, browser cache, Turbo |

Also check:
- `TODOS.md` for related known issues
- `git log` for prior fixes in the same area: **recurring bugs in the same files are an architectural smell**, not a coincidence

**External pattern search:** If the bug doesn't match a known pattern above, WebSearch for:
- "{framework} {generic error type}". **Sanitize first:** strip hostnames, IPs, file paths, SQL, customer data; search the error category, not the raw message.
- "{library} {component} known issues"

If WebSearch is unavailable, skip this search and proceed with hypothesis testing. If a documented solution or known dependency bug surfaces, present it as a candidate hypothesis in Phase 3.

---

## Phase 3: Hypothesis Testing

Before writing ANY fix, verify your hypothesis.

1. **Confirm the hypothesis:** Add a temporary log statement, assertion, or debug output at the suspected root cause. Run the reproduction. Does the evidence match? Prefer one debugger breakpoint / REPL inspection over ten logs; never "log everything and grep." **Tag every temporary probe with a unique prefix** (e.g. `[DEBUG-a4f2]`) so cleanup is a single `grep`: untagged logs survive, tagged logs die.

2. **If the hypothesis is wrong:** Before forming the next hypothesis, consider searching for the error. **Sanitize first**: strip hostnames, IPs, file paths, SQL fragments, customer identifiers, and any internal/proprietary data from the error message. Search only the generic error type and framework context: "{component} {sanitized error type} {framework version}". If the error message is too specific to sanitize safely, skip the search. If WebSearch is unavailable, skip and proceed. Then return to Phase 1. Gather more evidence. Do not guess.

3. **3-strike rule:** If 3 hypotheses fail, **STOP**. Use AskUserQuestion:
   ```
   3 hypotheses tested, none match. This may be an architectural issue
   rather than a simple bug.

   A) Continue investigating (I have a new hypothesis: [describe])
   B) Escalate for human review (this needs someone who knows the system)
   C) Add logging and wait (instrument the area and catch it next time)
   ```

**Red flags**: if you see any of these, slow down:
- "Quick fix for now": there is no "for now." Fix it right or escalate.
- Proposing a fix before tracing data flow: you're guessing.
- Each fix reveals a new problem elsewhere: wrong layer, not wrong code.

---

## Phase 4: Implementation

Once root cause is confirmed:

1. **Fix the root cause, not the symptom.** The smallest change that eliminates the actual problem.

2. **Minimal diff:** Fewest files touched, fewest lines changed. Resist the urge to refactor adjacent code.

3. **Write a regression test** that:
   - **Fails** without the fix (proves the test is meaningful)
   - **Passes** with the fix (proves the fix works)

4. **Run the full test suite.** Paste the output. No regressions allowed.

5. **If the fix touches >5 files:** Use AskUserQuestion to flag the blast radius:
   ```
   This fix touches N files. That's a large blast radius for a bug fix.
   A) Proceed (the root cause genuinely spans these files)
   B) Split (fix the critical path now, defer the rest)
   C) Rethink (maybe there's a more targeted approach)
   ```

---

## Phase 5: Verification & Report

**Fresh verification:** Reproduce the original bug scenario and confirm it's fixed. This is not optional.

**Instrumentation cleanup:** Remove all temporary probes (`grep` the `[DEBUG-...]` prefix and confirm none survive) and delete any throwaway repro harness (or move it to a clearly-marked debug location).

Run the test suite and paste the output.

Output a structured debug report:
```
DEBUG REPORT
════════════════════════════════════════
Symptom:         [what the user observed]
Root cause:      [what was actually wrong]
Fix:             [what was changed, with file:line references]
Evidence:        [test output, reproduction attempt showing fix works]
Regression test: [file:line of the new test]
Related:         [TODOS.md items, prior bugs in same area, architectural notes]
Status:          DONE | DONE_WITH_CONCERNS | BLOCKED
════════════════════════════════════════
```

Log the investigation as a durable learning for future sessions using the `learn-capture` skill: capture the root cause summary and the affected files so future investigations on the same area can find it.

## Important Rules

- **3+ failed fix attempts → STOP and question the architecture.** Wrong architecture, not failed hypothesis.
- **Never apply a fix you cannot verify.** If you can't reproduce and confirm, don't ship it.
- **Never say "this should fix it."** Verify and prove it. Run the tests.
- **If fix touches >5 files → AskUserQuestion** about blast radius before proceeding.
- **Completion status:**
  - DONE: root cause found, fix applied, regression test written, all tests pass
  - DONE_WITH_CONCERNS: fixed but cannot fully verify (e.g., intermittent bug, requires staging)
  - BLOCKED: root cause unclear after investigation, escalated

## Boundary

This is a debugging-discipline skill, not a tool or environment wrapper. How you capture
a stack trace, which test runner or REPL you use, and how your repo's CI reports results
are your own project's conventions. The invariant is the shape: no hypothesis before a
red-capable reproduction exists, no fix without a regression test that fails before and
passes after, and escalate after three failed hypotheses rather than guessing a fourth.

## References (progressive disclosure)

To keep this skill lean, depth was moved to `references/` (load only when needed):

- `references/preamble.md`: retired; was a runtime preamble tied to a toolchain no longer present, not required for this skill's core flow.
