# Emitted-prompt scaffold (codified DNA + recon slots)

The scaffold is FIXED and task-agnostic. It holds zero task-specific content. Only the
`{{MINE_BY_X}}`, `{{GOTCHAS}}`, and `{{SETTLED_DECISIONS}}` slots and the `{{GOAL}}`/deliverable
specifics come from recon. This is the invariant that keeps quality deterministic instead of
depending on the agent re-deriving conventions each time.

## Structure rules (bake into every emitted prompt)

- **Explicit role + structured sections** (markdown headers; the run reads these literally).
- **State scope explicitly** — frontier models are literal; "every node, not just the first", "all four
  surfaces", etc. Do not rely on the run generalizing.
- **Coverage-not-filter for find/audit phases** — "report every finding incl. uncertain/low-sev;
  a later step filters." Otherwise the run self-suppresses findings.
- **Be explicit about rails** — what must NOT change, what access is allowed.
- **Explicit completion criteria** live in the `.goal-condition.txt` (see terminal-condition.md),
  but the brief restates the deliverable shape so the run knows the target.

## Common scaffold (all shapes)

```markdown
# <GOAL/deep-research> (<STEP n of m, if paired>) — <topic>
Status: SAVED <date>, awaiting the go to fire. <READ-ONLY | worktree+CI>.
<gating links: the paired step's prompt path; the recon seed path>

## GOAL
<one paragraph: the measurable end state> {{GOAL}}

## Operating doctrine (non-negotiable)
- Investigate the codebase directly. Do NOT ask the user for context findable via filesystem, git,
  memory, or other tools. "Ask the user" is a last resort.
- Load the recon seed <path>.recon.json FIRST and VERIFY it against live state — it is a SEED,
  not authority; may be stale by fire time. Do not trust blindly.
- Verify every premise against live state before accepting it.
- **Settled decisions** (the SETTLED DECISIONS block / recon `settled_decisions[]`) are ASSERTED, not
  re-opened. Confirm each against live state as EVIDENCE — a namespace, identity, or version CAN drift
  — but do NOT re-present a settled decision to the user as a choice. Re-gate ONLY genuinely-open items. A
  settled decision that live state AFFIRMATIVELY CONTRADICTS is a BLOCKING finding: surface it with
  evidence (the one thing that re-opens it), never a silent default re-ask. An ABSENT/unverifiable probe
  (e.g. a repo/org not created YET — expected in a research-before-build arc) is NOT a contradiction:
  leave it asserted, marked `unverifiable-pending`.
- For any external-state premise inherited from the prompt builder — installed plugins, git roots,
  materialized deploy paths, CLI/API shape, hook payload shape, remote monitor state, systemd state
  — run the preflight probes from `references/recon.md` and record claim-vs-actual deltas before
  acting on the premise.
- Severity-grade all findings: BLOCKING / WARNING / INFO.
- Adversarially red-team your own conclusions before presenting (spawn a skeptic per headline claim).

## SETTLED DECISIONS (assert — do NOT re-gate)   <- omit this whole section when the task has no prior locked decisions
{{SETTLED_DECISIONS}}   <- recon settled_decisions[]: {decision | value | locked_at/where | confirm-against-live probe}.
                           Confirmed-against-live = silent EVIDENCE; only a live CONTRADICTION re-opens one (as BLOCKING).

## Phases
<shape-specific — see below>

## Rails
<shape-specific — READ-ONLY block OR worktree+git-identity+CI block>

## MINE, BY X  (research/audit/decision)
{{MINE_BY_X}}   <- recon source-mining list, with paths

## GOTCHAS — do NOT re-learn the hard way
{{GOTCHAS}}     <- recon gotcha list, memory-primed

## DELIVER
<exact artifacts, paths, and an operator-grade summary spec: what shipped, verified, skipped, risks>
```

## Fan-out execution discipline (bake into any prompt whose run fans out subagents)

When a built prompt's run will spawn parallel subagents (research fan-out,
multi-file migration, review dimensions), bake these three dials into the
prompt's Phases/Rails. They are encoded HERE (first-party harness guidance)
rather than as per-agent frontmatter because your filesystem/review agents may
be vendored (installed via a plugin) — editing their frontmatter drifts from
upstream and is overwritten on plugin update. The native Workflow/Agent
per-call options below are the durable, drift-free mechanism.

**1. Scaling table (right-size the fan-out).** Match agent count + per-agent
tool-call budget to task complexity; don't fix a single fan-out width:

| Task class | Subagents | Tool calls / agent |
|---|---|---|
| Simple fact / single lookup | 1 (inline) | 3–10 |
| Comparison / few-angle | 2–4 | 10–15 |
| Broad audit / many-slice | 1 per slice (cap ~10–16 concurrent) | 10–20 |
| Open-ended discovery | loop-until-dry: spawn until K rounds add nothing | per round |

After each round the lead agent SYNTHESIZES and decides whether more fan-out is
warranted (synthesize-and-decide), instead of a blind fixed width.

**2. Three-tier model routing.** Pin cheap-tier models on mechanical
subagents, reserve the frontier tier for synthesis/coordination:
- cheap tier (e.g. a small fast model) — fetch, grep, file-read, mechanical transforms;
- mid tier — per-item review/extraction;
- frontier (the session model) — lead synthesis, judging, adversarial verify.
In Workflow scripts use `agent(..., {model: '<cheap>'})` / `effort:'low'` on
mechanical stages; in the Agent tool pass `model`. (The *principle* is the durable
part — adopt the tiering; pick the specific model tiers your runtime offers.)

**3. Worktree isolation for FS-mutating fan-out.** Any subagent that
MUTATES files in parallel must run isolated so siblings don't collide and a
no-change run leaves no residue: Workflow `agent(..., {isolation: 'worktree'})`
or the Agent tool's `isolation: 'worktree'`. The worktree branches from the
default branch and is auto-removed if the agent made no changes (zero residue);
use it ONLY for parallel mutation (it costs setup time + disk per agent).

## Shape-specific phases & rails

**research+implement (default):**
- STEP 1 (research, READ-ONLY): Phases = inventory/anti-dup → stress-test premises → decide →
  master plan (the MAP) → **GATE** (stop; present ONLY genuinely-open forks + a one-line
  settled-decisions assert banner — never re-ask a locked decision; wait for explicit "go").
  Rails = READ-ONLY.
  Deliverable = the MAP at `<prompts-dir>/<topic>-MAP-<date>.md` + the staged STEP 2 prompt.
- STEP 2 (implement): opens with **PRECONDITION: STEP 1 produced the MAP AND the user approved it**
  (assert the approved MAP's path + SHA/date; skip rows the user dropped). Phases = steps → verify-live
  → deliver. **Derive the implement rails from the TARGET's own contract — do not hardcode a
  repo/PR flow:**
  - *git repo (code):* fresh worktree from main (never canonical home; never force-push), brand git
    identity if applicable, CI gates must pass, independent runtime verification before "done".
  - *operator-state / state-dir* (e.g. an operator-state directory, snapshot-repos): work in place under the dir's
    own contract; snapshot-semantics (a daily auto-commit timer), NOT a feature-branch PR; respect
    hook-owned / gitignored files; use the dir's sanctioned tools, not ad-hoc rm/mv.
  - *config dir / no-VCS target:* in-place edits with a pre-change baseline + reversibility note.
  Always: independent runtime verification before claiming done (release-safety doctrine).

**audit:** Phases = census → classify (drift/overlap/silent-failure/etc.) → severity-graded
findings → self-audit. Rails = READ-ONLY (no mutations, timeout-wrapped SSH, root-owned-file
rc-aware "COULD-NOT-VERIFY ≠ absent", no secret values, no live fix — fixes become gated follow-ups).

**decision:** Phases = inventory (ALREADY-HAVE/PARTIAL/NET-NEW) → stress-test premises →
decision table ({DO|DEFER|DO-NOT}, value, effort, blast-radius, rationale; explicit DO-NOT list) →
master plan for DO set → GATE. Rails = READ-ONLY. Bias to smallest high-confidence change; "empty
DO set" is a valid high-value outcome.

**standalone:** single brief with the common scaffold; rails match whether it mutates.

## The MAP (what research produces for the gate)

`<prompts-dir>/<topic>-MAP-<date>.md`:
- Per-row table: `item | claim | grounding evidence (CITED) | confidence (HIGH/MED/LOW)`.
- Settled/locked decisions live in a decision-EVIDENCE table (each confirmed-against-live, with the
  probe) — the gate section then carries ONLY genuinely-open forks plus a one-line assert banner of
  the settled values. A locked decision rendered as a "confirm this row" gate line is the re-gate bug.
- "Read before approving" synthesis notes (the arc, the close calls, candidate drops).
- A Step-2 prep appendix (per-row implementation hints) so the implement goal is well-seeded.
- A week/row flagged `confidence:none` is FLAGGED, never invented (evidence-grounded, no padding).

## The gate is a SEPARATE fire

research → MAP → the user approves/edits → THEN the user fires the implement goal. Not chainable in one run:
`/workflows` has no mid-run user input, and the `/goal` loop only returns control on completion.
The two-step split is structural, not stylistic.
