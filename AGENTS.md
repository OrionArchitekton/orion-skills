# AGENTS.md - orion-skills

## Repo Role

`orion-skills` is an open-source library of original agent skills for
disciplined coding-agent workflows: finishing work, preserving scope, preparing
PRs, capturing learnings, and writing executable plans.

## Boundaries

- Owns skill source folders, skill docs, tests, and public project docs.
- Does not own local `~/.claude/skills`, `~/.codex/skills`, private estate
  skill installs, or plugin marketplaces.
- Keep skills portable and workflow-focused. Do not add credentials, local
  estate paths, or private rollout details to public skill content.

## Authority Order

1. `/home/orion/src/orion-estate/platform/orion-estate-audit/AGENTS.md`
2. `README.md`
3. `skills/`, `docs/`, and tests
4. Public contribution and code-of-conduct docs

## Validation

```bash
python -m pytest
```

For docs-only changes, run `git diff --check` at minimum.
