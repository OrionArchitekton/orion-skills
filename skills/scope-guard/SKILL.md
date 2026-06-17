---
name: scope-guard
description: Session boundary discipline contract. Establishes and self-audits write scope for infrastructure and multi-file work. Behavioral discipline — not a filesystem interceptor.
---

# Scope Guard

Session boundary discipline. Constrains which files Claude may write to during a session. This is a behavioral contract — it shapes how Claude operates through self-imposed discipline. It is NOT a filesystem-level interceptor and cannot guarantee hard prevention of every out-of-scope edit.

## Activation

When invoked, collect these parameters:

1. **Scope description** — what this session is doing (one sentence)
2. **Allowed write paths** — directories and/or file globs that may be modified
3. **Excluded areas** — directories and/or file globs that must NOT be modified

If the user does not provide explicit paths, attempt to derive defaults from:

1. Repo-local `CLAUDE.md` boundary declarations
2. Repo-local `AGENTS.md` boundary notes (e.g., "this repo owns X, not Y")
3. If neither exists, ask the user to declare write scope explicitly

## Deterministic enforcement (Claude Code hook)

In Claude Code the **`scope-guard-enforce`** PreToolUse hook makes this contract
self-enforcing. On activation, after collecting the scope, **write the session
marker** so the hook can block out-of-scope writes:

```bash
mkdir -p ~/.claude/state && cat > ~/.claude/state/scope-guard.json <<'JSON'
{"active": true,
 "scope": "<one-sentence scope>",
 "allowed": ["/abs/path/or/glob/**", "..."],
 "excluded": ["/abs/path/to/protect", "..."]}
JSON
```

The hook then DENIES any Edit/Write whose target is outside `allowed` or inside
`excluded`. **Clear it** when the scope changes or the session ends:
`rm -f ~/.claude/state/scope-guard.json`. No marker = no enforcement (the hook is
inert by default — safe). **No-hook environments:** the hook is absent, so
the self-check below IS the enforcement — apply it manually before each write.

## Scope Rules

**Read scope:** Unrestricted. Reading broadly for context is always allowed.

**Write scope:** Constrained to declared allowed paths. Before any file write (Edit, Write tool calls), self-check:

1. Is the target file within the declared allowed write paths?
2. Is the target file NOT in the excluded areas?
3. If both pass — proceed with the write.
4. If either fails — STOP. Do not write. Report:

```
## Scope Violation Detected

Target file: <path>
Declared write scope: <allowed paths>
Excluded areas: <excluded paths>
Reason: <which rule was violated>

Stopping. This file is outside declared write scope.
To proceed, explicitly expand the scope or confirm this exception.
```

## Session Audit

At session end, or when `/pre-pr` is invoked, or when the user asks for a scope audit, produce:

```
## Scope Audit

**Session scope:** <description>
**Allowed write paths:** <paths>
**Excluded areas:** <paths>

| File | Action | In Scope? |
|------|--------|-----------|
| path/to/file.py | modified | yes |
| path/to/other.py | inspected (read-only) | n/a |
| path/to/edge.py | modified | WARNING — near boundary |
```

Distinguish `modified` (Edit/Write was used) from `inspected` (Read only).

## Honesty Note

This skill operates as self-imposed discipline within Claude's reasoning. If paired with a hook that validates edited file paths against declared scope, enforcement becomes mechanical. Without that hook, it relies on Claude's adherence to the contract. Do not claim or imply filesystem-level enforcement.

## What this skill does NOT do

- Does not intercept filesystem writes mechanically
- Does not prevent reads of any file
- Does not hardcode repo-specific paths globally
- Does not depend on any specific internal package
