# Synthetic finding ledger

This offline example uses revision labels R (reviewed), C (current) and F (final),
not pretend commit SHAs. In real use obtain full identities with `git rev-parse`
and inspect exact source with `git show`. Author for every finding is
`fixture-reviewer`; target is a local synthetic service. Remote state is unknown.
No thread mutation or posting is authorized. All command shapes below require
Git and Python 3 plus an authorized local consumer checkout.

The service charges an amount, reads a tenant-scoped item and evaluates a policy.
Its contract requires charges in [0, 100], tenant equality before returning an
item, and denial of unknown policies. The limit is operator-selected; changing
it has no authorization in this task. The optional adapter is absent.

| ID | Reviewed at R | Observed at C | Disposition / attributable reason | Evidence before closure |
|---|---|---|---|---|
| F1 | Charge 101 succeeds | Still appends 101 | `fix`: fixture-reviewer's overflow defect remains | At F, 101 raises with no append; 100 still appends once |
| F2 | `fetch_item` lacks tenant isolation | Renamed `read_item` checks equality | `already-satisfied`: trace the moved implementation | At C and F, cross-tenant read raises; same-tenant read returns item |
| F3 | Charge -1 succeeds | Negative amounts already rejected | `already-satisfied`: behavior fixed since R | At C and F, -1 raises with zero appends |
| F4 | Reviewer asks for unknown-policy fallback | Current policy raises on unknown | `decline-non-defect`: fallback conflicts with the denial contract | At C and F, unknown raises and allow succeeds; retain disagreement |
| F5 | Optional adapter needs validation | Adapter and its execution path absent | `decline-non-defect`: inapplicable to this target | Inspect current source and target configuration; do not generalize to other targets |
| F6 | Raise configured limit to 200 | Limit remains 100 | `operator/design-gated`: policy change exceeds authority | Retain existing limit; operator decision remains open |

For each row, a real ledger records the full reviewed/current/final SHAs, author,
current symbol, exact probe and observed result. F1 can be reported fixed only
after running and re-reading F. F2/F3 are verified already-satisfied, not repairs
performed by the applying agent. F4/F5 retain the reason for declining; F6 stays
open. If R or its author cannot be established, preserve unknown provenance and
avoid a verified-resolution claim.

For example, a consumer's focused negative probe for F1 has this shape:

```python
effects = []
try:
    charge(101, effects)
except ValueError:
    assert effects == []
else:
    raise AssertionError("overflow accepted")
charge(100, effects)
assert effects == [100]
```

Run the same probe against C and F: failure at C reproduces the finding; success
at F supports its repair. Recheck the target SHA afterward. If the target has
advanced, inspect the affected behavior again before claiming it is resolved.

For a commit-specific claim, set and export `VERIFIED_SHA` to the full commit
being tested and `TMPDIR` to an explicit temporary root outside the checkout.
This example's entire source seam is one module. Materialize that module from
the Git object, not the working tree:

```sh
: "${TMPDIR:?Set an explicit temporary root outside the checkout}"
test -n "${VERIFIED_SHA:-}" || exit 1
proof_commit=$(git --no-replace-objects rev-parse --verify --end-of-options "${VERIFIED_SHA}^{commit}") || exit 1
test "$proof_commit" = "$VERIFIED_SHA" || exit 1
proof_dir=$(mktemp -d "$TMPDIR/review-proof-XXXXXX") || exit 1
git --no-replace-objects show "$proof_commit:service.py" > "$proof_dir/service.py" || exit 1
printf '%s\n' "$proof_dir/service.py"
```

Run the Python probe against the returned module path in an isolated process,
not against an import from the original checkout. At C it still fails even if
local repaired bytes are staged or hidden by `assume-unchanged`/`skip-worktree`.
Object reads explicitly disable replacement refs so a different commit cannot
be substituted for the named SHA.
At F it passes. An unknown SHA, missing module or Git error blocks proof; never
fall back to working-tree source. The shell recipe alone is not a behavioral
test. It grants no commit authority.

For a larger consumer, materialize every relevant source input using its approved
immutable-source method and record the check environment/dependencies. This
one-module example does not prove a multi-module application or live PR state.
Uncommitted `service.py` can pass while the named Git object still accepts
overflow; an empty Git status can hide that difference. Retain the uncommitted
patch/tree identity and label that proof local until an authorized immutable
revision contains it. Recheck the current target before reporting: a passing
historical commit does not establish the behavior of a newer target.

If the reviewed PR has merged, record `needs-new-vehicle` for the repair work
before editing. Keep the per-finding substantive decisions above as evidence,
and prepare an authorized follow-up from the current target. Do not push the
surviving merged branch. Native host access is necessary to verify live PR state;
offline Git history alone does not establish that state.

These are worked decisions, not an automatic adjudicator. The repository's
synthetic fixture suite validates their behavioral evidence with actual local
Git revisions. Human or agent application review still judges whether the
evidence supports a disposition. No remote review thread is changed.
