---
name: pre-pr
description: Repo-contract-aware preflight plus advisory diff review before creating any PR. Detects base branch, runs repo-local checks, scans for secrets, and reports findings with severity levels.
---

# Pre-PR Verification

Structured verification pass before creating any PR. Run this BEFORE `gh pr create` or `git push` for a new PR.

## Step 1: Detect base branch

First check for repo-local PR convention. Look for a declared base branch in:

1. Repo-local `CLAUDE.md` or `AGENTS.md` (some repos use a non-`main` default branch — e.g. `develop`, `release`, or a project-specific trunk; never assume `main`)
2. `.claude/pr-config.json` if it exists (field: `baseBranch`)

If no repo-local convention is found, fall back:

```bash
git remote show origin | grep 'HEAD branch' | sed 's/.*: //'
```

Report which source determined the base branch.

## Step 2: Verify working branch

```bash
CURRENT=$(git branch --show-current)
```

Check that the current branch is NOT the base branch or any protected branch declared in repo-local config. If it is, report as BLOCKING.

## Step 3: Run repo-local preflight

Check for and execute repo-local preflight in this order:

1. `.claude/hooks/pre-commit.sh` — if present and executable, run it
2. Repo-declared CI contract commands from `CLAUDE.md` or `AGENTS.md` (e.g., `pytest`, `npm test`, `bun test`)

If no repo-local preflight exists, report as INFO: "No repo-local preflight found."

## Step 4: Secret scan

Scan the diff against the base branch for credential patterns:

```bash
git diff <base-branch>...HEAD
```

Patterns to check (advisory — not a policy gate):
- `password`, `secret`, `token`, `api_key`, `apikey`, `private_key`, `auth_token` followed by assignment with a string value
- Base64-encoded strings longer than 40 characters that look like keys
- Your secrets manager's documented token prefixes (most managers publish a recognizable prefix for service/personal tokens — add yours here)

If hits are found, report as BLOCKING (secrets are the one advisory pattern that blocks).

## Step 5: Repo-local optional patterns

If `.claude/pr-config.json` exists and declares additional scan patterns:

```json
{
  "scanPatterns": [
    { "pattern": "console\\.log", "severity": "WARNING", "label": "Debug logging" },
    { "pattern": "TODO|FIXME|HACK", "severity": "WARNING", "label": "Shipping markers" }
  ]
}
```

Run each pattern against the diff and report at the declared severity.

If no repo-local patterns are configured, skip this step.

## Step 6: File inventory

List all changed files with a one-line rationale:

```bash
git diff --stat <base-branch>...HEAD
```

For each file, state what changed and why (based on the diff content and commit messages).

## Output Format

```
## Pre-PR Report

**Base branch:** <branch> (source: <repo-local | origin default>)
**Current branch:** <branch>
**Files changed:** <count>

### BLOCKING
- [secrets found, protected-branch violation, preflight failure]

### WARNING
- [advisory findings: TODOs, debug markers, large diffs, repo-local patterns]

### INFO
- [file inventory, branch state, preflight status]

### Result: CLEAR | ISSUES (<N> blocking, <N> warning)
```
