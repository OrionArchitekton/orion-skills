---
name: readonly
description: Enter or leave a structural READ-ONLY session mode for audit/research/census work. Sets the marker the pretooluse-readonly hook enforces, which then DENIES the file-editing tools (Edit/Write/MultiEdit/NotebookEdit) until cleared. Shell writes via Bash are outside the matcher. Operator-invoked.
disable-model-invocation: true
---

# Read-Only Mode

Structural read-only rail for audit / research / census work. Activating it makes
the `pretooluse-readonly` PreToolUse hook DENY the file-editing tools
(Edit/Write/MultiEdit/NotebookEdit) for the rest of the session, until cleared.
Writes issued through the `Bash` tool are outside that matcher; see
[What this does NOT do](#what-this-does-not-do) before relying on this for an
airtight audit.

It is the sister of `scope-guard`: scope-guard constrains *where* you may write;
read-only mode constrains *whether* you may write at all. The marker is opt-in,
so no marker means no enforcement, but once the marker exists the gate is
fail-CLOSED: anything it cannot evaluate is denied.

## When to use

- An explicit audit / research / census where the file-editing tools should be
  structurally unavailable rather than merely discouraged.
- Backstopping read-only subagents with a hard structural rail, not just
  behavioral discipline (the PreToolUse payload carries no subagent identity, so
  the marker is session-global, enter read-only, do the read-only work, clear).

## Activation: the marker lifecycle

The enforcement hook is INERT until the marker is set. Use a small helper to
manage the marker; do not hand-write the marker JSON:

Paths below are written against the INSTALLED skill directory, because that is
where these run from in practice: the working directory is normally your project,
not this repo, so a bare `skills/readonly/...` path would not resolve. Set `RO`
once and the rest of this document works verbatim either way:

```bash
RO=~/.claude/skills/readonly          # installed
# RO=./skills/readonly                # or, working inside a clone of this repo

"$RO"/scripts/readonly-mode.sh on  "audit: <what>"   # enter read-only
"$RO"/scripts/readonly-mode.sh status                # check
"$RO"/scripts/readonly-mode.sh off                   # leave (ALWAYS clear)
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
               "command": "$HOME/.claude/skills/readonly/hooks/pretooluse-readonly.sh" } ]
} ] } }
```

Verify it on your own machine before trusting it:

```bash
python3 "$RO"/selftest.py    # exit 0 = every case behaved
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

**It does not cover shell writes, and that is the boundary worth knowing.** The
matcher registers the hook on `Edit|Write|MultiEdit|NotebookEdit`. `Bash` is a
separate tool, so `rm`, `sed -i`, `cp`, `> file`, or any script run through it
mutates files without this hook ever being consulted. Read the guarantee as
"the file-editing tools are blocked", not "nothing on disk can change".

Closing that gap fully is not a matter of adding `Bash` to the matcher and
moving on, because the honest options both cost something:

- Add `Bash` to the matcher and deny it outright while the marker is active.
  Airtight, but it also blocks `ls`, `grep`, `git log`, and the rest of the
  read-only work the mode exists to support.
- Match on command shape (`rm`, `>`, `-i`) and deny only those. This is a
  tripwire, not a wall: an alias, `eval`, a wrapper script, or the same binary
  reached by another path walks straight past a string match, and a matcher that
  finds nothing has established only that nothing matched.

The default here is the narrow, honest one. If your audit must be airtight
against shell writes, take the first option deliberately and accept that reads
through `Bash` go with it.

Also:

- Does not block reads.
- Does not distinguish subagent from main thread (the marker is session-global).
- Does not persist any allow/deny audit; it is a single on/off gate.
- Does not survive a marker someone hand-edits into an unparseable state; that
  fails closed and blocks writes until fixed, which is deliberate but will look
  like a bug if you are not expecting it (`readonly-mode.sh status` says so).
