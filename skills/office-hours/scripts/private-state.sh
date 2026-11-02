#!/usr/bin/env bash
# Print the private state directory only after Git proves the profile is ignored.
set -eu
umask 077
fail() { printf '%s\n' "office-hours: $*; skip private state writes" >&2; exit 1; }
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || fail 'a Git worktree is required'
EXCLUDE=$(git -C "$ROOT" rev-parse --git-path info/exclude) || fail 'cannot resolve exclusion file'
case "$ROOT$EXCLUDE" in *$'\n'*|*$'\r'*) fail 'invalid Git path' ;; esac
[ -n "$ROOT" ] || fail 'empty worktree path'
[ -n "$EXCLUDE" ] || fail 'empty exclusion path'
case "$EXCLUDE" in /*) ;; *) EXCLUDE="$ROOT/$EXCLUDE" ;; esac
[ ! -L "$EXCLUDE" ] || fail 'exclusion file is a symlink'
[ ! -e "$EXCLUDE" ] || [ -f "$EXCLUDE" ] || fail 'exclusion path is not a regular file'
STATE_ROOT="$ROOT/.office-hours"
[ ! -L "$STATE_ROOT" ] || fail 'state directory is a symlink'
[ ! -L "$STATE_ROOT/builder-profile.jsonl" ] || fail 'profile is a symlink'
[ ! -L "$STATE_ROOT/builder-journey.md" ] || fail 'journey is a symlink'
[ ! -L "$STATE_ROOT/analytics" ] || fail 'analytics directory is a symlink'
[ ! -L "$STATE_ROOT/analytics/skill-usage.jsonl" ] || fail 'analytics file is a symlink'
[ ! -L "$STATE_ROOT/analytics/spec-review.jsonl" ] || fail 'review metrics file is a symlink'
[ ! -L "$STATE_ROOT/analytics/eureka.jsonl" ] || fail 'insight metrics file is a symlink'
TRACKED=$(git -C "$ROOT" ls-files -- .office-hours) || fail 'cannot check tracked state'
[ -z "$TRACKED" ] || fail 'private state is already tracked'
mkdir -p -- "$(dirname -- "$EXCLUDE")" || fail 'cannot create exclusion parent'
# Start a new line even if the existing file has no terminal newline. Preserve rules.
if ! grep -qxF '/.office-hours/' "$EXCLUDE" 2>/dev/null; then
  printf '\n/.office-hours/\n' >> "$EXCLUDE" || fail 'cannot write exclusion'
fi
for path in .office-hours/ .office-hours/builder-profile.jsonl .office-hours/builder-journey.md; do
  git -C "$ROOT" check-ignore -q -- "$path" || fail 'private state is not ignored'
done
mkdir -p -- "$STATE_ROOT" || fail 'cannot create private state directory'
printf '%s\n' "$STATE_ROOT"
