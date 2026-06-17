---
name: pre-compact
description: Use when about to run /compact, when the context window is filling up or near its limit, when wrapping up a long working session, or when handing in-progress work to a fresh/future instance so it can resume without re-deriving state. Triggers — "drop a handoff", "recap before compact", "save context", "context is at 90%".
---

# Pre-Compact Context Pack

## Overview

`/compact` discards most of the conversation. This skill captures the session into a **persistent, queryable context pack** so a fresh instance resumes with zero re-derivation — what shipped, what's in flight, what's next, and the operating rules to follow.

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

A pack is just a Markdown file in a **persistent directory** — NOT `/tmp` (wiped on
reboot). Pick a durable, agent-neutral location and keep it consistent, e.g.:

- `packs/` — one file per pack, named `<UTC-timestamp>-<slug>.md`.
- a `LATEST.md` pointer (a copy of, or a path to, the newest pack) so a fresh
  instance has one well-known file to read on resume.

That is the entire contract. You can manage it **by hand** (write the file, update
the pointer) or wrap it in a small **optional engine** that timestamps the id,
repoints `LATEST.md`, supersede-links replaced packs, and rebuilds an index — but no
such engine is required for this skill to work. The format is the durable part; the
tooling is a convenience.

## The Iron Rule: Verify, Don't Transcribe

Your own session narrative is the **least** trustworthy input. Before writing the pack, confirm claims against reality. A handoff that says "fixed and committed (a1b2c3d)" when no such commit exists is worse than no handoff — it sends the next instance building on phantom work.

Set `verified_state` honestly: `verified` (all key claims disk-confirmed) · `mixed` · `claimed-only`. In the body, split **✅ VERIFIED** from **⚠️ CLAIMED (unverified)**.

## Process

**1. Capture real runtime state** (don't rely on memory). For each repo/worktree touched this session:
```bash
git -C <repo> status -sb && git -C <repo> log --oneline -8
git worktree list
```
Note: current branch(es), uncommitted changes, any in-flight background jobs/agents, recently edited files.

**2. Verify claims.** For every "I did X": does the commit/branch/PR actually exist? Did tests actually run (real output)? Was a deploy independently verified? Downgrade `verified_state` for anything you can't confirm.

**3. Compose the body** using the template below. Be specific — file:line, SHAs, exact next move.

**4. Write the pack.** Write the body to a timestamped file in your packs directory and update the pointer:
```bash
PACKS=~/.claude/handoffs/packs            # or wherever you keep packs (persistent, not /tmp)
mkdir -p "$PACKS"
TS=$(date -u +%Y-%m-%dT%H%M%SZ)
cp /tmp/pack-body.md "$PACKS/$TS-<slug>.md"
cp "$PACKS/$TS-<slug>.md" ~/.claude/handoffs/LATEST.md   # the well-known pickup file
```
Record in the body the directory + git baseline (branch, HEAD sha) you were working
in, so a fresh instance can recognize which pack matches its working dir. If you use
an engine, it does this (and supersede-links) for you; otherwise do it inline.

**5. Print the pickup line.** Tell the user to paste this to the fresh instance:
> Read ~/.claude/handoffs/LATEST.md and resume from it.

**6. Flag — do not perform — promotions.** If the session produced a durable decision/learning, list it under *Candidate promotions* for the human to later move into memory/canon. Never auto-write canon.

## Pack Body Template

```markdown
# HANDOFF — <title>
**Date:** <YYYY-MM-DD> · **Host:** <box> · **Identity:** <git identity>
**Pointers:** memory file(s) · authoritative plan · proof packet · audit packs

## TL;DR — where things stand
<2–4 sentences: the mission and current position.>

## Verified state
- ✅ VERIFIED: <claim + how confirmed (SHA, test output, health check)>
- ⚠️ CLAIMED (unverified): <claim + why not confirmed + how to confirm>

## Shipped / merged
- <thing> — <repo> — <SHA / PR#> — <verified?>

## In-flight (current working state)
- Branch/worktree: <name @ path> · Uncommitted: <summary> · Background: <jobs/pipelines>

## Open work (prioritized, actionable)
### 1. <next thing> — <why it matters>
**Branch/worktree:** <where to work>
**Decisions already made (do NOT re-ask):** <locked choices + rationale>
**Scope:** <specific files / lines / steps>
**Blocker to surface to the user:** <question that needs a human, if any>

## Gated / deferred (do NOT start without explicit ask)
- <thing> — <why gated>

## Operating rules (follow when resuming)
- <commit discipline, base branch, force-push ban, worktree discipline, etc.>

## Resume — first action
<The single literal first move for the fresh instance.>

## Candidate promotions (evidence → canon; human review only)
- <durable decision/learning worth promoting to memory or canon later>
```

## The "do NOT re-ask" Discipline

The highest-value lines in a pack are locked decisions. A fresh instance has no memory of *why* you chose the shim over the rewrite, or that a given repo's base branch is not `main`. Without "decisions already made (do NOT re-ask)", it re-litigates settled questions or guesses wrong. Capture the decision **and** its rationale.

## Pack management operations (if you build/use an engine)

A pack manager — optional — is just convenience around the file format above. Useful
operations: **create** (timestamp + write + repoint `LATEST.md` + index), **latest**
(path + next-action of the newest pack), **list** (by status), **supersede** (link a
replacement), **set-status** (`active | done | superseded | stale | archived`),
**sweep** (archive superseded packs older than N days — move, never delete). None are
required; you can do all of this by hand.

## Common Mistakes

- **Transcribing instead of verifying** → claimed-vs-verified split skipped; next instance builds on phantom work. Run the git/disk checks first.
- **Writing to `/tmp`** → evaporates on reboot. Always write to a persistent packs directory.
- **Vague next steps** ("continue the work") → give the literal first command/file.
- **Omitting locked decisions** → re-litigation. Include "do NOT re-ask".
- **Auto-promoting to canon** → packs are evidence; flag promotions, let a human move them.
- **Leaving many "active" packs for one arc** → a per-dir "newest active pack" selector then surfaces an *older* pack instead of the head. When a session continues an arc that already has a pack, mark the prior one `superseded` (or delete its pointer) so only the head is current.

## Other agent runtimes

The format is plain Markdown and tool-agnostic — it works anywhere you can write a
file. If your runtime auto-surfaces a pack on resume (via a session-start hook), great;
if not, the convention still works — just **read your `LATEST.md` (or newest pack) manually**
when you start a fresh session, since nothing will auto-inject the pointer.
