---
name: gist
description: |
  Publish an embeddable PUBLIC GitHub gist of material that is ALREADY public, a
  path in a public repo, fetched over the unauthenticated raw URL so its
  world-readability is a structural fact, not a promise. The shared redactor runs
  as a backstop, a per-day cap is enforced in the live path, and it ships DISARMED
  behind a dual arm flag (a shared flag plus a gist-specific one).
  A gist is a code surface, so this is human-gated: it does not auto-fire and does
  not auto-publish. Use for "make a gist of <public file>", "embeddable gist", "/gist".
disable-model-invocation: true
---

# /gist: publish an embeddable gist of ALREADY-public content

This is not a gist wrapper. It is a discipline skill: how to let an agent publish
to a **code** surface safely. A prose redactor cannot prove the absence of an
embedded secret or a structural leak in real source, so instead of trusting a
scanner on code, `/gist` only ever republishes content it fetched from a **public
repo over the unauthenticated raw URL**. If that fetch 200s, the content is
already world-readable; re-publishing it as a gist discloses nothing new. That
structural guarantee is the guard; the redactor is a backstop on top. This is the
concrete implementation of the "Gate by artifact type" rule in
`references/DERIVE-FROM-PUBLIC.md` (and, if you also installed `/x`, that skill's
`references/DOCTRINE.md`).

**Human-gated** (`disable-model-invocation: true`): a human invokes `/gist`,
reviews the dry-run, and sends. It never auto-fires and never auto-publishes.

## Locate bundled helpers

Use the direct-install assignment below for manual installs. When this skill is
loaded as a plugin, use the `# Plugin:` assignment instead before every command
block. Claude Code substitutes the plugin-root token in the loaded Markdown;
it is not a variable you can assume exists in a terminal. For a manual archive
session, replace it with the actual absolute plugin directory. Keep paths quoted.
Plugin invocation is `/orion-skills:gist`; direct invocation stays `/gist`.

```bash
CORE=~/.claude/skills/gist/publish-core
# Plugin: CORE="${CLAUDE_PLUGIN_ROOT}/skills/gist/publish-core"
```

## Components

- Gist client: `publish-core/gist_client.py`, fetch public raw URL → backstop → dry-run by default
- Redactor:    `publish-core/redactor.py`, backstop; built-in universal patterns + your denylist
- Cap ledger:  `publish-core/cap_ledger.py`, surface `gist` (cap from `$GIST_DAILY_CAP`, default 2); enforced + incremented automatically in the live `--send` path
- Arm flags:   `~/.claude/state/publishers-armed` AND `~/.claude/state/gist-publishers-armed` (a live gist needs BOTH; either absent = DISARMED)
- Self-test:   `publish-core/selftest.py`, proves the guards before you trust them

## Auth

The live create shells `gh gist create --public`, using your existing `gh` token
(it needs the **`gist`** scope: `gh auth refresh -s gist`). No secret is read or
printed by this skill, `gh` handles auth. With no `gh` / no scope, the live
create fails; the dry-run still works (it never calls `gh`).

## Source repo

Pass `--repo OWNER/REPO` (or set `$GIST_SOURCE_REPO`); ref defaults to `main`
(or `$GIST_SOURCE_REF`). **It must be a PUBLIC repo**: the unauthenticated raw
fetch is what proves the content is already world-readable.

## Procedure (run in order; stop at the first gate that blocks)

1. **Pick the already-public source**: one or more repo-relative paths and a
   short description. List valid paths with:
   ```bash
   gh api repos/OWNER/REPO/git/trees/main?recursive=1 --jq '.tree[].path'
   ```

2. **Dry-run (fetch + redactor backstop):**
   ```bash
   python3 "$CORE/gist_client.py" create \
     --repo OWNER/REPO --path path/to/file.md --desc "..."
   ```
   - `REFUSED: ... HTTP 404` → the path/ref is wrong or the repo is not public.
     Fix the path; never bypass (the fetch is the already-public proof).
   - `VERDICT: ABSTAIN` → the backstop hit something. Because the fetch already
     proved world-readability, a hit may be a **false positive** (e.g. a public doc
     that shows a token PREFIX in an example).

3. **Review hits, then ack if benign.** Eyeball each printed hit. If, and only
   if, each is a benign already-public token, re-run with `--ack-public-hits`.
   **Never ack a hit you have not read.** Configuration failures are not content
   hits: `redactor-config` blocks with exit 3 even with `--ack-public-hits`.
   Repair the configured denylist before proceeding. A hit that looks like a real
   secret means a leak is already live in the public repo and must be fixed there first.

4. **Cap check (optional preview).** The live `--send` path enforces the cap
   itself (refuses with exit 4 at cap, reserves before create), so this is just a
   way to see remaining room before you send:
   ```bash
   python3 "$CORE/cap_ledger.py" check gist   # exit 4 = at cap
   ```

5. **Arm check + create.** A gist is a CODE surface, so it needs BOTH flags.
   - **DISARMED (default)**: the dry-run is the deliverable; report it and stop.
   - **ARMED** (`touch` BOTH flags), create live. The dry-run prints a `sha256=`
     per file; pass it back via `--expect-sha256 <name>=<hex>` so the send is
     bound to the exact bytes you reviewed (the default `main` ref can move
     between the dry-run and the send):
     ```bash
     touch ~/.claude/state/publishers-armed
     touch ~/.claude/state/gist-publishers-armed
     python3 "$CORE/gist_client.py" create \
       --repo OWNER/REPO --path path/to/file.md --desc "..." \
       --expect-sha256 "file.md=$REVIEWED_SHA256" --send
     ```
     The live path refuses if either flag is absent, the daily cap is reached, or
     the bytes drifted from `--expect-sha256`. On success it prints the gist URL,
     increments the cap (reserved BEFORE the create so a crash can't leave an
     uncounted public gist), and writes a receipt to
     `~/.claude/state/gist-receipts.jsonl`. For maximum safety, pin `--ref` to an
     immutable commit SHA instead of a branch. Set `REVIEWED_SHA256` to the hash
     from the reviewed dry-run. Add `--ack-public-hits` only after reviewing benign
     content hits; configuration errors cannot be acknowledged.

## First run (smoke test before trusting it)

```bash
# 1. (optional) install your denylist for the backstop, outside the skill:
mkdir -p ~/.claude/config
cp "$CORE/x-denylist.sample.txt" ~/.claude/config/x-denylist.txt
# 2. prove the guards:
python3 "$CORE/selftest.py"
# 3. dry-run against a public path (no gh needed, nothing created):
python3 "$CORE/gist_client.py" create \
  --repo OWNER/REPO --path README.md --desc "test"
# 4. set REVIEWED_SHA256 from the reviewed dry-run, then arm (BOTH flags) + first live gist, then verify it on gist.github.com:
gh auth refresh -s gist          # if your token lacks the gist scope
touch ~/.claude/state/publishers-armed
touch ~/.claude/state/gist-publishers-armed
python3 "$CORE/gist_client.py" create \
  --repo OWNER/REPO --path README.md --desc "test" \
  --expect-sha256 "README.md=$REVIEWED_SHA256" --send
```

## Hard rails

- **Only ever publish content fetched from a PUBLIC repo over the unauthenticated
  raw URL.** Never feed local files to the gist client, the raw-fetch proof is
  the actual guard for this code surface.
- Human-gated: never auto-fire, never auto-send. A human reviews the dry-run.
- Never `--ack-public-hits` a redactor hit you have not eyeballed and confirmed is
  a benign already-public token.
- DISARMED → no create, ever. A live gist needs BOTH the shared flag and the
  gist-specific flag, so arming a prose publisher (e.g. /x) never silently arms
  the gist code surface, see `references/DERIVE-FROM-PUBLIC.md`.
- Never print a token/secret value (the client and `gh` both avoid this; keep it).
- An absent default custom denylist is optional. If `$X_DENYLIST_FILE` is set,
  that input must exist and be readable UTF-8 text with one Python regex per
  line. A broken rule or unreadable input blocks; private rules are never printed.
- Invalid or unreadable cap state returns exit 5 before create and preserves the
  original bytes. Never reset unknown usage to zero. Recovery guidance lives in
  `docs/runbooks/publishing-safety-recovery.md` in the source repository.
- An uncertain create keeps its reserved slot. Verify the original attempt;
  never blindly retry or refund that reservation.
