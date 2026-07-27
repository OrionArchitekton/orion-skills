---
name: reprobe-stale-premise
description: "Use when about to act on a claim you did not just verify, a handoff/pre-compact \"next task\"/\"still broken\", a teammate's diagnosis, \"tool X doesn't exist\", \"X is live/dead\", \"consume shipped tool Y\", a \"UNBUILT\" registry state, or whether remote/PR work landed. Especially on a shared multi-session box. Symptom: starting the implied work before re-probing the premise."
---

# reprobe-stale-premise

## Overview

**Any claim you did not just verify is a hypothesis, not a fact. Re-probe live ground truth before doing the work the claim implies.**

A handoff's "still failing", a teammate's "it's the null-handling at line 80", a scout's "tool X isn't on disk", a registry's "UNBUILT": each was true *when written* and may be false *now*. On a shared multi-session box, an owner or a timer may have shipped the fix, moved the file, or renamed the tool while you were away. Acting on the stale premise produces the expensive failures: "fixing" an already-fixed bug, building a duplicate of something that exists under another name, racing another session's landed work.

This is cheap insurance, not paranoia: **one live probe gates the implied work.** It is the opposite of re-litigating settled decisions: a *settled decision* you assert (absent is not contradicted); an *unverified premise about live state* you re-probe.

## When to use

Resuming a handoff/pre-compact pack; a "go fix X" naming a broken runtime; a "build X" where X may already exist; a "consume tool Y" plan; deciding whether a PR/commit landed; any inherited diagnosis. **When NOT:** a fact you established yourself this session; a settled design decision you have already made (that is a separate discipline: assert it, do not re-litigate it).

## Premise types and their re-probe

| Inherited claim | Re-probe BEFORE acting |
|---|---|
| Handoff/plan "still broken / rogue X / UNBUILT" | Re-run the live probe now (`systemctl status` + log pass/fail counts + the actual channel/route). Check whether the owner already shipped: **`git fetch origin` FIRST** (see "Did the work land?" below; `git log` against a stale local ref lies), then `git log -- <file>` in HEAD ancestry + `git diff HEAD` for drift. If it no longer reproduces, **report `ALREADY-FIXED (checked: <cmd>)`** and stop; do not invent a fix. If a parallel session **shipped-then-reverted** the arc, **honor the revert** (reconcile drifting docs, do not rebuild); a reverted state is not a fresh bug. |
| "Fix the 500 in X" (prior diagnosis) | Confirm the symptom **reproduces now**. A borrowed trace is a hypothesis: confirm root cause yourself; **no repro = no confirmed bug**. "null at line 80" is where it *surfaced*, not proof of *why*. |
| "Tool/system X is absent" (searched by name) | Search by **content/concept** (its distinctive mechanism terms) + known **aliases** + registry surfaces (a skills index, a home/ownership registry, whatever your project keeps). "Not found by name" is not "absent." Report `ABSENT (checked: <cmd>)`, never silent absence. |
| "Just CONSUME shipped tool Y" | Prove three things live: (1) Y's contract/config lists **MY** targets; (2) Y **returns data**, not just a pass/fail exit code; (3) Y is **reachable on my invocation path**. If any fails, report `STOP-INCOMPLETE-dup` naming **which check failed**, and surface the choice to the owner (extend Y to cover your targets vs. build a distinct tool); do not silently wrap a tool you cannot reach. |
| "Service X is live / dead" | Liveness drifts both ways; re-probe (see `prove-deploy-is-live` or your own runtime-liveness discipline). A "dead" verdict needs an on-vantage probe; a "live" one needs the real route. |

## Did the work land? (verify against fetched origin, never stale local)

The local working tree, the **unfetched** `origin/main` ref, and the session narrative can each independently produce a confident, wrong "it didn't land" / "it's done".

1. **`git fetch origin` FIRST**, then read `git show origin/<prodBranch>:<file>` or `git ls-tree -r --name-only origin/main`. `git show origin/main:file` reads your *local tracking ref*: stale without a fresh fetch.
2. Cross-check the authoritative source: `gh pr view <n> --json state,mergedAt`; `gh pr list --state merged`. **The remote is truth; the clone is a cache.**
3. **Before any follow-up push**, run `gh pr view <n> --json state,headRefOid` FIRST. A push to a **MERGED + deleted** branch silently **re-creates an orphan** (tell: a push you expected to fast-forward prints `* [new branch]`; `gh pr checks` may stay green on the stale association). Recover: branch off `origin/main`, `cherry-pick` your follow-up SHA, fresh PR; then `git push origin --delete <old-branch>`. Never force-push main.
4. A **squash-merged** branch head absent from main's ancestry is **benign**, not an orphan: confirm the fix is in `origin/main` + the PR is `MERGED` before deleting anything.
5. **Merged is not deployed** (ops/alerting/infra). Landing in `origin/main` is not running on the nodes; a separate deploy step (or a sibling that finished only PART of a multi-step post-merge) can orphan it. Verify each node's deployed `sha256sum` against `git show origin/main:<path>` (see `prove-deploy-is-live`), not PR-merged state.
6. **Applying onto a swept/snapshotted PR worktree:** before you apply, reconcile that live HEAD still `==` the snapshot sha AND (`git fetch` then) `git rev-list --left-right --count HEAD...origin/<branch>` `== 0  0` with a clean `git status`; a parallel session may have replayed/advanced the branch since the snapshot. If diverged, **DEFER** (leave threads open for the owning session); never force-push to win.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The handoff/teammate said it's still broken, just fix it" | That was a belief at write-time. The owner may have fixed it hours ago. Re-probe first. |
| "The diagnosis pinpoints line 80, I'll just patch it" | A borrowed trace is a hypothesis. No repro = no confirmed bug. A blind null-guard can turn a loud 500 into a silently-wrong result. |
| "I grepped the name and it's not here, so it doesn't exist" | It lives under an alias / different repo. Search by concept + aliases + registry before concluding absent. |
| "We'll just consume tool Y, it's already shipped" | Prove Y covers your targets, exposes data, and is reachable, or you will wrap a tool you can't reach (dup-by-construction). |
| "The local file shows the old value, so the work didn't land" | Stale checkout / unfetched ref. `git fetch` then check origin + `gh pr view`. |

## Red flags (you're acting on a stale premise)

- About to edit/build/fix based on a claim you have not re-probed **this session**.
- Concluding "X doesn't exist" from a single by-name search.
- About to `git push` a follow-up without `gh pr view <n> --json state` first.
- Reporting "it didn't land" from the local tree without a fresh `git fetch`.

## Related

This consolidates a family of recurring premise-drift failures seen across multi-session, multi-owner operation: a stale "still broken" handoff, a "tool doesn't exist" search that missed an alias, blind trust in an inherited root-cause line number, an unfetched-origin false negative, and a push-to-merged-branch orphan recreation. Counterpart: a settled design decision you have made is asserted once, not re-litigated; this skill is for an unverified claim about live state, which you re-probe instead. Escalation: when the implied action is itself a shared-state mutation (a commit/push into a shared checkout, closing a shared board item, a registry write), stand down and verify first: probe for a concurrent owner, claim the work atomically, and confirm the change landed before you consider it closed.

## Boundary

This is the premise-verification discipline, not a tool. The concrete mechanics, which
registry or handoff format you use, how your CI/CD reports deploy state, your branch and
PR conventions, belong to your own repo doctrine. The invariant is the shape: never act on
an inherited claim you have not re-probed this session, and never conclude absence from a
single by-name search.
