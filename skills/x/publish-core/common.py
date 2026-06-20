#!/usr/bin/env python3
"""publish-core shared primitives: paths, arm-flag, logging, rate buckets.

The cross-cutting state for an autonomous-publishing safety harness. Stdlib-only
by design (no external deps -> offline-runnable, no SDK drift).

This ships with one surface ('x' / Twitter). Add your own surfaces by extending
CAPS below; a per-day surface uses day_key(), a per-week surface uses week_key()
(add it to WEEKLY_SURFACES).
"""
from __future__ import annotations

import contextlib
import datetime as _dt
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
X_RECEIPTS_PATH = STATE_DIR / "x-receipts.jsonl"
NUDGE_LOG = STATE_DIR / "publish-nudge.log"

# Per-surface caps. The X daily cap is overridable via $X_DAILY_CAP (default 5)
# so you don't edit code to retune it. Extend this dict to add surfaces
# (e.g. "blog": 1) — give each its own env override if you like.
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


CAPS = {"x": _int_env("X_DAILY_CAP", 5)}
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
    """The system ships DISARMED: the arm-flag file is absent by default.

    Live-send paths MUST check this; dry-run never does. Arm with
    `touch ~/.claude/state/publishers-armed` after your first manual smoke test;
    disarm by removing it.
    """
    return ARM_FLAG_PATH.exists()


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> None:
    ensure_state_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


@contextlib.contextmanager
def cap_lock():
    """Hold an exclusive cross-process lock for the cap ledger.

    The ledger is a read-modify-write on one JSON file shared by every surface and
    every concurrent session. Without a lock, two sends can both read prior=N and
    both write N+1 — a lost update that over-publishes. flock on a dedicated lock
    file makes check+increment atomic across processes.

    POSIX (Linux/macOS) gets real flock. fcntl is imported lazily so this module
    still imports on non-POSIX platforms (e.g. Windows) for dry-runs/tests; there
    the lock degrades to a no-op (single-machine concurrency on Windows is out of
    scope for this harness). The lock file is opened in append mode so acquiring
    the lock never truncates it.
    """
    ensure_state_dir()
    try:
        import fcntl
    except ImportError:
        fcntl = None
    fh = CAPS_LOCK_PATH.open("a")
    try:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def log_line(message: str) -> None:
    """Append to the operations log. NEVER /dev/null (a silent probe failure
    must not masquerade as success)."""
    ensure_state_dir()
    try:
        with NUDGE_LOG.open("a") as fh:
            fh.write(f"{iso_z()} {message}\n")
    except OSError:
        pass
