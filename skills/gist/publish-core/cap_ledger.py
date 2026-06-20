#!/usr/bin/env python3
"""publish-core cap ledger — per-surface publish-rate limiter.

Date/week-keyed JSON counter at ~/.claude/state/publish-caps.json:
  {"2026-06-18": {"x": 3}}

Reads the PRIOR count at entry (a passing test can mask an off-by-one when a
function reads its own just-written state — so read first, then write). At cap it
returns "do not continue".

Stdlib-only. All mutations take an exclusive cross-process flock
(common.cap_lock) so concurrent sends can't lose an update and over-publish.

CLI:
  cap_ledger.py check   <surface>   # exit 0 (room) / exit 4 (AT CAP), read-only
  cap_ledger.py incr    <surface>   # atomic check-and-increment; exit 4 if at cap
  cap_ledger.py reserve <surface>   # alias of incr (atomic check-and-increment)
  cap_ledger.py show                # print the current ledger (JSON)
"""
from __future__ import annotations

import json
import sys

import common


def _bucket(surface: str):
    return common.bucket_key(surface)


def current(surface: str) -> int:
    if surface not in common.CAPS:
        raise ValueError(f"unknown surface: {surface}")
    ledger = common.read_json(common.CAPS_PATH, {})
    return int(ledger.get(_bucket(surface), {}).get(surface, 0))


def remaining(surface: str) -> int:
    return max(0, common.CAPS[surface] - current(surface))


def at_cap(surface: str) -> bool:
    return current(surface) >= common.CAPS[surface]


def _do_increment(surface: str, enforce_cap: bool):
    """Atomic read-modify-write under the cap lock. Returns the NEW count, or None
    if enforce_cap and already at cap (no write). The lock makes check+increment
    atomic across concurrent processes (no lost-update over-publish)."""
    with common.cap_lock():
        ledger = common.read_json(common.CAPS_PATH, {})
        bucket = _bucket(surface)
        prior = int(ledger.get(bucket, {}).get(surface, 0))   # read under lock
        if enforce_cap and prior >= common.CAPS[surface]:
            return None
        new = prior + 1
        ledger.setdefault(bucket, {})[surface] = new
        common.write_json(common.CAPS_PATH, ledger)
        return new


def increment(surface: str) -> int:
    """Record one publish (always +1). Atomic under the cap lock."""
    if surface not in common.CAPS:
        raise ValueError(f"unknown surface: {surface}")
    return _do_increment(surface, enforce_cap=False)


def reserve(surface: str):
    """Atomically check-and-increment: returns the NEW count, or None if already
    at cap (no increment). Race-safe replacement for at_cap()-then-increment()."""
    if surface not in common.CAPS:
        raise ValueError(f"unknown surface: {surface}")
    return _do_increment(surface, enforce_cap=True)


def main(argv) -> int:
    if not argv:
        print("usage: cap_ledger.py check|incr|reserve <surface> | show", file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "show":
        print(json.dumps(common.read_json(common.CAPS_PATH, {}), indent=2, sort_keys=True))
        return 0
    if cmd not in ("check", "incr", "reserve") or len(argv) < 2:
        print("usage: cap_ledger.py check|incr|reserve <surface> | show", file=sys.stderr)
        return 2
    surface = argv[1]
    if surface not in common.CAPS:
        print(f"unknown surface: {surface} (valid: {', '.join(common.SURFACES)})", file=sys.stderr)
        return 2
    cap = common.CAPS[surface]
    if cmd == "check":
        cur = current(surface)
        if cur >= cap:
            print(f"AT CAP: {surface} {cur}/{cap} for {_bucket(surface)} — do not continue")
            return 4
        print(f"OK: {surface} {cur}/{cap} for {_bucket(surface)} ({remaining(surface)} remaining)")
        return 0
    # incr / reserve — both atomic check-and-increment under the cap lock (no TOCTOU)
    new = reserve(surface)
    if new is None:
        print(f"AT CAP: {surface} already {current(surface)}/{cap} for {_bucket(surface)} — refusing to increment")
        return 4
    print(f"recorded: {surface} {new}/{cap} for {_bucket(surface)}")
    return 4 if new >= cap else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
