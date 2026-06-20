#!/usr/bin/env python3
"""publish-core shared primitives: paths, arm-flag, logging, rate buckets.

The cross-cutting state for an autonomous-publishing safety harness. Stdlib-only
by design (no external deps -> offline-runnable, no SDK drift).

This copy ships with one surface ('gist'). Add your own surfaces by extending
CAPS below; a per-day surface uses day_key(), a per-week surface uses week_key()
(add it to WEEKLY_SURFACES).
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import fcntl
import json
import os
from pathlib import Path

HOME = Path(os.environ.get("HOME", str(Path.home())))
STATE_DIR = HOME / ".claude" / "state"

# State files.
CAPS_PATH = STATE_DIR / "publish-caps.json"
CAPS_LOCK_PATH = STATE_DIR / "publish-caps.lock"
PROCESSED_PATH = STATE_DIR / "publish-processed.json"
ARM_FLAG_PATH = STATE_DIR / "publishers-armed"
# A gist is a CODE surface — higher-risk than prose. It must NOT inherit "armed"
# from the shared flag a lower-risk prose surface (e.g. /x) set before gist
# existed. A live gist therefore requires BOTH flags (see is_gist_armed()).
GIST_ARM_FLAG_PATH = STATE_DIR / "gist-publishers-armed"
GIST_RECEIPTS_PATH = STATE_DIR / "gist-receipts.jsonl"
NUDGE_LOG = STATE_DIR / "publish-nudge.log"

# Per-surface caps. The gist daily cap is overridable via $GIST_DAILY_CAP
# (default 2) so you don't edit code to retune it. Extend this dict to add
# surfaces — give each its own env override if you like.
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


CAPS = {"gist": _int_env("GIST_DAILY_CAP", 2)}
# Surfaces whose cap is per-ISO-week instead of per-day. (none by default)
WEEKLY_SURFACES = set()
SURFACES = tuple(CAPS.keys())


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def iso_z(ts: _dt.datetime | None = None) -> str:
    ts = ts or utcnow()
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def day_key(ts: _dt.datetime | None = None) -> str:
    ts = ts or utcnow()
    return ts.strftime("%Y-%m-%d")


def week_key(ts: _dt.datetime | None = None) -> str:
    """ISO year-week bucket, e.g. 2026-W25 (for per-week surfaces)."""
    ts = ts or utcnow()
    iso = ts.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def bucket_key(surface: str, ts: _dt.datetime | None = None) -> str:
    return week_key(ts) if surface in WEEKLY_SURFACES else day_key(ts)


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def is_armed() -> bool:
    """The shared arm flag: the system ships DISARMED (file absent by default).

    Live-create paths MUST check this; dry-run never does. Arm with
    `touch ~/.claude/state/publishers-armed` after your first manual smoke test;
    disarm by removing it.

    NOTE: a CODE surface (like gist) requires a SECOND, surface-specific flag on
    top of this one so it can't inherit "armed" from a lower-risk prose surface —
    see is_gist_armed() and references/DERIVE-FROM-PUBLIC.md.
    """
    return ARM_FLAG_PATH.exists()


def is_gist_armed() -> bool:
    """A live gist requires BOTH the shared flag AND its own flag.

    A gist publishes CODE to the public internet under your account — a strictly
    higher-risk surface than a prose poster. Requiring a gist-specific flag means
    arming /x (or any prose publisher) never silently arms gist; removing the
    shared flag still disarms everything. Arm a live gist with BOTH:
        touch ~/.claude/state/publishers-armed
        touch ~/.claude/state/gist-publishers-armed
    """
    return ARM_FLAG_PATH.exists() and GIST_ARM_FLAG_PATH.exists()


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> None:
    ensure_state_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


@contextlib.contextmanager
def cap_lock():
    """Hold an exclusive cross-process lock for the cap ledger.

    The ledger is a read-modify-write on one JSON file shared by every surface and
    every concurrent session. Without a lock, two sends can both read prior=N and
    both write N+1 — a lost update that over-publishes. flock on a dedicated lock
    file makes check+increment atomic across processes. POSIX (Linux/macOS).
    """
    ensure_state_dir()
    fh = CAPS_LOCK_PATH.open("w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def log_line(message: str) -> None:
    """Append to the operations log. NEVER /dev/null (a silent probe failure
    must not masquerade as success)."""
    ensure_state_dir()
    try:
        with NUDGE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{iso_z()} {message}\n")
    except OSError:
        pass
