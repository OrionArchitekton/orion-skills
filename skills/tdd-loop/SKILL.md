---
name: tdd-loop
description: Use when implementing a feature or bugfix from a spec that should land as a hardened, CI-green PR, or when asked for an "autonomous implement loop", "self-correcting TDD", or to "build this end-to-end and open a PR". Use whenever code must not ship with failing tests or unreviewed security-sensitive changes. Triggers include /tdd-loop, "implement this feature", "build this and open a PR".
---

# Self-Correcting TDD Implementation Loop

## Overview

Given a feature/bugfix spec, drive it to a hardened, CI-green PR through a closed
test-driven development (TDD) loop: **RECON → PLAN → per-slice RED → GREEN → REFACTOR → SLICE-LOOP → mandatory
adversarial + security self-review (BLOCKING = hard gate) → VERIFIED PR → CAPTURE** —
looping until BOTH the full test suite AND the security checklist are green, each
proven by a captured artifact, never by self-report.

The skill's contribution is the **enforcer + iteration controller**. It is
self-contained — it composes nothing you must install. (Optional: if you run a skill
ecosystem with dedicated TDD / planning / review skills, slot them into the matching
stages below; the gates are identical either way.)

## Iron Law

**No slice advances on self-report. Every green verdict cites an externally-verifiable
ARTIFACT — a captured exit code, a report file, or a `git` result.**

A skill body is a prompt, not an enforcement boundary (no hook ships with this skill).
A self-policed gate can be rationalized past, so bind every gate to an artifact you can
re-read. "I checked and it's fine" is not a green verdict.

**Violating the letter of the gates is violating the spirit of the gates.** A green
deploy, green CI, a stale LGTM, "I'm confident" — necessary at most, never sufficient.

## When to use

- Implementing a feature/bugfix from a spec that should land as a CI-green PR.
- Triggers: `/tdd-loop`, "implement this", "build this feature and open a PR",
  "self-correcting TDD", "autonomous implement loop".

**When NOT to use:**
- Pure research/audit with no code.
- An undecided idea ("should I build X?") → brainstorm/design first.
- A one-line mechanical edit → just do it; the loop is overhead.

## Preconditions (refuse if unmet — recon first)

Run recon BEFORE any code. **Refuse to proceed if preconditions fail** — do not paper
over a missing spec, a dirty tree, or an unknown base branch.

- **recall:** search your prior sessions / notes for lessons in this area before
  substantive work (if your harness has session search or a memory store).
- **spec:** scenarios + acceptance criteria exist. New or contract-visible behavior
  needs them; if absent, write or locate the spec first.
- **clean worktree** from the repo's current default branch (not a shared canonical
  checkout you also build in).
- **declared checks known:** the repo's test / lint / build commands (repo-local
  `CLAUDE.md` / `AGENTS.md` / CI). If none are declared, state that explicitly — and
  let it RAISE rigor (hand-roll a check), never lower it.

## The loop (use your harness's canonical for each stage; do not reinvent)

0. **RECON** — recall prior lessons; investigate live state. Verify any
   root-cause/approach hypothesis against the actual code; **no single-hypothesis
   lock-in** (≥2 independent readings for any contested root cause before acting).
   Refuse if preconditions fail.
1. **PLAN** — vertical slices + the test seam(s), sequenced by dependency. Each slice
   is a tracer-bullet vertical slice (end-to-end through every layer it touches), NOT a
   horizontal layer.
2. **RED** — write ONE failing test for the next slice; run it; confirm it fails for
   the RIGHT reason. Distinguish a real RED from a FLAKE (re-run to confirm
   determinism). **Not all tests up front** — that horizontal slice is fake TDD.
3. **GREEN** — implement minimally until that one test passes; iterate edit→test.
4. **REFACTOR** — clean up while tests stay green.
5. **SLICE-LOOP** — repeat 2–4 one vertical slice at a time until the feature is
   complete. An unexpectedly-failing test routes BACK to root-cause investigation,
   never forward to a speculative patch.
6. **ADVERSARIAL + SECURITY SELF-REVIEW (mandatory)** — see *Enforcer gates* +
   *Security checklist*. Feed the computed diff to the reviewer roles; **BLOCKING
   findings are HARD GATES**: fix, re-run the full suite, re-review.
7. **VERIFIED PR** — preflight (detect base branch, secret scan) → finish the branch →
   commit (passes the secret gate; never echo secrets; never force-push) → open the PR
   with test evidence + review summary → independent runtime verification (a green
   deploy/CI is not runtime proof).
8. **CAPTURE** — record the lessons so the next pass is cheaper.

## Enforcer gates (hard-stop; each binds to an ARTIFACT)

The loop refuses to advance until the named artifact proves green. **BLOCKING-as-hard-gate:
the PR does not open while any BLOCKING finding is open OR the suite is red.**

- **Precondition gate** — recon done vs the spec; **refuse if preconditions fail**.
- **RED gate** — the test is observed FAILING for the right reason, re-run to rule out a
  FLAKE (capture both runs). "Saw red once" is not enough.
- **Slice gate** — ONE RED→GREEN per vertical slice; an unexpected failure → root-cause
  investigation, not a forward patch.
- **Review-ran gate** — COMPUTE the diff yourself (`git diff <base>...HEAD`), assert it
  is NON-EMPTY and matches the slices touched, and feed THAT diff to the reviewers. An
  empty/clean reviewer result on a non-empty diff is a GATE FAILURE (re-run) — "the
  engine actually ran against the actual diff" is a precondition of any green verdict.
- **Security gate (BLOCKING-as-hard-gate)** — run the diff through the security
  checklist below; any BLOCKING finding blocks the PR. Loop-until clean.
- **Secret gate** — independently re-run your secret scanner on the staged set and
  assert it produced a CLEAN report (report file exists, exit 0). A scanner that errors,
  times out, or runs outside the repo can fail OPEN, so a non-blocking advisory counts
  as NOT green here. Escape a false positive via the scanner's allow mechanism, **never**
  by bypassing the commit hook past a real finding.
- **Completion gate** — run the FULL test suite as the LAST action before the PR,
  capture its exit code to a file, and quote it. A non-zero, stale, or absent capture =
  not green. No "done" without independent runtime verification.

**Iteration controller:** loop-until( full-suite green AND security-checklist green ),
both proven by captured artifacts. Only then open the PR.

See `references/ENFORCER.md` for the runnable mechanics of every gate.

## Security checklist (stage 6 must check each named bug class)

- **fail-open** — a gate/guard that defaults to ALLOW on error, exception, or timeout.
- **path traversal** — `../` escapes, unsanitized path joins, symlink escape,
  absolute-path injection.
- **injection** — shell / SQL / template; unescaped interpolation; unquoted expansion.
- **secret-spill** — including the **secret-to-stdout prohibition**: never echo
  plaintext secrets; redirect secret-bearing commands and check the exit status; read a
  single value without printing it.
- **auditability** — mutation without a receipt/log; non-idempotent operations; no
  rollback path.
- **ID collisions** — non-unique keys / slugs / filenames; races on shared identifiers.

## Reviewer engines (roles, not products)

Dispatch the computed diff to (at least) two roles:

- a code-level **SECURITY** reviewer that encodes the six classes above, and
- an **ADVERSARIAL / CORRECTNESS** reviewer (logic, edge cases, state, error
  propagation, abuse / composition / cascade failures).

Use whatever diff-fed reviewer agents your harness provides. If you have none, run each
role's checklist against the diff YOURSELF in a dedicated pass — the gate is that a
reviewer (human, agent, or your own structured pass) actually saw the *computed* diff.
A PR-scoped or "looks simple, skipping" review is NOT the pre-PR security engine: run
security review on every diff, then any broader post-PR review as a complement.

## Substrate (harness-agnostic)

Drive the per-slice and per-review fan-out with whatever your harness gives you —
independent subagents, a deterministic workflow runner if you have one, or inline
sequential work. Never assume a particular orchestrator is available; an un-orchestrated
run MUST still complete end-to-end inline. The gates above are substrate-independent —
they bind to artifacts either way.

## Rails (baked in)

- **Mandatory recon + refuse-if-preconditions-fail** (above).
- **No single-hypothesis lock-in** — verify any root cause vs live state; ≥2 readings
  for a contested cause before acting.
- **Full test suite + adversarial review before any commit/PR; BLOCKING = hard gate.**
- **Investigate the codebase directly** — do not ask for context you can discover
  yourself.
- **Never echo secrets to stdout** — redirect secret-bearing commands + check the exit
  status.
- **Concise output; write large artifacts to files incrementally** — do not dump large
  blobs into the transcript.
- **For the CODE the loop drives:** a fresh worktree/branch off the repo's *detected*
  default branch (never a shared canonical checkout); **never force-push**; base branch
  detected from repo PR convention or `git remote show origin` — **never assumed `main`**.
- Severity-grade every finding **BLOCKING / WARNING / INFO**.

## Red flags — STOP (you are rationalizing past a gate)

| Thought | Reality |
|---|---|
| "The spec is obvious — I'll just implement it" | Refuse-if-preconditions-fail. New/contract-visible behavior carries a spec; "obvious" is how unscoped behavior ships. Write or locate it first. |
| "I'll write all the tests first, then implement" | Horizontal slice = fake TDD. ONE RED→GREEN per slice. |
| "The test is flaky — I'll add a retry until it goes green" | A retry masks the bug. Re-run to CONFIRM determinism, then root-cause; never paper a real failure as a flake. |
| "This surprise failure is unrelated / pre-existing — I'll patch around it" | Backflow rule: an unexpected red routes to root-cause (≥2 hypotheses vs live state), never a forward speculative patch. |
| "The reviewer returned nothing, so it's clean" | Empty result on a non-empty diff = gate FAILURE. Did the engine see the diff? |
| "Security review is overkill for this small change" | The 6 named bug classes are a fixed checklist, not optional. |
| "The post-push CI/review pipeline will catch security — I'll skip it now" | That runs AFTER push; this is the pre-PR gate. Run security review on the computed diff BEFORE opening the PR. |
| "The secret scanner exited without blocking" | It can fail OPEN on scan error/timeout. Assert a CLEAN report was actually produced. |
| "Tests passed earlier, I'll call it done" | Run the FULL suite LAST; capture + quote the exit code. |
| "I'll force-push to tidy the branch" | Never force-push by default. |
| "I'm confident it's correct" | Confidence is not an artifact. Cite the captured exit code / report / git result. |

## What it deliberately does NOT do

- Does NOT duplicate a post-push CI/review pipeline (that runs *after* push; this is the
  *pre-PR* gate — they complement).
- Does NOT add a secret-scan hook (your secret scanner already gates at commit time;
  assert its report rather than stacking a third layer).
- Does NOT claim done without independent runtime verification.

## Boundary

This skill governs the **pre-PR quality loop** — whether the loop's gates are green and
you may open the change as a PR. It is **not** a deploy-mechanics skill. Deploy targets,
secret manager, worktree/branch specifics, and CI wiring defer to your project's own
doctrine (your repo's `AGENTS.md` / `CLAUDE.md`). Route the *how/where* of deploy to
your project's canonical process; this skill only decides whether you may call it ready.

## References

- `references/ENFORCER.md` — base-branch detection, diff computation + non-empty
  assertion, the reviewer dispatch skeleton, the secret-scan fail-open → re-assert-clean
  gate, the suite-exit-code capture gate, and the backflow rule. Load when running the loop.
