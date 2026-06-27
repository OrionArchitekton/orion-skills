---
name: chain-launcher
description: Use right after you approve a research/decision plan (a MAP) to surface the exact next command for the implement phase — making the research → approve → implement hand-off frictionless without auto-crossing the approval gate. Triggers — /chain-launcher, "what's the next goal line", "advance the chain", "fire the implement step". Never auto-fires the next phase (the gate is a deliberate human fire); does not build the prompt (that is goal-prompt).
---

# Chain Launcher — surface the next command on plan approval

## Overview

The compounding pattern for autonomous work is: **build the prompt → run the
research/decision phase → a human approves the plan → run the implement phase.** The
research→implement gate is a **separate human fire by construction** — a long
autonomous run returns control only on completion, and there is no mid-run input to
inject an approval into, so nothing can (or should) auto-cross the approval gate.

This skill removes the *friction*, not the gate: given an approved plan / prompt set,
it surfaces the **exact next command** for the human to fire, so they don't re-derive
it. Convenience over re-typing.

## When to use
- Right after approving a research/decision plan (a "MAP"), to get the implement-phase
  command.
- Triggers: `/chain-launcher`, "what's the next goal line", "advance the chain".

**When NOT to use:**
- To auto-fire the next phase — never; the gate is a deliberate human fire.
- To BUILD the prompt — that is `goal-prompt`.

## Procedure
1. Identify the topic stem you used when you authored the prompt set (e.g.
   `timer-audit`).
2. Locate the paired **implement** prompt/launcher you saved for that stem and print
   its fire line **verbatim** — that IS the command to run. A tiny report-only helper
   that globs your prompts directory for `<stem>-implement-*` removes the friction; it
   reads and prints only — it fires nothing.
3. **Bind to the plan you just approved — do not guess on ambiguity.** If more than one
   launcher matches the stem, do NOT print one blindly: list the matches and pick the
   one tied to the approved plan (matched by the plan's id/date, or the newest), and
   surface the ambiguity. Firing a stale or sibling launcher — one not bound to the
   approval — is exactly the failure this gate exists to prevent.
4. The human reviews and fires it (editing the DO set inline first if the approval
   changed it).

## Rails
- **Never auto-fire.** Print the line; the human fires it. The gate is a separate,
  deliberate fire.
- The helper is **report-only** — it reads and prints; it writes nothing and runs
  nothing.
- **Bind to the approval.** On more than one match, surface the ambiguity and pick the
  launcher tied to the approved plan; never fire one you can't tie to the approval.
- If no implement prompt exists yet, say so and point back to `goal-prompt` (build it
  first).

## Boundary (defer to the consumer's setup)
Where you keep prompt sets, how you name the implement launcher, and which command runs
an autonomous phase are your harness's conventions. This skill only insists the
research→implement hand-off stays a deliberate human fire and that the next command is
surfaced, not re-derived.
