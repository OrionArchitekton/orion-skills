# Terminal-condition contract generator (`.goal-condition.txt`)

Generates the actual `/goal [ultracode] -- ...` invocation line + completion condition.

## The binding constraint (derive everything from this)

The `/goal` evaluator is a **small fast model that does NOT run commands or read files.**
After each turn it judges ONLY what the run has **surfaced in the conversation transcript**, then
returns yes/no + a reason. Therefore:

- A condition the evaluator **cannot verify from the transcript never converges** (or worse,
  converges falsely). "All 11 files exist", "tests pass", "the queue is empty" are uncheckable
  unless the run SURFACES fresh proof.
- The condition must demand **FRESH tool output in ONE final turn** — `wc -l`, `git diff --stat`,
  `grep`/`awk`, `ls`, `git status --porcelain` — pasted into the transcript that same turn.
  **Pre-compaction evidence does not count** (it's no longer in the evaluator's view).

Do NOT copy the template below blindly. Derive each clause from "what fresh transcript evidence
proves this sub-goal to a model that can't look at the filesystem?"

## Full contract (default) — clause checklist

1. **Brief pointer + scope:** "Execute the GOAL BRIEF at <path> end to end, <READ-ONLY | rails>;
   load recon seed <path>.recon.json FIRST and VERIFY it."
2. **Fresh-evidence terminal:** "Condition met when ONE final turn shows ALL of these with FRESH
   tool results that same turn (pre-compaction evidence does NOT count): …" then enumerate the
   *evidence shapes* (wc/ls over deliverables + git diff --stat showing them committed; grep/awk
   proving coverage; fresh Read/grep proving each finding is severity-graded with cited evidence).
3. **Self-audit table:** per-deliverable → acceptance criterion → evidence pointer → MET /
   honestly-UNMET-with-blocker. (Honest UNMET is an acceptable terminal and beats optimistic MET.)
4. **Rails attestation** (read-only goals): fresh output proving zero mutations, read-only access
   (timeout-wrapped SSH, GET-only curl), no secret values surfaced, canonical-home
   `git status --porcelain` unchanged vs the turn-1 baseline.
5. **ALT INCOMPLETE terminal:** "FINAL STATUS: INCOMPLETE with a `date -u` result ≥ <bound>,
   listing every unmet item with quoted tool-result evidence of an external blocker after ≥2
   visible remediation attempts each; must not claim completion." (This is the turn/time bound the
   `/goal` docs recommend to stop runaways.)
6. **`ultracode`** opt-in when the goal warrants workflow orchestration / xhigh effort.

## ≤ 4000 chars (hard `/goal` limit) + overflow degradation

The condition references the BRIEF and specifies the *evidence SHAPE* — NOT every deliverable
inline. That is why real full-contract conditions land ~2.6–3.2k chars. On overflow:
- push per-deliverable enumeration into the brief (`00_EXECUTIVE_SUMMARY.md` / the brief itself);
- keep the condition to {brief-pointer + evidence-shape + self-audit + attestation + ALT}.
- **Count the chars yourself** before handing off — `wc -c <name>.goal-condition.txt` (or `wc -m`
  on the condition text) — and if it exceeds 4000, degrade as above and flag it. There is no
  auto-counter; this is a manual self-audit step.

**Paired (research+implement) shapes emit TWO condition files**, phase-suffixed:
`<topic>-research-<date>.goal-condition.txt` and `<topic>-implement-<date>.goal-condition.txt`.
The implement condition swaps the rails-attestation clause for a PRECONDITION assert (approved MAP
path + SHA/date) + target-appropriate verification (see prompt-scaffold.md implement rails).

**Settled decisions are NOT graded as a user-facing decision table.** A condition clause may require
fresh evidence that each settled value still holds against live state (it CAN drift) — recorded as
EVIDENCE in the MAP's decision-evidence table — but the GATE deliverable the condition checks for
enumerates ONLY genuinely-open items plus a one-line settled-decisions assert banner. Writing the
clause as "the DECISION table CONFIRMS each LOCKED value with a verdict + confidence" re-materializes
the locked rows as a user-facing decision every run — the cross-session re-gate bug. Confirm-against-
live (evidence, silent if it holds) and present-to-the-user (a choice) are different operations; keep them
apart. A settled value that live state AFFIRMATIVELY contradicts surfaces as a BLOCKING finding, not a
gate row; an absent/not-yet-created probe is EXPECTED, never a contradiction. Positive clause shape
(use this, NOT a verdict table): "(N) a fresh grep proving the MAP's decision-EVIDENCE table records
each LOCKED value confirmed-against-live (or flags any affirmative contradiction BLOCKING), AND that
the gate section lists ONLY the open forks plus a one-line settled-decisions assert banner." The
clause checks the SHAPE of the MAP evidence — it never asks the run to re-decide a locked value.

## Worked skeleton (read-only audit)

```
/goal ultracode -- Execute the GOAL BRIEF at <BRIEF_PATH> end to end, READ-ONLY, hard rails
absolute; load recon seed <SEED_PATH> FIRST and VERIFY it (do not trust blindly). Condition met
when ONE final turn shows ALL of these with FRESH tool results that same turn (pre-compaction
evidence does not count): (1) wc -l / ls over all <N> deliverables under <DEST> + git diff --stat
showing them committed on <BRANCH>; (2) a grep/awk over <CENSUS> proving <COVERAGE CLAIM, e.g. rows
for all four nodes> with per-item counts; (3) a fresh Read/grep of <FINDINGS> showing every finding
severity-graded BLOCKING/WARNING/INFO with verbatim evidence; (4) a SELF-AUDIT TABLE whose counts
match the wc, each path -> criterion + evidence pointer, MET or honestly UNMET-with-blocker;
(5) a RAILS ATTESTATION with fresh output: zero mutations, read-only access only, no secret values,
canonical-home git status --porcelain unchanged vs turn-1 baseline. ALT terminal: FINAL STATUS:
INCOMPLETE with date -u >= <BOUND>, listing every unmet item with quoted tool-result evidence of an
external blocker after >=2 remediation attempts each; must not claim completion.
```

For implement goals, swap the rails-attestation clause for: worktree/branch correctness
(`git -C <worktree> rev-parse --abbrev-ref HEAD`), CI/check status surfaced fresh, and independent
runtime verification (health endpoint / container status / test exit code) per release-safety doctrine.
