---
name: ship
disable-model-invocation: true
description: Use when a completed code change is ready to take from green tests through a PR to verified-live, and you need a disciplined end-to-end finish that does not claim done until runtime is independently confirmed.
---

# Ship

## Overview

Take a finished change from passing tests to verified-live without claiming success on faith.

**Core directive:** Run tests (RED/GREEN), open a PR, run adversarial self-review for fail-open/auditability gaps, then live-verify before reporting done.

**Violating the letter of the gates is violating the spirit of the gates.** Cheap proxies — a green deploy, green CI, a stale LGTM, "I'm confident" — are necessary-at-most, never sufficient.

## When to Use

- A code change is implemented and you believe it is finished.
- You are about to say "done", "fixed", "deployed", or "shipped".

Do NOT use for: brainstorming, mid-implementation work, or anything with no diff to ship.

## Steps

1. **Run tests (RED/GREEN).** Confirm the relevant test fails RED before the fix and passes GREEN after. Run the repo's declared test + lint commands (repo-local `CLAUDE.md` / `AGENTS.md` / CI contract) — **a green CI run is not a substitute for re-running the declared tests yourself.** **No declared test suite RAISES rigor — it is never a license to skip Gate 1.** On any security/authz path, hand-roll a failing default-deny check (RED) and make it pass (GREEN) before claiming done. State exactly what you ran.
2. **Open a PR.** Re-detect the base branch from repo PR convention even if you think you know it; fall back to `git remote show origin` default. Never assume `main`. **A prior or verbal LGTM is permission, not evidence** — re-request approval on the *post-edit* diff; never downgrade re-review to an opt-out "flag me if…". Show a diff summary before committing. Never force-push.
3. **Adversarial self-review for fail-open / auditability gaps.** Attack your own change: Where does it fail OPEN instead of fail-closed? Which mutation or decision goes unreceipted / unaudited? What state is asserted but never verified? **If you find a fail-open or bypass path, first challenge whether it should exist at all — prefer ELIMINATING it over making it "safe".** Report findings severity-graded — **BLOCKING** / **WARNING** / **INFO**. Fix BLOCKING before proceeding. This pass is mandatory; it is not optional "ceremony" you skip because tests are green.
4. **Live-verify before reporting done.** Independently confirm runtime via the repo/host's declared verification path (container status, systemd status, health endpoint, env render, connectivity). **A green deploy/CI is not runtime proof.** If independent verification is impossible, say "unverifiable / not done" explicitly — do NOT claim success, and do NOT substitute a forward-promise ("will verify") for the claim.

## Quick Reference

| Phase | Gate |
|-------|------|
| Tests | RED before, GREEN after; lint clean; no-suite ⇒ hand-roll, not skip |
| PR | Re-detected base branch, fresh approval on post-edit diff, no force-push |
| Self-review | Fail-open eliminated or graded; no unaddressed BLOCKING |
| Live-verify | Runtime confirmed by declared path, or "unverifiable / not done" stated |

## Rationalizations — and why they fail

Captured verbatim from baseline (RED) testing of agents *without* this skill:

| Rationalization | Reality |
|-----------------|---------|
| "I'm confident the fix is correct." | Confidence is not evidence. Gate 4. |
| "`./deploy.sh` exited 0, so it works." | A clean deploy proves the script ran, not that the handler serves traffic or fail-closes. Gate 4. |
| "CI was green, round it up to done." | CI green is necessary-not-sufficient; only an independent runtime check closes Gate 4. |
| "If green: ship." / "tests pass so it works." | Green tests never authorize shipping a fail-open-capable surface. Gates 3+4 still mandatory. |
| "I'm not inventing a verification ritual / ceremony." | Gates 3 and 4 are not ceremony. Declining them = shipping on faith. |
| "Senior already said LGTM, ship it." | A stale/verbal LGTM is permission, not approval of the post-edit diff. Gate 2. |
| "Flag me if any of the delta wants re-review." | Re-review is opt-IN, not opt-out. Gate 2. |
| "No test suite here, so move fast." | No suite RAISES rigor; hand-roll RED→GREEN, especially on authz paths. Gate 1. |
| "I'll make the bypass safe." | First ask whether the bypass should exist at all; prefer elimination. Gate 3. |

## Red Flags — STOP, you are about to ship on faith

- "Confident" / "probably still pass" → run the tests.
- "It deployed / CI green, so it works" → live-verify runtime, not the exit code.
- "No tests configured here" → hand-roll the check; do not skip.
- "LGTM from earlier" → re-approve the current diff.
- "Fails safe enough" → eliminate the fail-open path or grade it BLOCKING.
- "Reporting done" with no independent runtime check → it is not done.

## Boundary

This `ship` is a **finish-discipline checklist** — it governs the *quality gates* between green and done. It is **not** a deploy-mechanics skill and is **not authoritative for deploy mechanics**. Deploy decisions, targets, and tooling defer to your project's own deploy doctrine (deploy targets, secrets manager, worktree/branch discipline) per your repo's `AGENTS.md` / `CLAUDE.md`. This skill only governs *whether you may call it done* — route the *how/where* of deploy to your project's canonical deploy process.
