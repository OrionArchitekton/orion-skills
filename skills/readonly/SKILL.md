---
name: readonly
description: Enter or leave a structural READ-ONLY session mode for audit/research/census work. Sets the marker the pretooluse-readonly hook enforces, which then DENIES every file-mutating tool until cleared. Operator-invoked.
disable-model-invocation: true
---

# Read-Only Mode

Structural read-only rail for audit / research / census work. Activating it makes
the `pretooluse-readonly` PreToolUse hook DENY every file-mutating tool
(Edit/Write/MultiEdit/NotebookEdit) for the rest of the session, until cleared.

It is the sister of `scope-guard`: scope-guard constrains *where* you may write;
read-only mode constrains *whether* you may write at all. Same proven mechanism, an opt-in,
fail-open session marker + a PreToolUse `permissionDecision: deny`.

## When to use

- An explicit audit / research / read-only census where NO file should change.
- Backstopping read-only subagents with a hard structural rail, not just
  behavioral discipline (the PreToolUse payload carries no subagent identity, so
  the marker is session-global, enter read-only, do the read-only work, clear).

## Activation: the marker lifecycle

The enforcement hook is INERT until the marker is set. Use a small helper to
manage the marker; do not hand-write the marker JSON:

```bash
skills/readonly/scripts/readonly-mode.sh on  "audit: <what>"   # enter read-only
skills/readonly/scripts/readonly-mode.sh status                # check
skills/readonly/scripts/readonly-mode.sh off                   # leave (ALWAYS clear)
```

`on` writes `~/.claude/state/readonly.json` `{"active":true,"reason":...}`; the
hook then denies writes citing that reason. `off` removes it (writes allowed
again). No marker = no enforcement (safe default). Set `READONLY_MARKER` to
relocate the marker.

## Mechanism (shipped, not left to the reader)

Both halves ship in this repo and are executable:

| File | Role |
|---|---|
| `skills/readonly/hooks/pretooluse-readonly.sh` | PreToolUse hook that returns `permissionDecision: deny` |
| `skills/readonly/scripts/readonly-mode.sh` | marker lifecycle (`on` / `off` / `status`) |
| `skills/readonly/selftest.py` | fires the real hook and proves it denies |

Register the hook on the file-mutating tools:

```json
{ "hooks": { "PreToolUse": [ {
  "matcher": "Edit|Write|MultiEdit|NotebookEdit",
  "hooks": [ { "type": "command",
               "command": "$HOME/path/to/skills/readonly/hooks/pretooluse-readonly.sh" } ]
} ] } }
```

Verify it on your own machine before trusting it:

```bash
python3 skills/readonly/selftest.py    # exit 0 = every case behaved
```

## Fail-closed behavior

The hook is opt-in but not forgiving once opted in:

- **Marker absent**: inert, writes allowed. Read-only mode was never entered.
- **Marker present and `{"active": true}`**: writes denied.
- **Marker present and `{"active": false}`**: writes allowed (explicit clear).
- **Marker present but unreadable, empty, malformed, a directory, or `active`
  holding any other value**: writes **denied**.

That last row is the point. Under the Claude Code PreToolUse contract only
`exit 0` with a `deny` decision, or `exit 2`, actually blocks; every other
non-zero exit lets the tool run. A gate that crashes on unexpected input
therefore fails open on exactly the input most likely to be hostile, so once the
marker exists every evaluation failure is routed to `exit 2`. "I could not tell"
is treated as "block", which is what fail-closed means operationally.

## Discipline

- Set BEFORE the read-only work; clear AFTER; prefer clearing in the same turn
  (or a trap) so a crash doesn't strand the session, and others, read-only. The
  marker is a file on disk: a stranded `active` marker blocks writes in the NEXT
  session too until someone runs `off`.
- Read scope is unrestricted; only writes are blocked.
- No-hook environments: the hook is absent, apply read-only discipline
  manually (the marker is a no-op there).

## What this does NOT do

- Does not block reads.
- Does not distinguish subagent from main thread (the marker is session-global).
- Does not persist any allow/deny audit; it is a single on/off gate.
