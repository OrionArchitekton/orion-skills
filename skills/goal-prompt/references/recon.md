# Always-deep two-tier recon

The recon is the skill's load-bearing value. It spends budget ONLY on **codebase traversal**
(volatile, task-specific unknowns), never on **basic recon** (authority order, naming,
worktree/git rules, routing, doctrine, rails — those are codified in the scaffold). Codification
*redirects* the recon budget onto the unknowns that cause backside errors.

## Why two tiers

A single pass that "gathers context" produces a confident-but-wrong brief when the gathered facts
are wrong. The value is **correction**, not gathering. In practice a grounding fan-out routinely
corrects several false premises in a scout's seed before they reach the brief — e.g.
gitignored-but-live plaintext secrets, dual storage assumed single, editable installs pointing at
stale copies (*what runs ≠ what's newest*), stale-but-load-bearing copies. Any one would have
produced a wrong plan.

- **Tier 1 — inline scout (cheap).** The skill's own fast traversal drafts a *provisional* seed:
  quick `rg`/`ls`/register/routing reads. Explicitly a draft; expected to contain errors.
- **Tier 2 — grounding fan-out (the spend).** A background Workflow (or parallel agents) whose
  PRIMARY job is to **adversarially correct the scout's seed**. Each scout premise → a skeptic
  that checks it against *live* state and must refute-or-confirm with cited evidence. The
  corrected seed is what gets written.

**No-fan-out fallback (REQUIRED when you can't spawn agents — e.g. you are yourself a subagent,
or in a no-hook env):** do NOT skip Tier 2 and do NOT fake a fan-out. Run the four skeptic
passes (below) **sequentially inline** against live state, and stamp the seed
`"tier2": "sequential-inline"` (vs `"fan-out"`). If even sequential live verification is impossible
(no access), stamp `"tier2": "scout-only-UNVERIFIED"` and say so loudly in the build-audit and in
the seed's `verify_instructions` — an unverified seed is a known-risk handoff, never a silent one.

## Recon agents (fan out; cross-check before a finding enters the seed)

1. **Anti-duplication** — does this already exist / partially exist? Grep skills, scripts,
   registers, routing table, recent git across the project's repos. Classify each sub-goal
   ALREADY-HAVE / PARTIAL / NET-NEW.
2. **Premise verification** — every premise the task rests on, checked against LIVE state (not
   docs). Each premise → {confirmed | refuted | unverifiable} + cited evidence. Refuted premises
   must survive a second skeptic.
3. **Source mining** — the concrete, dated sources the fired goal should mine (git history,
   registers, handoffs, memory, specific files), with paths. Becomes the prompt's "MINE, BY X" list.
4. **Gotcha discovery (memory-primed)** — prime from your agent's accumulated memory notes (the
   lessons already learned the hard way) and probe the task for those classes. Becomes the
   prompt's "GOTCHAS — do NOT re-learn the hard way" list.

Coverage-not-filter at the finding stage (report everything; the cross-check is the filter).

## Recurring backside-error probe checklist (seed from your memory notes; extend as the corpus grows)

- **gitignored-but-live** — untracked files (`.env`, secrets) present and load-bearing at runtime.
- **what-runs ≠ what's-newest** — editable installs / symlinks / materialized allowlist trees
  pointing at stale copies.
- **stale-but-load-bearing** — looks prunable, but deleting breaks imports/boot.
- **storage/topology assumption** — single vs dual/multi backend; a shared var feeding two sides.
- **fail-closed gate in the path** — a CI/secret/merge gate that will block the autonomous run.
- **suppressed-probe / silent-failure** — a check whose failure reads as success.
- **stale-tree / worktree mis-key** — branch/push from a canonical home or stale tree.
- **audit-shape patterns** (read-only census/audit): *enabled-but-not-firing* (a job/timer with a
  recent LAST but empty NEXT), *doc-claims-a-job-that-no-longer-runs*, *uneven coverage* (a guard
  wired on some units and not others), *COULD-NOT-VERIFY ≠ absent* (an rc≠0 read is a gap, never
  proof of absence).
- **external-state premise without a live probe** — installed plugin versions, git roots,
  materialized deploy paths, CLI/API shapes, hook payload shape, remote monitor state, and
  systemd state must each have a one-line live probe before the prompt treats the claim as true.
  File existence and old recon are not enough.

## Build-time external-state preflight block

Before emitting a `.goal-condition.txt`, enumerate every premise that depends on state outside
the prompt text itself and run a cheap live probe. Capture the result as claim-vs-actual deltas in
the build audit and in `.recon.json` `premises[]`. Use probes like these, adapted to the task:

```bash
git -C <path> rev-parse --show-toplevel && git -C <path> status --short --branch
test -r ~/.claude/plugins/installed_plugins.json && jq -r '.[]?.name // empty' ~/.claude/plugins/installed_plugins.json
test -r ~/.claude/plugins/known_marketplaces.json && jq -r 'keys[]?' ~/.claude/plugins/known_marketplaces.json
systemctl --user list-timers --all --no-pager
printf '%s\n' '{"tool_name":"Write","tool_input":{"file_path":"/tmp/probe"}}' \
  | ~/.claude/hooks/pretooluse-readonly.sh
```

If a probe is unavailable, mark that premise `unverifiable` and carry the risk into the fired
goal. Do not silently convert a missing probe into a confirmed claim.

## `.recon.json` schema (the verify-don't-trust seed)

**Keep the seed compact — CITE, don't inline.** `evidence` fields hold a path + the command +
a *trimmed* result line, not raw multi-KB output blobs. The seed is a verifiable pointer-map the
fired goal re-runs, not an evidence archive. Add a `"tier2"` field
(`"fan-out" | "sequential-inline" | "scout-only-UNVERIFIED"`) recording how it was grounded.

```json
{
  "topic": "<slug>",
  "generated_at": "<ISO-8601 UTC>",
  "shape": "research+implement|audit|decision|standalone",
  "verify_instructions": "Load FIRST and VERIFY against live state before trusting. This is a recon SEED, not authority. It may be stale by fire time; re-check each premise in the goal's first phase.",
  "premises": [{"claim": "...", "status": "confirmed|refuted|unverifiable", "evidence": "<cited: path/cmd/output>", "corrected_from": "<scout's wrong claim, if corrected>"}],
  "anti_dup": [{"subgoal": "...", "classification": "ALREADY-HAVE|PARTIAL|NET-NEW", "evidence": "..."}],
  "sources": [{"what": "...", "path": "...", "why": "..."}],
  "gotchas": [{"class": "<from checklist>", "detail": "...", "evidence": "...", "memory_ref": "<your memory note id, if any>"}],
  "settled_decisions": [{"decision": "<what was decided>", "value": "<the chosen value>", "locked_at": "<ISO date>", "locked_where": "<gate prompt | handoff pack | source>", "confirm_against_live": "<cheap live probe that re-validates the VALUE as evidence — NOT a user-facing question>"}]
}
```

The emitted prompt always instructs: "load the recon seed FIRST and VERIFY it; do not trust blindly."
The seed is advisory grounding, not authority — recon can be stale by the time the goal fires.

## `settled_decisions` vs `premises` — the re-gate firewall

Decisions the user has ALREADY made (locked at a prior gate, in a handoff, or via a direct answer) go in
`settled_decisions[]`, NOT in `premises[]`. The routing is the whole point:

- a **premise** is a fact the task rests on → the fired goal re-verifies it and MAY surface it for
  (re-)decision;
- a **settled decision** is a choice the user already made → the fired goal **asserts** it. It confirms the
  VALUE against live state as EVIDENCE (a namespace, identity, version, or path CAN drift, so the
  check is legitimate) but does **not** re-present the decision to the user as a question.

Confirm-against-live (silent evidence if it holds) and present-to-the-user (a choice) are **different
operations.** Conflating them — routing a locked value through `premises[]` or grading it "confirm
each locked row with a verdict" in the terminal condition — is what re-asks an already-made decision
every session (the cross-session re-gate bug). The ONE thing that re-opens a settled decision is live
state CONTRADICTING it: that surfaces as a BLOCKING finding with evidence, never a silent default
re-ask. **Absent/unverifiable ≠ contradicted** (the "COULD-NOT-VERIFY ≠ absent" probe rule above
applies here too): a probe that returns ABSENT — e.g. the repo or org does not exist YET, which is
EXPECTED in a research-before-build arc — is NOT a contradiction. Only an AFFIRMATIVE live value that
DIFFERS from the locked value re-opens it; an absent/unverifiable probe leaves the decision asserted
(mark it `unverifiable-pending`), never a re-ask. (Worked example: a locked "6 clean items" value that
live state AFFIRMATIVELY refuted as "3 clean" was a legitimate BLOCKING re-open; the locked rows
that live state confirmed were NOT re-asked — and a `gh repo view` returning "Could not resolve" for
a not-yet-created repo was treated as EXPECTED-absent, not a contradiction.)
