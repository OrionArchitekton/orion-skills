# Customizing the redactor denylist

`publish-core/redactor.py` is the only guard for public output. It has two layers:
**built-in universal** patterns (always on, no editing) and **your custom**
denylist (loaded from a file *outside* the skill).

## Built-in universal patterns (keep as-is)

No editing needed; these catch the most dangerous leaks for everyone:

- **Secret-shaped tokens** — private-key headers, `Bearer …`, AWS `AKIA…`,
  `ghp_`/`glpat-`/`sk-`/`xoxb-` prefixes, JWTs, Doppler `dp.…`, generic
  high-entropy strings (≥40 chars).
- **Private network coordinates** — RFC-1918 (10/8, 172.16/12, 192.168/16),
  CGNAT/mesh (100.64/10), `localhost:PORT`, `*.internal` / `*.local` /
  `*.svc.cluster.local`.
- **Absolute home paths** — `/home/<user>/…`, `/Users/<user>/…` (pin an
  author/machine; matter most for code surfaces).

## Your custom denylist (external file — edit THIS, not the code)

Your org-specific nouns live in a file the skill loads at runtime:

```bash
mkdir -p ~/.claude/config
cp publish-core/x-denylist.sample.txt ~/.claude/config/x-denylist.txt
$EDITOR ~/.claude/config/x-denylist.txt
```

(Override the path with `$X_DENYLIST_FILE`.) One Python regex per line, matched
case-insensitively; `#` starts a comment. A plain word is a valid regex; use
`\b…\b` on short tokens to avoid matching inside ordinary words.

**Why a file, not editing `redactor.py`:** your private nouns survive skill
updates, and you never accidentally publish your own denylist (a map of exactly
what you consider sensitive) if you share or fork the skill. The skill ships with
**no** real org nouns — until you create this file, only the universal patterns
are active, and `redactor.py --check` prints a warning saying so.

| Class to add | Examples for the file |
|---|---|
| hostnames / nodes | `\b(?:prod\|staging\|db)-host-\d+\b` |
| repos / products / services | `\b(?:acme-platform\|internal-service)\b` |
| business / client identities | `\bACME\b`, `\bAcme Corp\b` |
| internal email domains | `[\w.%+-]+@(?:yourcompany\|internal)\.com` |
| internal branch / ticket refs | `\b(?:internal\|private)/[\w./-]+\b`, `\bJIRA-\d+\b` |

## Policy: abstain if uncertain (fail-closed)

`decision(text)` returns `ABSTAIN` if **any** pattern (built-in or custom)
matches, and you must not publish past an ABSTAIN — genericize and re-check, or
stop. The point is to *refuse and surface*, not to auto-strip and post (which can
leave a partial leak). Abstaining on a borderline candidate is the correct, safe
outcome.

## Verify

```bash
python3 publish-core/selftest.py     # built-ins + the custom loader + cap, all green
```
The self-test is stable regardless of your customization — it proves the built-in
universals and that a custom file is loaded and applied (via a temp file), so you
don't have to keep test fixtures in sync with your real denylist.

## A denylist is a backstop, not a proof

Enumeration can't anticipate every private noun, and it is the wrong tool for
machine-screening real **source code** (embedded secrets, structural identifiers,
business logic). For code/config surfaces: keep them human-gated, pair the
denylist with an entropy/allowlist secret scanner (gitleaks/trufflehog-class),
and prefer publishing material that is already public.
