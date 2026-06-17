---
name: readonly
description: Enter or leave a structural READ-ONLY session mode for audit/research/census work. Sets the marker the pretooluse-readonly hook enforces, which then DENIES every file-mutating tool until cleared. Operator-invoked.
disable-model-invocation: true
---

# Read-Only Mode

Structural read-only rail for audit / research / census work. Activating it makes
the `pretooluse-readonly` PreToolUse hook DENY every file-mutating tool
(Edit/Write/MultiEdit/NotebookEdit) for the rest of the session — until cleared.

It is the sister of `scope-guard`: scope-guard constrains *where* you may write;
read-only mode constrains *whether* you may write at all. Same proven mechanism —
an opt-in, fail-open session marker + a PreToolUse `permissionDecision: deny`.

## When to use

- An explicit audit / research / read-only census where NO file should change.
- Backstopping read-only subagents with a hard structural rail, not just
  behavioral discipline (the PreToolUse payload carries no subagent identity, so
  the marker is session-global — enter read-only, do the read-only work, clear).

## Activation — the marker lifecycle

The enforcement hook is INERT until the marker is set. Use a small helper to
manage the marker; do not hand-write the marker JSON:

```bash
~/.claude/scripts/readonly-mode.sh on  "audit: <what>"   # enter read-only
~/.claude/scripts/readonly-mode.sh status                # check
~/.claude/scripts/readonly-mode.sh off                   # leave (ALWAYS clear)
```

`on` writes `~/.claude/state/readonly.json` `{"active":true,"reason":...}`; the
hook then denies writes citing that reason. `off` removes it (writes allowed
again). No marker = no enforcement (safe default).

> This skill is the *contract*; the marker helper and the `pretooluse-readonly`
> hook are the *mechanism*. Wire a PreToolUse hook that returns
> `permissionDecision: deny` for mutating tools whenever the marker file is
> `active`. Without that hook the marker is inert (see below).

## Discipline

- Set BEFORE the read-only work; clear AFTER — prefer clearing in the same turn
  (or a trap) so a crash doesn't strand the session, and others, read-only. The
  marker is a file on disk: a stranded `active` marker blocks writes in the NEXT
  session too until someone runs `off`.
- Read scope is unrestricted; only writes are blocked.
- No-hook environments: the hook is absent — apply read-only discipline
  manually (the marker is a no-op there).

## What this does NOT do

- Does not block reads.
- Does not distinguish subagent from main thread (the marker is session-global).
- Does not persist any allow/deny audit; it is a single on/off gate.
