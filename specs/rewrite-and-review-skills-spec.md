# Rewrite guards and review findings

## Selected behavior and boundaries

Two standalone procedures help a coding agent preserve an existing safety
property during a rewrite and adjudicate snapshot-bound review findings.
They provide judgment and evidence requirements, not an automated safety
verdict. They require no provider, private service, installed sibling skill or
lock helper. Repository access, a shell, Git for revision identity and the
consumer repository's checks are explicit prerequisites for the worked examples.
Neither procedure grants mutation, publication, deployment or review-thread
authority. Missing evidence remains unresolved.

Source adaptation rights and an accountable maintenance owner must be confirmed
before release acceptance. Local preparation does not satisfy either condition.
Collection release holds and unrelated policy decisions remain outside scope.

## Terminology

- A **guard** enforces a safety property before a protected effect.
- **Binding evidence** demonstrates that the guard controls the actual effect,
  including denial with no effect on the negative path.
- A **finding** is a hypothesis bound to a reviewed revision, location and author.
- A **disposition** is an attributable, evidence-backed decision for one finding.
- The five dispositions are `fix`, `already-satisfied`, `decline-non-defect`,
  `operator/design-gated` and `needs-new-vehicle`. Stale describes evidence,
  not a sixth disposition and not permission to discard a finding.

## Scenarios, in dependency order

### 1. Preserve a guard across a rewrite

A maintainer compares the original guarded operation with a candidate rewrite.
The agent records both revisions, inventories each guard, traces every entry
point to the protected effect, and records preserved, moved, superseded or
unresolved status with evidence. A dropped guard or a guard moved after the
effect fails acceptance even when textual guard counts match. A guard moved
into a shared entry wrapper is acceptable only when every affected entry point
denies the prohibited case before any effect, while the allowed case still works.
An unavailable source or failed verifier never becomes a clean safety verdict.

Acceptance: a synthetic tenant-scoped write demonstrates original success,
denial without a write, a dropped guard, an unsafe move and a safe move. The
same negative-path check rejects both unsafe candidates. Happy-path success and
equal regex counts are explicitly insufficient.

### 2. Adjudicate findings at the current revision

An agent receives a review against an earlier revision. Before changing source,
it verifies the current target, work vehicle and ownership, then re-reads every
finding at the current revision. It retains the author, reviewed revision,
current revision, evidence, disposition and unresolved action per finding.
A valid defect receives a minimal authorized fix; an already-fixed defect gets
current evidence; a stale location is traced to its current implementation;
a disputed claim gets a reason tied to the controlling contract; an inapplicable
target gets evidence instead of an invented fix. Missing attribution or an
unknown reviewed revision is recorded as unknown and blocks a resolution claim.

Acceptance: one offline synthetic Git history supports current-valid, stale,
already-fixed, disputed, inapplicable and design-gated findings. After a real fix,
the agent re-reads the defect and runs relevant checks at the final revision.
If the target advances again, affected findings are revalidated. An old finding
never authorizes weakening a stronger current invariant, pushing a merged branch,
posting a reply or resolving a remote review thread.

Commit-specific evidence must come from the named immutable source, materialized
without working-tree overlays for every relevant source input. A clean Git
status cannot establish byte identity. A passing uncommitted repair
cannot establish that HEAD contains the repair, even if staged. Local uncommitted
proof retains its patch/tree identity and is labeled accordingly; this creates
no authority to commit. The synthetic scenario runs the probe on Git-object
source despite unstaged/staged/untracked files and index flags that conceal
local repairs. Unknown revisions, missing source and Git errors block proof.

### 3. Use either procedure independently

A consumer copies one skill directory to a temporary location with no other
skills installed. All mandatory references and notices are inside that directory;
its worked scenario can be exercised offline using synthetic inputs. Any required
consumer tools are explicit. Private paths, endpoints, credentials and history
are absent. No heuristic guard detector, locking implementation or runtime service
is bundled.

Acceptance: temporary standalone copies resolve local references and retain
their provenance and notice files. Reviewers can apply each procedure to the
scenarios without a private dependency. Unconfirmed rights or maintenance
ownership remain release blockers even if technical checks pass.

## Test seam decision

Use the procedure's evidence output as the highest useful seam: worked guard
and finding ledgers reviewed against executable, offline Python/Git scenarios.
The focused suite executes the guard example with a side-effect recorder and
builds a synthetic reviewed/current history for finding adjudication. It also
checks standalone-copy closure. Human/agent application review verifies judgment
and authority boundaries; string-presence tests cannot establish that an agent
will follow prose. No production analyzer or generic workflow engine is added.

Git fixture discovery stops at each explicit temporary root. Inherited Git
repository/worktree overrides are cleared. Tests use isolated home/config/temp
directories outside operator-state repositories and never contact a provider.
