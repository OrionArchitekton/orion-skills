#!/usr/bin/env python3
"""publish-core redactor, the ONLY guard for public output.

A public surface (X, a blog, a gist) often has NO platform-side secret/PII
scanner. So private material must be caught HERE before it ships. Policy: a
denylist of private tokens + ABSTAIN-if-uncertain (fail-closed). If a candidate
carries any denylisted proper noun, host, identity, PII, or secret-shaped token,
the verdict is ABSTAIN: do NOT publish, surface to a human to genericize.

Two layers of patterns plus a bounded public-identifier allowlist:
  * BUILT-IN UNIVERSAL (below), secret-shaped tokens, RFC-1918/CGNAT IPs,
    private-key headers, *.internal/.local hosts, /home//Users absolute paths,
    and customer PII (emails, SSNs, phone numbers). Useful for everyone, always on.
  * YOUR CUSTOM DENYLIST (loaded from a file OUTSIDE this skill), your org's
    hostnames, repo/product names, client identities, internal email domains.
    Default: ~/.claude/config/x-denylist.txt (override with $X_DENYLIST_FILE).
    Keeping your private nouns in an external file means they survive skill
    updates AND you never accidentally publish your own denylist if you share
    the skill. Copy publish-core/x-denylist.sample.txt to that path and edit.
    See references/REDACTOR-DENYLIST.md.
  * PUBLIC TECHNICAL IDENTIFIER ALLOWLIST (references/public-technical-identifiers.v1.json),
    standard public CLI commands/flags, git env/config keys, RFCs, public error
    codes, OSS libraries, and documented APIs. Exact allowlisted identifiers only
    exempt generic long-token entropy matches so public CS terminology survives
    verbatim; explicit secrets, IPs, private hosts, internal paths, customer PII,
    and custom denylist rules NEVER yield to the allowlist.

A denylist is a backstop, not a proof. For machine-screening real source code,
pair it with an entropy/allowlist secret scanner (gitleaks/trufflehog-class) and
keep code surfaces human-gated.

Stdlib-only. Never echoes a matched secret value (matches are masked).

CLI:
  redactor.py --check <file|->     # exit 0 PUBLISH (clean) / exit 3 ABSTAIN
  redactor.py --redact <file|->    # print a redacted preview (placeholders)
  redactor.py --selftest           # run the bundled checks
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path

CUSTOM_PATH = Path(os.environ.get(
    "X_DENYLIST_FILE", str(Path.home() / ".claude" / "config" / "x-denylist.txt")))
ALLOWLIST_PATH = (
    Path(__file__).resolve().parent.parent / "references" / "public-technical-identifiers.v1.json"
)
_ALLOWLIST_SCHEMA = "public-technical-allowlist/v1"

_BUILTIN = []
_GENERIC_ENTROPY_CLASS = "secret"
_GENERIC_ENTROPY_PATTERN = r"\b[A-Za-z0-9_\-]{40,}\b"


def _add(cls: str, pattern: str, flags=re.IGNORECASE, *, allowlist_exempt: bool = False):
    _BUILTIN.append((cls, re.compile(pattern, flags), allowlist_exempt))


# --- BUILT-IN UNIVERSAL (always on; no editing needed) ---
# Private network coordinates.
_add("internal-ip", r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")
_add("internal-ip", r"\b(?:192\.168\.\d{1,3}\.\d{1,3})\b")
_add("internal-ip", r"\b(?:172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")
_add("internal-ip", r"\b(?:100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})\b")
_add("internal-host", r"\blocalhost:\d{2,5}\b")
_add("internal-host", r"\b[\w.-]+\.(?:internal|local|svc\.cluster\.local)\b")
# Absolute home/workspace paths that pin an author/machine (matters for code).
_add("internal-path", r"/home/[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+")
_add("internal-path", r"/Users/[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+")
# Customer / personal PII. Never allowlisted.
_add("pii", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_add("pii", r"\b\d{3}-\d{2}-\d{4}\b")
_add("pii", r"(?<!\d)(?:\+1[-.\s])?(?:\(\d{3}\)\s*|\d{3}-)\d{3}-\d{4}(?!\d)")
# Secret-shaped tokens (high-entropy / known prefixes). Fail-closed.
_add("secret", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")
_add("secret", r"\b(?:Bearer|bearer)\s+[A-Za-z0-9._\-]{16,}\b")
_add("secret", r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b")
_add("secret", r"\b(?:sk|pk|rk|ghp|gho|ghs|glpat|xoxb|xoxp)[-_][A-Za-z0-9_-]{16,}\b")
_add("secret", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{6,}\b")
_add("secret", r"\bdp\.[A-Za-z0-9._-]{6,}\b")
_add(_GENERIC_ENTROPY_CLASS, _GENERIC_ENTROPY_PATTERN, allowlist_exempt=True)


class RedactionConfigError(ValueError):
    """Configured protection could not be loaded; contains no private rules."""


def load_public_allowlist(path: Path | None = None) -> tuple[str, frozenset[str]]:
    """Load the versioned Public Technical Identifier Allowlist fail-closed.

    An absent default ALLOWLIST_PATH returns an empty set; an explicit path, a
    symlink, an unreadable file, or malformed schema raises RedactionConfigError.
    """
    target = path if path is not None else ALLOWLIST_PATH
    o_nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, os.O_RDONLY | o_nofollow)
    except FileNotFoundError as exc:
        if path is not None or target.is_symlink():
            raise RedactionConfigError("allowlist: missing-config") from exc
        return "0.0.0", frozenset()
    except OSError as exc:
        raise RedactionConfigError("allowlist: unreadable-config") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise RedactionConfigError("allowlist: unreadable-config")
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            fd = -1
            payload = json.load(fh)
    except RedactionConfigError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RedactionConfigError("allowlist: invalid-json") from exc
    finally:
        if fd != -1:
            os.close(fd)
    if not isinstance(payload, dict) or payload.get("schema_version") != _ALLOWLIST_SCHEMA:
        raise RedactionConfigError("allowlist: invalid-schema")
    version = payload.get("version")
    categories = payload.get("categories")
    if not isinstance(version, str) or not version.strip() or not isinstance(categories, dict):
        raise RedactionConfigError("allowlist: invalid-schema")
    entries: set[str] = set()
    for items in categories.values():
        if not isinstance(items, list) or not all(isinstance(x, str) and x for x in items):
            raise RedactionConfigError("allowlist: invalid-entries")
        entries.update(items)
    return version, frozenset(entries)


def is_allowlisted_public_identifier(
    token: str, *, allowlist: frozenset[str] | None = None
) -> bool:
    """Return True iff token matches an exact entry in the public technical allowlist."""
    entries = allowlist if allowlist is not None else load_public_allowlist()[1]
    return token in entries


def _is_exempt_match(text: str, match: re.Match[str], allowlist: frozenset[str]) -> bool:
    raw = match.group(0)
    if raw in allowlist:
        return True
    # CLI long flags start with "--", which lies outside \b; accept "--<matched>" if allowlisted.
    start = match.start()
    if start >= 2 and text[start - 2 : start] == "--" and f"--{raw}" in allowlist:
        return True
    return False


def _load_custom():
    """Return compiled patterns and safe (line, failure class) diagnostics.

    Only an absent default denylist is optional. An explicit path, an existing
    unreadable input, or any malformed rule blocks the whole guard.
    """
    pats, errors = [], []
    try:
        if not stat.S_ISREG(CUSTOM_PATH.stat().st_mode):
            return pats, [(0, "unreadable-config")]
        contents = CUSTOM_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        if "X_DENYLIST_FILE" in os.environ or CUSTOM_PATH.is_symlink():
            errors.append((0, "missing-config"))
        return pats, errors
    except (OSError, UnicodeError):
        return pats, [(0, "unreadable-config")]
    for lineno, ln in enumerate(contents.splitlines(), 1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        try:
            pats.append(("custom", re.compile(s, re.IGNORECASE), False))
        except (re.error, OverflowError, RecursionError, MemoryError):
            errors.append((lineno, "invalid-regex"))
    return pats, errors


def active_patterns():
    pats, errors = _load_custom()
    if errors:
        raise RedactionConfigError("; ".join(
            f"denylist line {line}: {kind}" if line else f"denylist: {kind}"
            for line, kind in errors))
    return _BUILTIN + pats


def custom_load_errors():
    """Return safe failure locations/classes, never private patterns."""
    return _load_custom()[1]


def _mask(s: str) -> str:
    s = s.strip()
    if len(s) <= 4:
        return s[0] + "*" * (len(s) - 1) if s else ""
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def scan(text: str):
    """Return [(class, masked_snippet)]. Never returns raw secret text."""
    patterns = active_patterns()
    _, allowlist = load_public_allowlist()
    hits, seen = [], set()
    for cls, rx, allowlist_exempt in patterns:
        for m in rx.finditer(text):
            if allowlist_exempt and _is_exempt_match(text, m, allowlist):
                continue
            raw = m.group(0)
            key = (cls, raw.lower())
            if key in seen:
                continue
            seen.add(key)
            hits.append((cls, _mask(raw)))
    return hits


def redact(text: str) -> str:
    patterns = active_patterns()
    _, allowlist = load_public_allowlist()
    out = text
    for cls, rx, allowlist_exempt in patterns:
        if allowlist_exempt:
            out = rx.sub(
                lambda m, _cls=cls, _src=out: (
                    m.group(0) if _is_exempt_match(_src, m, allowlist) else f"[REDACTED:{_cls}]"
                ),
                out,
            )
        else:
            out = rx.sub(f"[REDACTED:{cls}]", out)
    return out


def decision(text: str):
    """Fail-closed verdict. ('PUBLISH', []) or ('ABSTAIN', hits)."""
    try:
        hits = scan(text)
    except RedactionConfigError as exc:
        return "ABSTAIN", [("redactor-config", str(exc))]
    return ("ABSTAIN" if hits else "PUBLISH"), hits


def _read_source(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()
    with open(arg, "r") as fh:
        return fh.read()


def main(argv) -> int:
    if not argv:
        print("usage: redactor.py --check|--redact <file|-> | --selftest", file=sys.stderr)
        return 2
    mode = argv[0]
    if mode == "--selftest":
        import selftest
        return selftest.main([])
    if len(argv) < 2:
        print("usage: redactor.py --check|--redact <file|->", file=sys.stderr)
        return 2
    if mode == "--check" and "X_DENYLIST_FILE" not in os.environ and not CUSTOM_PATH.exists():
        print("note: no default custom denylist; only built-in universal patterns "
              "are active. Your private nouns are NOT covered.", file=sys.stderr)
    text = _read_source(argv[1])
    if mode == "--redact":
        try:
            sys.stdout.write(redact(text))
        except RedactionConfigError as exc:
            print(f"ABSTAIN: {exc}", file=sys.stderr)
            return 3
        return 0
    if mode == "--check":
        verdict, hits = decision(text)
        print(f"VERDICT: {verdict}")
        if hits:
            print(f"HITS ({len(hits)}), genericize before publishing:")
            for cls, masked in hits:
                print(f"  - [{cls}] {masked}")
        return 0 if verdict == "PUBLISH" else 3
    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(main(sys.argv[1:]))
