---
name: design-fail-closed-gate
description: 'Use when authoring any unattended or self-enforced gate: a PreToolUse/pre-commit/pre-push hook, secret/leak scanner, CI merge gate, auto-reaper/auto-mutator, dead-man''s-switch, or LLM self-review enforcer. Symptom: deciding allow/block from free-text, a scanner''s "didn''t complain", a self-assertion, or an exit code, with no human watching.'
---

# design-fail-closed-gate

## Overview

**An unattended or self-policed gate must fail CLOSED by construction: the safe verdict must be the structural default, not a behavior you hope holds.** A gate that silently fails open lets a destructive auto-mutator, a secret leak, or a never-fired dead-man's-switch through with nobody watching, the worst blast radius there is (a blind reaper that would have aborted a live pipeline and dozens of active sessions; a control plane left open for days).

The trap is always the same: the gate *looks* like it enforces, but its default-on-anything-unexpected is ALLOW. You make it fail closed by changing the **shape** of what it trusts, not by hardening a matcher.

## When to use
Authoring/reviewing: a hook (PreToolUse, pre-commit, pre-push), a CI/merge gate, an auto-reaper or auto-mutator, a dead-man's-switch / liveness probe that triggers action, or any LLM self-enforced "I checked it" quality gate. **When NOT:** an advisory/report-only surface a human reads (those must fail *open*, never block on advisory errors); also NOT a refactor/port/scoped-recreate that re-routes an EXISTING gate (that is re-asserting a dropped guard after a rewrite, a different task: re-assert the guard, do not author a new one).

## The rulebook

**1. Signal shape over prose.** Gate on a whole-string `^…$`-anchored token or a structured field with exact membership, **never an allowlist/keyword veto over free-form text**. If you are adding words to a veto to pass the latest input, you are on the treadmill: a list cannot be fail-closed against an open vocabulary. Prose classification caps at **SOFT / propose-for-confirm**; move the hard trust boundary to a human-set durable field or an external fact (`gh state == MERGED`, never "PR looks merged"). A `CLOSED`-unmerged PR is not done.

**2. Bind every green to an external artifact.** A self-policed "I checked, it's clean" is not an enforcement boundary; the same model can rationalize past it. Each pass must cite a re-readable artifact: a captured exit code (`echo $? > file`), a report file (`--report-path`), or a computed non-empty diff. Two specific traps: an **empty** reviewer result on a **non-empty** diff reads as "clean", so assert the engine ran against a computed non-empty diff; a scanner that **fails open** on error/timeout/non-repo cwd, so re-run and assert a CLEAN report was produced, do not trust "didn't block". "Clean report produced" means the report file **exists AND parses AND its findings array is empty**; an **absent or zero-byte** report is the fail-open trap, never a clean result.

**3. Parse external envelopes strictly.** Validate before reading values: require `status==success`, the key **present**, and the correct **type**, never `data.get("k") or []` (coerces missing/null/`status:error` into a falsely-healthy empty collection; a truthy non-list slips through too). Reject non-finite floats with `math.isfinite` (not just `isnan`: `inf`/`nan` pass naive bound checks). Check **each raw input** before `max`/`sum`/`abs`: aggregation masks a NaN operand (`max(0.0, nan)` -> `0.0`). A **count** input must be proven COMPLETE, not just non-empty: a paginated list (`gh --json commits`/REST) truncates silently (cap 100, no `totalCount`) -> undercount -> fail-OPEN; fetch via `gh api graphql` `totalCount` and fail closed when `totalCount > len(nodes)`.

**4. Exit-code semantics (know your harness, they invert).** *Claude Code hooks:* `exit 0` + `{"hookSpecificOutput":{"permissionDecision":"deny"}}` -> BLOCK; `exit 2` -> BLOCK; **any other non-zero (1, crash, no JSON) -> fail-OPEN, the tool runs.** So provision inputs best-effort (no fatal `set -e`), run an always-`exit 0` gate that owns the decision (any error in enforce -> deny), and translate ANY non-zero into `exit 2`. Do **not** `exec` the hook, a post-exec crash surfaces as exit 1 = fail-open; run it and check `$?`. *Git hooks (pre-commit/pre-push) invert this:* **ANY non-zero blocks**, so the structural default is already fail-closed; reach `exit 0` only after you have asserted the clean artifact (rule 2), and do not rely on `set -e` to do it for you. (The "both must be `exit 2`" check below is Claude-Code-specific; a git hook proves denial by any non-zero.)

**5. Exit-2-preserving traps.** Advisory hook -> `trap 'exit 0' EXIT`. **Blocking** hook -> `trap 'rc=$?; [ "$rc" -eq 2 ] && exit 2; exit 0' EXIT`. A blanket `exit 0` trap on a blocking gate converts its fail-closed `exit 2` into `exit 0` = silent hole.

**6. A severity flip does nothing alone.** Fail-closed only bites when something invokes the gate **in a blocking position** AND the gate runs **only where its dependencies exist** (e.g. a signature-verification tool that only exists on the CI/signing host, not the deploy target). Verify both the invocation point and the host capability before claiming the gate protects anything.

**7. Auto-mutators/reapers: verify selection, scope the universe.** Verify against the live target the gate exists to clear (dry-run **selection count** vs the actual leak), not its green exit. Evaluate liveness over the **whole** candidate universe: peer groups can mutually alibi a real leak (the holder must sit outside the orphan universe). Split read-only **detection** from stateful **remediation**, and run an adversarial REFUTE per finding before any irreversible bulk reclaim. Stamp an `actor` on every autonomous mutation (auditable + bulk-reversible). Gate never-consumed artifacts at the **writer**, not downstream GC. When a cap operates over a **lineage** (process tree, parent -> child, dependency graph), group by lineage and cap WHOLE subtrees, never flat-slice a flattened member list (slicing kills a parent while deferring children that reparent/detach and leak the exact growth the cap bounds).

## Prove it denies (mandatory)
A gate is unproven until you have watched it BLOCK. Feed it a **real-format** trigger (a `ghp_…`-shaped token, **not** the `AKIA…EXAMPLE` doc key, which gitleaks and most scanners **allowlist by default**, so it passes uselessly and proves nothing), a contradiction, and each malformed shape: **missing file, empty, null field, wrong type, `nan`, `+inf`, `-inf`, ambiguous/unexpected phrasing, a truncated/incomplete paginated count, a lineage cap that would split a subtree**. Every one must route to BLOCK. Add a regression test per shape. Diff original-vs-patched exit codes for a blocking hook (both must be `exit 2`).

## Rationalizations, STOP
| Excuse | Reality |
|--------|---------|
| "I'll just grep the bot's summary for 'approved'" | Prose veto cannot be fail-closed against an open vocabulary; reword once and it fails open. Gate on a structured token. |
| "The scanner didn't complain, so it's clean" | Scanners fail open on error/timeout/non-repo cwd. Assert a CLEAN report artifact was produced. |
| "I set severity to fail-closed" | A severity flip does nothing until something invokes the gate in a blocking position where its deps exist. |
| "`data.get('x') or []` handles the missing case" | It coerces missing/null/error into a falsely-healthy empty. Require status + presence + type first. |
| "The hook errored, so it blocked" | Exit 1 / crash = fail-OPEN in Claude Code. Only exit 2 / exit0+deny blocks. |
| "The reaper exited 0, it's working" | Verify the selection count vs the live leak; a 0-reap with green exit means it found nothing (peer mutual-alibi). |

## Red flags (your gate fails open)
- Deciding allow/block by matching words in free text.
- A green path that rests on a self-assertion, not a re-readable artifact.
- A blocking hook with `set -e` or a blanket `trap 'exit 0'`, or invoked via `exec`.
- You have not run the gate against a real-format secret / malformed input and watched it BLOCK.

## Related

Siblings in this collection: **prove-control-binds** (once you author the gate, prove it
actually FIRES against a canary, do not trust its green exit); **prove-deploy-is-live**
(prove the deploy that ships the gate is actually running it).

## Boundary

This is the gate-design discipline, not a framework. The concrete mechanics (which hook
system, which scanner, how you read a secret without printing it, your branch and CI
conventions) belong to your own repo doctrine. The invariant is the shape: make the safe
verdict the structural default, bind every green to a re-readable artifact, and prove the
gate denies before you call it armed.
