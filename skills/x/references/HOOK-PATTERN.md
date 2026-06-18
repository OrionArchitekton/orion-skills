# Auto-trigger pattern — a hook that NUDGES (never posts)

The autonomous half of `/x` is optional and environment-specific, so it ships as a
pattern to adapt rather than wired code. A hook is shell: it cannot run a skill or
post. It can only emit `additionalContext` to nudge the in-session model to
consider publishing — through the same redactor + cap + arm gates.

## Shape

A `Stop` hook that, when the system is ARMED and a fresh signal has surfaced this
session, nudges the model once (debounced) to consider a redacted post. Register
it in `settings.json` under `"hooks": { "Stop": [ … ] }`.

```bash
#!/usr/bin/env bash
# Stop hook — publish nudge. NUDGES only; never posts. Ships DISARMED.
trap 'exit 0' EXIT          # fail-OPEN: a never-emitted nudge must never block a Stop
set +e
command -v jq >/dev/null 2>&1 || exit 0

STATE="$HOME/.claude/state"
LOG="$STATE/publish-nudge.log"
ARM="$STATE/publishers-armed"
CORE="$HOME/.claude/skills/x/publish-core"
mkdir -p "$STATE" 2>/dev/null

INPUT=$(cat 2>/dev/null)
SID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
log(){ printf '%s session=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SID" "$1" >>"$LOG" 2>/dev/null; }

# Ship DISARMED: no arm flag -> emit nothing.
[ -e "$ARM" ] || { log "skipped reason=disarmed"; exit 0; }

# Debounce: at most one nudge per session.
DB="$STATE/publish-nudged-${SID}.json"
[ -e "$DB" ] && { log "skipped reason=already-nudged"; exit 0; }

# Respect the cap (read-only check).
python3 "$CORE/cap_ledger.py" check x >/dev/null 2>&1
[ $? -eq 4 ] && { log "skipped reason=at-cap"; exit 0; }

# (Plug in your own "is there a fresh signal?" check here — see below.)
# If nothing fresh: log "skipped reason=no-fresh-signals"; exit 0

printf '{"at":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$DB" 2>/dev/null
log "fired"
CTX="[publish] A fresh, genericizable lesson surfaced this session. If it is useful to others, run /x on a REDACTED, private-info-free version. The redactor is fail-closed (abstain beats leak) and the daily cap applies. Skip anything not publishable."
jq -n --arg ctx "$CTX" '{hookSpecificOutput:{hookEventName:"Stop",additionalContext:$ctx}}'
exit 0
```

## Signal discovery (the "is there a fresh signal?" part)

What counts as a publishable signal is yours to define. A simple version: a note
file written in the last N hours that you haven't already acted on. Track what
you've published in a small JSON dedup set under `~/.claude/state/` so the same
signal isn't surfaced twice — and, on a shared/multi-session box, remember that a
recency window over a shared notes directory will surface OTHER sessions' notes
too. Only publish what the current session actually produced and can genericize.

## Rails (don't skip these)

- **Fail-open** (`trap 'exit 0'; set +e`, never `set -e`/`exec`): a broken hook
  must not block a Stop.
- **Log to a file, never `/dev/null`** — a silent probe failure must not look like
  success.
- **Disarmed by default** — the arm-flag check is the first gate; with no flag the
  hook emits nothing.
- The hook nudges; the *model* runs `/x`, which still enforces redactor + cap + arm.
