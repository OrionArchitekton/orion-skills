---
name: oss-loop
description: Use when carrying an OSS tool from idea/spec to a shipped, published release through one closed loop where the agent does everything reversible and a human touches only the irreversible gates (publish, merge, tag, DNS, secrets). Triggers — /oss-loop, "ship the next version of <tool>", "take <tool> to vN", "run the OSS build-ship loop". Composes your prompt/research/TDD/launch skills; it does not reimplement them. NOT for a one-off code change (that is a TDD/implement loop) or the public product page alone (that is your launch skill).
---

# OSS Build-Ship Loop (operator-gates-only)

## Overview

Carry an OSS tool from idea/spec to a shipped, published release through one closed
loop where the **agent does everything reversible and a human touches only the
irreversible gates**:

**build the prompt → research → human approves the plan → TDD the change to a
CI-green PR → human merges/tags → launch the public surface → verify live → capture
the lesson.**

This skill is the **orchestrator + gate boundary** — it COMPOSES whatever skills your
harness has for each step; it does not reimplement them. In this library those steps
map to `goal-prompt` (build the prompt), `tdd-loop` (the hardened implement loop), and
`learn-capture` (close the loop); the launch step is whatever publishes your
microsite / registry page. Swap in your own equivalents — the gates bind to artifacts
either way.

## When to use
- A new version of an already-shipped OSS tool (the common case → a parameter bump + a
  recon delta, not a harness rebuild).
- A new tool, discover → build → ship.
- Triggers: `/oss-loop`, "ship the next version", "run the OSS build-ship loop".

**When NOT to use:**
- A single code change with no release → a TDD/implement loop (`tdd-loop`).
- Just the public product page → your launch/microsite skill.
- An undecided idea ("should I build this?") → brainstorming, not this.

## The loop (compose each step; do not reinvent)
0. **RECALL + RECON** — pull prior-arc artifacts (the prompt set, the approved plan,
   where the repo/registry homes are); for a new version, run the recon DELTA against
   the last release. Refuse if preconditions fail.
1. **PROMPT** — build the research(+implement) prompt: recon-grounded, with a
   transcript-checkable terminal condition (`goal-prompt`). Never fire it from here —
   the approval gate is a separate human fire.
2. **RESEARCH** — the human fires the research/loop run → a reviewed plan (a "MAP").
   If a research pass returns "all refuted / inconclusive", check for an **abstention**
   (a verifier that crashed / rate-limited and returned no votes) before trusting it —
   a crashed verifier is not a refutation.
3. **GATE (human)** — the human approves/edits the plan's DO set.
4. **IMPLEMENT** — drive the change to a CI-green PR through a self-correcting
   RED→GREEN loop with a BLOCKING adversarial + security review (`tdd-loop`). The agent
   OPENS the PR; it does not tag or merge.
5. **OPERATOR GATES (human)** — push the version tag, merge the human-merged PR, change
   DNS. The agent is incapable of these by construction.
6. **LAUNCH** — publish the public surface (microsite / product page), only if it
   changed.
7. **VERIFY LIVE** — the installer's source of truth, live: the package index shows vN
   as latest (`pip index versions <pkg>` or your ecosystem's equivalent), the image
   registry tag pulls anonymously, the microsite returns 200 over TLS. **"merged" is
   not "published".**
8. **CAPTURE** — route the lessons to durable homes (`learn-capture`).

## Rails (operator-gates-only — non-negotiable)
- The agent MUST STOP at every irreversible gate: **publish to a package/image
  registry, merge a human-merged PR, push a tag, change DNS, arm a scheduled job, write
  a secret.** Make this fail-closed by construction (the agent literally cannot perform
  them), never a prose "please don't".
- CODE work in a fresh worktree/branch off the repo's **detected default branch** (never
  assume `main`, never the canonical checkout); never force-push.
- Scaffolding a microsite from a template: EXCLUDE the deploy-provider dir (e.g.
  `.vercel/`) — a leaked one can clobber the template's production project.
- Never echo secrets; pass a secret-scan (e.g. gitleaks) before every commit.
  Severity-grade findings BLOCKING / WARNING / INFO.

## Red flags — STOP
| Thought | Reality |
|---|---|
| "I'll just merge/tag/publish to finish the loop." | Those are the human's gates. The agent STOPS and hands them over. |
| "I'll rebuild the harness for the new version." | A new version is a parameter bump + a recon delta, not a rebuild. |
| "The research pass said all refuted, so the research failed." | Check for an abstention (a crashed/rate-limited verifier returning no votes) first — silence is not a refutation. |
| "It merged, so it's shipped." | Verify the installer's source of truth (the package/image registry), live. |

## Boundary (defer to the consumer's repo)
This skill owns the **sequence and the gate boundary**, not your deploy mechanics.
Branch naming, the secret manager, the package/image registries, DNS, and the CI
specifics are your repo's doctrine — this skill only insists the agent stops at the
irreversible gates and verifies the live source of truth before claiming "shipped".

## What it deliberately does NOT do
- Does NOT cross any irreversible gate autonomously.
- Does NOT reimplement the prompt / research / TDD / launch steps — it sequences them.
