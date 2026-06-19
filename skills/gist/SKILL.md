---
name: gist
description: |
  Publish an embeddable PUBLIC GitHub gist of material that is ALREADY public — a
  path in a public repo, fetched over the unauthenticated raw URL so its
  world-readability is a structural fact, not a promise. The shared redactor runs
  as a backstop, a per-day cap applies, and it ships DISARMED behind an arm flag.
  A gist is a code surface, so this is human-gated: it does not auto-fire and does
  not auto-publish. Use for "make a gist of <public file>", "embeddable gist", "/gist".
disable-model-invocation: true
---

# /gist — publish an embeddable gist of ALREADY-public content

This is not a gist wrapper. It is a discipline skill: how to let an agent publish
to a **code** surface safely. A prose redactor cannot prove the absence of an
embedded secret or a structural leak in real source — so instead of trusting a
scanner on code, `/gist` only ever republishes content it fetched from a **public
repo over the unauthenticated raw URL**. If that fetch 200s, the content is
already world-readable; re-publishing it as a gist discloses nothing new. That
structural guarantee is the guard; the redactor is a backstop on top. This is the
concrete implementation of the "Gate by artifact type" rule in
`references/DERIVE-FROM-PUBLIC.md` (and, if you also installed `/x`, that skill's
`references/DOCTRINE.md`).

**Human-gated** (`disable-model-invocation: true`): a human invokes `/gist`,
reviews the dry-run, and sends. It never auto-fires and never auto-publishes.

## Components (installed at `~/.claude/skills/gist/`)

- Gist client: `publish-core/gist_client.py` — fetch public raw URL → backstop → dry-run by default
- Redactor:    `publish-core/redactor.py` — backstop; built-in universal patterns + your denylist
- Cap ledger:  `publish-core/cap_ledger.py` — surface `gist` (cap from `$GIST_DAILY_CAP`, default 2)
- Arm flag:    `~/.claude/state/publishers-armed` (absent = DISARMED)
- Self-test:   `publish-core/selftest.py` — proves the guards before you trust them

## Auth

The live create shells `gh gist create --public`, using your existing `gh` token
(it needs the **`gist`** scope: `gh auth refresh -s gist`). No secret is read or
printed by this skill — `gh` handles auth. With no `gh` / no scope, the live
create fails; the dry-run still works (it never calls `gh`).

## Source repo

Pass `--repo OWNER/REPO` (or set `$GIST_SOURCE_REPO`); ref defaults to `main`
(or `$GIST_SOURCE_REF`). **It must be a PUBLIC repo** — the unauthenticated raw
fetch is what proves the content is already world-readable.

## Procedure (run in order; stop at the first gate that blocks)

1. **Pick the already-public source** — one or more repo-relative paths and a
   short description. List valid paths with:
   ```bash
   gh api repos/OWNER/REPO/git/trees/main?recursive=1 --jq '.tree[].path'
   ```

2. **Dry-run (fetch + redactor backstop):**
   ```bash
   python3 ~/.claude/skills/gist/publish-core/gist_client.py create \
     --repo OWNER/REPO --path path/to/file.md --desc "..."
   ```
   - `REFUSED: ... HTTP 404` → the path/ref is wrong or the repo is not public.
     Fix the path; never bypass (the fetch is the already-public proof).
   - `VERDICT: ABSTAIN` → the backstop hit something. Because the fetch already
     proved world-readability, a hit is a **false positive** (e.g. a public doc
     that shows a token PREFIX in an example).

3. **Review hits, then ack if benign.** Eyeball each printed hit. If — and only
   if — each is a benign already-public token, re-run with `--ack-public-hits`.
   **Never ack a hit you have not read.** A hit that looks like a real secret
   means a leak is already live in the public repo and must be fixed there first.

4. **Cap check:**
   ```bash
   python3 ~/.claude/skills/gist/publish-core/cap_ledger.py check gist   # exit 4 = stop
   ```

5. **Arm check + create.**
   - **DISARMED (default)** — the dry-run is the deliverable; report it and stop.
   - **ARMED** (`touch ~/.claude/state/publishers-armed`) — create live:
     ```bash
     python3 ~/.claude/skills/gist/publish-core/gist_client.py create \
       --repo OWNER/REPO --path path/to/file.md --desc "..." --ack-public-hits --send
     ```
     Prints the gist URL; writes a receipt to `~/.claude/state/gist-receipts.jsonl`.

6. **On a successful live create**, record the cap:
   ```bash
   python3 ~/.claude/skills/gist/publish-core/cap_ledger.py incr gist
   ```

## First run (smoke test before trusting it)

```bash
# 1. (optional) install your denylist for the backstop, outside the skill:
mkdir -p ~/.claude/config
cp ~/.claude/skills/gist/publish-core/x-denylist.sample.txt ~/.claude/config/x-denylist.txt
# 2. prove the guards:
python3 ~/.claude/skills/gist/publish-core/selftest.py
# 3. dry-run against a public path (no gh needed, nothing created):
python3 ~/.claude/skills/gist/publish-core/gist_client.py create \
  --repo OWNER/REPO --path README.md --desc "test"
# 4. arm + first live gist, then verify it on gist.github.com:
gh auth refresh -s gist          # if your token lacks the gist scope
touch ~/.claude/state/publishers-armed
python3 ~/.claude/skills/gist/publish-core/gist_client.py create \
  --repo OWNER/REPO --path README.md --desc "test" --send
```

## Hard rails

- **Only ever publish content fetched from a PUBLIC repo over the unauthenticated
  raw URL.** Never feed local files to the gist client — the raw-fetch proof is
  the actual guard for this code surface.
- Human-gated: never auto-fire, never auto-send. A human reviews the dry-run.
- Never `--ack-public-hits` a redactor hit you have not eyeballed and confirmed is
  a benign already-public token.
- DISARMED → no create, ever. If you run several publishers off one arm flag,
  give this code surface its own second flag — see `references/DERIVE-FROM-PUBLIC.md`.
- Never print a token/secret value (the client and `gh` both avoid this — keep it).
