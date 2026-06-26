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

> The capture blocks below use `if cmd; then rc=0; else rc=$?; fi` so they record a
> non-zero exit AND survive `errexit` (`set -e`) — a bare `cmd; rc=$?` would abort at the
> failing command before the guard runs (fail-OPEN). Avoid `if ! cmd; then rc=$?`: in the
> negated `then` branch `$?` is the status of `! cmd` (i.e. `0` when `cmd` failed), which
> silently captures a failure as success. Gate artifacts use `mktemp` (private, 0600,
> collision-free) rather than predictable `/tmp` paths — the diff and report can hold
> sensitive content.

## Computing the diff the reviewers actually see (Review-ran gate)

```bash
# base branch: honor a repo-declared PR base (AGENTS.md / CLAUDE.md / .claude) if you have one;
# else resolve the remote default — local symref first (fast, offline-safe), then the network call.
BASE="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
[ -n "$BASE" ] || BASE="$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')"
[ -n "$BASE" ] && [ "$BASE" != "(unknown)" ] || {
  echo "GATE FAIL: could not detect base branch (origin HEAD unset / offline). Try: git remote set-head origin -a"; exit 1; }
git rev-parse --verify --quiet "origin/$BASE" >/dev/null || {
  echo "GATE FAIL: base ref origin/$BASE not found (detached? unfetched?)"; exit 1; }
DIFF="$(mktemp)"   # private (0600) + collision-free; the diff can hold sensitive code
git diff "origin/$BASE"...HEAD > "$DIFF"
test -s "$DIFF" || { echo "GATE FAIL: diff is genuinely empty (no changes vs origin/$BASE)"; rm -f "$DIFF"; exit 1; }
```

Feed `$DIFF` (or the explicit changed-file list) to each reviewer. An
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
REPORT="$(mktemp)"   # fresh, private path — no stale or world-readable report file
# `if cmd; then rc=0; else rc=$?` captures the status AND survives `set -e`
if gitleaks git --staged --redact --report-path "$REPORT"; then rc=0; else rc=$?; fi
# rc 0 = clean; rc 1 = leak found OR scan error (BOTH block — inspect "$REPORT" + stderr to tell apart);
# any other rc / missing report = scanner error => NOT green (a commit hook would fail OPEN here)
test -f "$REPORT" || { echo "GATE FAIL: no secrets report produced"; exit 1; }
[ "$rc" -eq 0 ] || { echo "GATE FAIL: scanner rc=$rc (leak or scan error)"; exit 1; }
```

Never bypass the commit hook past a real finding. `--redact` keeps secret values out of
stdout — the secret-to-stdout prohibition applies to the scanner's own output too.

## Completion gate (full suite LAST, capture the exit code)

```bash
RCFILE="$(mktemp)"   # fresh file each run — never read a stale capture
# `if cmd; then ... else ...` captures the suite status AND survives `set -e`
if <repo-declared test command>; then echo 0 > "$RCFILE"; else echo $? > "$RCFILE"; fi
RC="$(cat "$RCFILE")"
[ "$RC" -eq 0 ] || { echo "GATE FAIL: suite rc=$RC"; exit 1; }
```

Quote the captured `RC` in the completion claim. A stale or absent capture = not green.
Run the FULL suite as the LAST action before the PR — not "tests passed earlier".

## Backflow rule

An unexpectedly-failing test (a slice that was green going red, or a RED that fails for
the WRONG reason) routes to root-cause investigation — ≥2 hypotheses, verified against
live state, no single-hypothesis lock-in — never a forward speculative patch.
