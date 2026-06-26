# Enforcer + dispatch — runtime mechanics

Depth for `tdd-loop/SKILL.md`. The SKILL.md is the contract; this file is the mechanics.
The gates bind to artifacts regardless of which substrate — independent subagents, a
deterministic workflow runner, or inline sequential work — you drive the loop with.

## Substrate (use what your harness has)

- **Independent subagents** — dispatch each slice and each reviewer as a subagent.
- **A deterministic workflow / parallel-agent runner** — use it for the per-slice and
  per-review fan-out.
- **Inline** — run sequentially.

Never assume a particular orchestrator exists. The gates below are substrate-independent.

> The capture blocks below intentionally inspect non-zero exit codes (`cmd; rc=$?`), so
> they assume `errexit` (`set -e`) is OFF — the default for a normal shell / agent Bash
> call. If you paste them into a `set -e` script, the script would abort at the failing
> command *before* the guard runs (fail-OPEN). Wrap with `set +e` / `set -e`, or use
> `if ! cmd; then rc=$?; else rc=0; fi`, so the gate still fires.

## Computing the diff the reviewers actually see (Review-ran gate)

```bash
# detect the base branch — repo PR convention first, else the remote's default HEAD
BASE="$(git remote show origin | sed -n 's/.*HEAD branch: //p')"
[ -n "$BASE" ] && [ "$BASE" != "(unknown)" ] || {
  echo "GATE FAIL: could not detect base branch (origin HEAD unset / offline). Try: git remote set-head origin -a"; exit 1; }
# resolve against the remote-tracking ref so a fresh worktree (no LOCAL base branch) still works
git rev-parse --verify --quiet "origin/$BASE" >/dev/null || {
  echo "GATE FAIL: base ref origin/$BASE not found (detached? unfetched?)"; exit 1; }
git diff "origin/$BASE"...HEAD > /tmp/tdd-loop-review.diff
test -s /tmp/tdd-loop-review.diff || { echo "GATE FAIL: diff is genuinely empty (no changes vs origin/$BASE)"; exit 1; }
```

Feed `/tmp/tdd-loop-review.diff` (or the explicit changed-file list) to each reviewer. An
empty/clean reviewer result on a NON-empty diff is a GATE FAILURE — re-dispatch with the
diff actually attached.

## Reviewer dispatch (diff-fed; roles, not products)

Dispatch the same computed diff to each role; collect findings; severity-grade.

- **SECURITY role** — the six named bug classes (fail-open, path traversal, injection,
  secret-spill, auditability, ID collisions). This is the *pre-PR* security engine — not
  a plan-level review and not a PR-scoped review that de-scopes security.
- **ADVERSARIAL / CORRECTNESS role** — logic, edge cases, state, error propagation,
  abuse / composition / cascade failures.

If you have no reviewer agents, run each role's checklist against the diff yourself in a
dedicated pass — the gate is that the *computed diff* was actually reviewed.

Dispatch prompt skeleton (each reviewer):

```text
Review ONLY this diff (attached). Return findings, each with a severity
(BLOCKING|WARNING|INFO) and concrete evidence (file:line + the failing scenario).
Do not review unchanged code. If the diff is empty, say so — do not return "clean".
<diff or changed-file list here>
```

Treat any BLOCKING as a hard gate: fix, re-run the full suite, re-review. Loop until
zero BLOCKING findings remain.

## Secret gate (your scanner can fail OPEN — re-assert a clean report)

Using [gitleaks](https://github.com/gitleaks/gitleaks) as the example scanner:

```bash
# `gitleaks git --staged` is the current form (replaces the deprecated `protect --staged`)
gitleaks git --staged --redact --report-path /tmp/tdd-loop-secrets.json; rc=$?
# rc 0 = clean; rc 1 = leak found OR scan error (BOTH block — inspect the report + stderr to tell apart);
# any other rc / missing report = scanner error => NOT green (a commit hook would fail OPEN here)
test -f /tmp/tdd-loop-secrets.json || { echo "GATE FAIL: no secrets report produced"; exit 1; }
[ "$rc" -eq 0 ] || { echo "GATE FAIL: scanner rc=$rc (leak or scan error)"; exit 1; }
```

Never bypass the commit hook past a real finding. `--redact` keeps secret values out of
stdout — the secret-to-stdout prohibition applies to the scanner's own output too.

## Completion gate (full suite LAST, capture the exit code)

```bash
<repo-declared test command> ; echo $? > /tmp/tdd-loop-suite.rc
RC="$(cat /tmp/tdd-loop-suite.rc)"
[ "$RC" -eq 0 ] || { echo "GATE FAIL: suite rc=$RC"; exit 1; }
```

Quote the captured `RC` in the completion claim. A stale or absent capture = not green.
Run the FULL suite as the LAST action before the PR — not "tests passed earlier".

## Backflow rule

An unexpectedly-failing test (a slice that was green going red, or a RED that fails for
the WRONG reason) routes to root-cause investigation — ≥2 hypotheses, verified against
live state, no single-hypothesis lock-in — never a forward speculative patch.
