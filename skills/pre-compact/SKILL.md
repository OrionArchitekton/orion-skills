---
name: pre-compact
description: Use when about to run /compact, when the context window is filling up or near its limit, when wrapping up a long working session, or when handing in-progress work to a fresh/future instance so it can resume without re-deriving state. Triggers, "drop a handoff", "recap before compact", "save context", "context is at 90%".
---

# Pre-Compact Context Pack

## Overview

`/compact` discards most of the conversation. This skill captures the session into a **persistent, queryable context pack** so a fresh instance resumes with zero re-derivation, what shipped, what's in flight, what's next, and the operating rules to follow.

**Core principle: a pack is handoff _evidence_, not canon.** It is never auto-promoted into any repo, memory store, or vault. Durable decisions get promoted separately, by a human, after review.

**The compaction contract (what to keep vs. drop).** A pack is a *decision- and
open-thread-shaped* compaction, not a transcript. PRESERVE: architectural/locked
decisions + their rationale ("do NOT re-ask"), open threads / next actions, the
verified-vs-claimed split, and the operating rails. DROP: redundant tool output,
verbose command transcripts, intermediate exploration, and anything a fresh
instance can re-derive from disk in one command. When in doubt, keep the
*decision* and the *pointer* (file:line, SHA, command), not the raw output that
produced it. A pack heavy with tool dumps but light on decisions has inverted the
contract.

## Where packs live (engine-agnostic)

A pack is just a Markdown file in a **persistent directory**: NOT `/tmp` (wiped on
reboot). Pick a durable, agent-neutral location and keep it consistent, e.g.:

- `tasks/<task-id>/packs/`: one immutable timestamped file per checkpoint.
- Return the **explicit pack path** for the task being handed off. A directory or
  branch alone is not task identity: multiple tasks can share both.

Choose a stable, distinct task ID (for example `project-fix-import`) and record the
repository identity and worktree in the body. Reuse that ID only for the same
work. A replacement names the previous pack for that task; preserve the old bytes.
An optional index or task-local pointer is a convenience, never an authority.
No engine, hook or private runtime is required.

A legacy global `LATEST.md` may belong to another task. Use it only after verifying
that its task and repository match the current request and there is exactly one
eligible continuation. Missing identity, conflicting candidates, or an ambiguous
request means no pickup: request the exact task/path if current authority cannot
resolve it. Never infer ownership or acceptance from a timestamp or an idle chat.

## The Iron Rule: Verify, Don't Transcribe

Your own session narrative is the **least** trustworthy input. Before writing the pack, confirm claims against reality. A handoff that says "fixed and committed (a1b2c3d)" when no such commit exists is worse than no handoff, it sends the next instance building on phantom work.

Set `verified_state` honestly: `verified` (all key claims disk-confirmed) · `mixed` · `claimed-only`. In the body, split **✅ VERIFIED** from **⚠️ CLAIMED (unverified)**.

## Process

**1. Capture real runtime state** (don't rely on memory). For each repo/worktree touched this session:
```bash
git -C <repo> status -sb && git -C <repo> log --oneline -8
git worktree list
```
Note: current branch(es), uncommitted changes, any in-flight background jobs/agents, recently edited files.

**2. Verify claims.** For every "I did X": does the commit/branch/PR actually exist? Did tests actually run (real output)? Was a deploy independently verified? Downgrade `verified_state` for anything you can't confirm.

**3. Compose the body** using the template below. Record the task, repository,
accepted baseline plus acceptance evidence (or `unknown`), last verified outcome
plus proof, unfinished step, owner, literal next action, and remaining authority.
Acceptance and verification are different facts. Never fill in missing acceptance
from recency, tests or your narrative.

**4. Write the pack.** Prepare a body file with literal `Task: <task-id>` and
`Repository: <repository-identity>` lines. Set `TASK_ID`, `REPO_ID` and `PACK_BODY`
to those values and the body's absolute path. Choose a persistent `HANDOFF_ROOT`
outside temporary storage (the default below is one option). Confirm the body and
selection match the current task before running this shell recipe:

```bash
set -eu
umask 077
: "${TASK_ID:?set a stable task ID}" "${REPO_ID:?set repository identity}" "${PACK_BODY:?set body path}"
case "$TASK_ID" in ''|.|..|*[!a-zA-Z0-9._-]*) echo 'Invalid task ID' >&2; exit 1 ;; esac
grep -qxF -- "Task: $TASK_ID" "$PACK_BODY" || { echo 'Task/body mismatch' >&2; exit 1; }
grep -qxF -- "Repository: $REPO_ID" "$PACK_BODY" || { echo 'Repository/body mismatch' >&2; exit 1; }
HANDOFF_ROOT="${HANDOFF_ROOT:-$HOME/.local/state/agent-handoffs}"
PACKS="$HANDOFF_ROOT/tasks/$TASK_ID/packs"
mkdir -p -- "$PACKS"
PACK=$(mktemp "$PACKS/$(date -u +%Y-%m-%dT%H%M%SZ)-XXXXXX.md")
cat -- "$PACK_BODY" > "$PACK"
printf 'Read %s and resume only the matching task after verification.\n' "$PACK"
```

This recipe preserves prior checkpoints even when two writes share a timestamp.
Use a directory you control and the current workspace's ownership rules; the
recipe does not acquire a task lease or arbitrate concurrent owners.

**5. Print the explicit pickup line.** Give the exact path returned above. On
pickup, check the pack's task/repository against the current request, then compare
its accepted baseline, proof and next action with current project authority.
Re-probe only the referenced live state needed for continuation. A stale pack is
historical evidence: preserve it, use the newer accepted baseline, and do not
execute a gated action just because its old next-action line names one. An
unknown remaining authority stays unknown until resolved.

**6. Flag, do not perform, promotions.** If the session produced a durable decision/learning, list it under *Candidate promotions* for the human to later move into memory/canon. Never auto-write canon.

## Pack Body Template

```markdown
# HANDOFF: <title>
Task: <task-id>
Repository: <repository-identity>
**Date:** <YYYY-MM-DD> · **Host:** <box> · **Identity:** <git identity>
**Worktree / branch / HEAD:** <absolute directory / branch / SHA>
**Owner:** <actual owner or unknown; verify lease before resuming>
**Accepted baseline:** <artifact/plan + acceptance evidence, or unknown>
**Last verified outcome:** <observable result + proof and verification time>
**Unfinished step:** <one concrete step>
**Next action:** <literal authorized first move>
**Remaining authority:** <scope granted; additional decisions still needed, or unknown>
**Supersedes:** <prior pack for this same task, or none>
**Pointers:** memory file(s) · authoritative plan · proof packet · audit packs

## TL;DR: where things stand
<2-4 sentences: the mission and current position.>

## Verified state
- ✅ VERIFIED: <claim + how confirmed (SHA, test output, health check)>
- ⚠️ CLAIMED (unverified): <claim + why not confirmed + how to confirm>

## Shipped / merged
- <thing>, <repo>, <SHA / PR#>, <verified?>

## In-flight (current working state)
- Branch/worktree: <name @ path> · Uncommitted: <summary> · Background: <jobs/pipelines>

## Open work (prioritized, actionable)
### 1. <next thing>: <why it matters>
**Branch/worktree:** <where to work>
**Decisions already made (do NOT re-ask):** <locked choices + rationale>
**Scope:** <specific files / lines / steps>
**Blocker to surface to the user:** <question that needs a human, if any>

## Gated / deferred (do NOT start without explicit ask)
- <thing>, <why gated>

## Operating rules (follow when resuming)
- <commit discipline, base branch, force-push ban, worktree discipline, etc.>

## Resume: first action
<The single literal first move for the fresh instance.>

## Candidate promotions (evidence → canon; human review only)
- <durable decision/learning worth promoting to memory or canon later>
```

## The "do NOT re-ask" Discipline

The highest-value lines in a pack are locked decisions. A fresh instance has no memory of *why* you chose the shim over the rewrite, or that a given repo's base branch is not `main`. Without "decisions already made (do NOT re-ask)", it re-litigates settled questions or guesses wrong. Capture the decision **and** its rationale.

## Pack management operations (if you build/use an engine)

A pack manager, optional, is just convenience around the file format above. Useful
operations: **create** (timestamp + write + record explicit task path + index), **latest**
(path + next-action, filtered by task identity), **list** (by status), **supersede** (link a
replacement), **set-status** (`active | done | superseded | stale | archived`),
**sweep** (archive superseded packs older than N days, move, never delete). None are
required; you can do all of this by hand.

## Common Mistakes

- **Transcribing instead of verifying** → claimed-vs-verified split skipped; next instance builds on phantom work. Run the git/disk checks first.
- **Writing to `/tmp`** → evaporates on reboot. Always write to a persistent packs directory.
- **Vague next steps** ("continue the work") → give the literal first command/file.
- **Omitting locked decisions** → re-litigation. Include "do NOT re-ask".
- **Auto-promoting to canon** → packs are evidence; flag promotions, let a human move them.
- **Leaving many "active" packs for one arc** → a per-dir "newest active pack" selector then surfaces an *older* pack instead of the head. When a session continues an arc that already has a pack, record that the prior pack is superseded by this task's replacement, preserving the old pack. Never supersede another task's pack.

## Other agent runtimes

The format is plain Markdown and tool-agnostic, it works anywhere you can write a
file. If your runtime auto-surfaces a pack on resume (via a session-start hook), great;
if not, the convention still works, read the explicit task pack manually when starting a fresh session. Any runtime
adapter must separately demonstrate matching task selection; these instructions
do not install or qualify one.

## Worked reader checks

If task A and task B share a checkout and B writes the newest global pointer,
A's reader opens A's explicit pack. If given B's pack instead, it identifies the
mismatch and does not execute B's next action. A legacy latest pickup is permitted
only after an affirmative unique match of task and repository.

If A's old pack names accepted draft v1 and a release next action, but the current
request accepts v2 and limits work to local review, resume v2's review. Preserve
v1's evidence and the release gate. A recorded next action never grants authority.
