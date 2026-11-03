---
name: apply-review-findings
description: "Use when addressing review comments, bot reports or adversarial findings on a branch or worktree, especially when the target may have advanced since the reviewed revision."
---

# Apply review findings

A review is evidence about a snapshot. Re-establish the defect at the current
target before changing source or calling a finding resolved.

## Before editing

Read the repository's contract, checks and applicable prior solutions. Record
the review source, finding IDs, authors, reviewed commit SHA and target. If the
reviewed SHA or attribution is unavailable, record unknown and obtain evidence;
do not invent it or claim resolution.

Refresh the authoritative target and record the current SHA and PR/branch state.
In an offline review, declare the pinned local target and the unverified remote
state. A merged PR requires an authorized follow-up vehicle from the current
target; a surviving branch is insufficient. Verify write ownership and isolate
your work using the repository's normal mechanism. A competing or unknown owner
blocks overlapping writes. No particular coordination service is required.

## Per-finding decision

Re-read the cited implementation and trace moved code at the current SHA.
Choose one disposition with evidence and an attributable reason:

| Disposition | Use when | Evidence or next step |
|---|---|---|
| `fix` | Defect remains and repair is authorized | Reproduction, minimal repair, final checks and re-read |
| `already-satisfied` | Current behavior already meets the requirement | Trace the fix or move and verify the original failure case |
| `decline-non-defect` | Claim is contradicted or inapplicable to this target | Current code/contract evidence; explain disagreement |
| `operator/design-gated` | Decision exceeds authority or needs a design choice | Preserve behavior and name the required decision |
| `needs-new-vehicle` | Work targets a merged/retired branch or different surface | Identify the current target; no writes until ownership/authority is established |

Staleness is a reason to revalidate every finding, never a reason to discard one.
Preserve stronger current guards even if a literal suggestion would weaken them.
If a high-severity declined finding is raised independently again, settle it
with a focused reproduction and the controlling contract; revise the disposition
when the evidence changes. Prior solutions inform the probe, not its verdict.
If the first fix fails, compare bounded alternatives against the same defect
and normal-case controls, retaining rejected alternatives and their evidence.

## Verify and report

Keep a ledger with finding ID/author, reviewed SHA, current SHA, current location,
disposition, reason, commands/results, final verification SHA and remaining action.
Retain contradictory evidence. Missing or failed checks leave the item unverified.
For each fix, re-read the actual defect site after the change and run the
repository's relevant checks. Bind results to the tested bytes: before claiming
resolution at a commit SHA, run the checks on source materialized from that
immutable revision, including all relevant source inputs, without working-tree
overlays. A clean Git status alone is insufficient: index flags can hide changed
bytes. The worked ledger demonstrates reading the module from a Git object.
For an uncommitted repair, retain its patch/tree identity, label the result
local/uncommitted and do not claim HEAD contains the fix. This grants no commit
authority. Recheck target identity before reporting; if it advances, revalidate
affected evidence and record the new SHA. A commit or a stale-thread marker
alone is insufficient.

[The worked ledger](references/finding-ledger-example.md) covers current-valid,
stale, already-fixed, disputed, inapplicable and policy-gated findings. It also
shows a merged-branch change of vehicle. Evidence-backed dispositions may be
prepared locally. Posting replies or resolving remote review threads requires
separate explicit authorization; never silently mark unverified items resolved.

## Prerequisites and authority

Require access to reviewed/current source, review provenance, repository checks
and ownership evidence. Git is needed for commit identities; hosted PR state
requires authorized access to the host. Missing access remains a stated gap.
There are no required sibling skills, providers, private services or lock helpers.
This procedure grants no source-write, commit, push, merge, service, credential,
installation or external-communication authority.

Retain [provenance](PROVENANCE.md) and the [notice](LICENSE.orion) with a standalone copy.
