---
name: goal-prompt
description: Use when you're asked to build, write, or author a goal prompt: a /goal, research, audit, decision, or implementation prompt that gets fired with /goal or /deep-research and runs autonomously. Triggers: "build a /goal prompt", "build a research goal prompt for X", "write a goal prompt for X", "goal prompt for X". Builds the prompt; never fires it.
---

# goal-prompt: build a fire-ready autonomous goal prompt

## Overview

A goal prompt is the ONE human turn that seeds a long, autonomous `/goal` run. **Upfront
context spend is the product:** the more the task is specified, recon-grounded, and rails-locked
at build time, the more autonomous and correct the run. This skill converts a loosely-stated
task into a maximally-specified, recon-grounded, rails-locked goal prompt, and **never fires it.**

**Two crown rules** (these are why the skill exists: an agent left to imitate examples skips both):

1. **Always-deep recon is mandatory, and it is error-CORRECTION, not gathering.** A cheap scout
   draft is then adversarially corrected by a grounding fan-out that refutes-or-confirms every
   premise against live state. This catches *backside errors* (the false facts that produce a
   confident-but-wrong run) BEFORE they reach the brief. Skipping or shallowing this is the #1 failure.
2. **The terminal condition must be transcript-demonstrable.** The `/goal` evaluator is a small
   fast model that **cannot run commands or read files**; it judges ONLY what the run
   surfaced in the conversation. "All files exist" is uncheckable and never converges. "ONE final
   turn shows FRESH `wc`/`git diff`/`grep` output + a self-audit table" is checkable. Derive the
   condition from this rule; do not copy a template blindly.

## When to use

- You're asked to build/author/write a goal prompt, research goal prompt, audit goal, decision goal,
  or implementation goal: anything fired with `/goal` or `/deep-research` and run hands-off.

**When NOT to use:**
- The task isn't decided yet ("should I build X?") → that's an upstream brainstorming / ideation step. Point upstream; do not invent scope here.
- You're asked to RUN a goal / research / workflow → that's the native `/goal`, `/deep-research`, `/workflows`. This skill only BUILDS the prompt.

## Procedure

1. **Detect the shape** (default = research+implement) and confirm in ONE line. See `references/prompt-scaffold.md`.

   | Shape | Emits | Use when |
   |---|---|---|
   | research+implement (default) | `<topic>-research-<date>.md` (→MAP) + `<topic>-implement-<date>.md` (gated) + sidecars | build-something needing a research→approve→build arc |
   | audit | `<topic>-audit-<date>.md` (READ-ONLY) + sidecars | read-only census/audit, no mutation |
   | decision | `<topic>-decision-<date>.md` (evaluate→BUILD set→plan→gate) + sidecars | "evaluate X, decide what to build" |
   | standalone | `<topic>-<verb>-<date>.md` + sidecars | execution / cutover / ratification one-shot |

   *"Sidecars" = the `.goal-condition.txt` (one per fireable prompt: a research+implement pair has TWO, phase-suffixed) + the `.recon.json` seed. **Shape tiebreaker:** "evaluate whether to do X" alone → decision; "evaluate, then build what I approve" → research+implement (it adds the staged runnable STEP-2 prompt). When in doubt and the user wants a runnable next step, pick research+implement.*

2. **Run always-deep two-tier recon** (crown rule 1). Scout-draft a seed, then run the grounding
   fan-out that adversarially corrects it. Emit `<topic>-<date>.recon.json`. Full spec, the
   memory-primed probe checklist, AND the single-agent/no-fan-out fallback: `references/recon.md`.
   **Do not shallow this**: if you genuinely cannot fan out, run the skeptic passes sequentially
   inline and mark the seed's status; never silently skip Tier 2.

3. **Assemble the prompt** from the codified scaffold + recon-filled slots. The scaffold is fixed
   (doctrine, phased structure, rails, deliverable shape); only the MINE-BY-X and GOTCHAS slots and
   the task specifics come from recon. See `references/prompt-scaffold.md`. **Context economy,
   durable state and budget:** the emitted prompt should instruct the fired run to reference large
   data by path rather than inline, write deliverables incrementally, checkpoint plan/progress to
   disk at every phase boundary, re-read that durable state after any compaction or resume (never
   trust transcript memory alone), bound every loop with an explicit breaker (max rounds, dry-round
   caps, a budget guard), and state the expected phase count so an over-running run notices and
   re-plans instead of grinding.

4. **Generate the terminal condition** (`.goal-condition.txt`) per crown rule 2, full contract by
   default, ≤4000 chars, with overflow degradation. Template + rules: `references/terminal-condition.md`.

5. **Self-audit each emitted artifact against a deterministic checklist, then hand off** (do NOT
   fire):
   - the `.goal-condition.txt` is <= 4000 bytes (`wc -c`);
   - it starts with `/goal `;
   - it contains the literal string `Condition met`;
   - it demands FRESH tool output in the final turn, not just an assertion of state;
   - it demands a self-audit table (per-deliverable, criterion, evidence pointer, MET/UNMET);
   - it carries an ALT `FINAL STATUS: INCOMPLETE` branch gated on a `date -u` floor;
   - the prompt, condition, and recon files pair by stem (same `<topic>-<phase>-<date>` prefix).

   Automate this checklist as a validator script if your setup allows it; keep it report-only
   advisory, never a hard gate, you still hand off and the user still fires. THEN confirm the SOFT
   judgments no gate can make: the fresh-evidence clause is genuinely evaluator-checkable (not just
   the word present), `.recon.json` carries verify-don't-trust instructions + `generated_at`, rails
   match the shape, scaffold holds zero task-specific content. Report a short build-audit and the
   exact `/goal` line the user will fire.

## Common mistakes (from baseline testing)

| Mistake | Fix |
|---|---|
| Light recon / "I didn't enumerate live state, my list may be incomplete" | Crown rule 1: run the grounding fan-out that CORRECTS the scout; emit `.recon.json`. The recon IS the value. |
| Copying the "fresh results that same turn" wording without understanding why | Crown rule 2: the evaluator can't read files; derive the condition from that, so it holds even with no exemplar to copy. |
| Condition says "the 11 files exist / tests pass" | Uncheckable by the evaluator. Demand FRESH tool output surfaced in one final turn + a self-audit table. |
| Re-deriving conventions / rails each build | Those are codified here and in the scaffold; spend recon budget on codebase traversal, not basics. |
| Firing the goal, or chaining research→implement in one run | Builder never executes. The research→MAP→approve GATE is a SEPARATE human fire (`/workflows` + the `/goal` loop have no mid-run input). |
| Inventing scope when the task isn't decided | Stop; point to an upstream brainstorming step. |

## Red flags: STOP

- "I'll skip the deep recon, the scout seed is probably fine" → backside errors live exactly here.
- "I'll reference the files by name in the condition" → the evaluator can't see files.
- "I'll fire it to check it works" → never. Hand the artifact to the user.
- About to write task-specific facts into the codified scaffold → those belong in recon slots.

## Outputs

Two destinations, do NOT conflate them:
- **The prompt artifacts you build** → a dedicated prompts directory (e.g. `~/goal-prompts/<topic>-<phase>-<date>.md`) +
  `.goal-condition.txt` + `.recon.json`. MAP → `<prompts-dir>/<topic>-MAP-<date>.md`. Naming matches
  your existing convention exactly. These are the ONLY files this skill writes.
- **The deliverables the FIRED goal will later produce** (an audit dossier, migrated code, etc.)
  go wherever that goal's `## DELIVER` section says (a repo, a worktree branch, or an audit dir),
  NOT necessarily under the prompts directory. The brief specifies that destination; the skill does not
  put goal *output* in the goal-*prompt* directory.
