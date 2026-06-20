---
name: x
description: |
  Post to X (Twitter) from an agent — manually (`/x <text>`) or autonomously (up
  to N/day) — behind a fail-closed safety harness: a redactor that abstains
  rather than leak, a per-day cap, and an arm-flag so the system ships DISARMED
  and never posts until a human enables it. Direct OAuth1.0a (`POST /2/tweets`),
  stdlib-only, no SDK. Use for "post to X", "tweet this", "/x ...", or when an
  autonomous loop wants to publish a short note.
x-origin: original
---

# /x — post to X behind a safety harness

This is not a Twitter wrapper. It is a discipline skill: the worked example of
how to let an autonomous agent publish to a public surface **safely** — verify in
dry-run, ship disarmed, redact fail-closed, cap the rate. The X poster is the
concrete instance; the reusable pattern is in `references/DOCTRINE.md`.

**How it runs:** like every skill in this repo, `/x` loads this `SKILL.md` and the
agent executes the procedure below — there is no separate `/x` binary to install.
The agent (or you, by hand) runs the `publish-core/*.py` steps; nothing posts
until the redactor passes, the cap has room, and the system is armed.

- **Manual:** invoke `/x <text>` (or "post this to X") — you supply the post or a topic to draft.
- **Autonomous:** an agent loop drafts a genericized, value-adding post (≤280
  chars) and runs the SAME safety path. Daily cap: **5** (override with the
  `X_DAILY_CAP` env var — no code edit). Auto-*firing* (a hook that nudges the
  agent when a signal surfaces) is an optional pattern you wire up — see
  `references/HOOK-PATTERN.md`; the skill supports both manual and autonomous invocation.

## Components (installed at `~/.claude/skills/x/`)

- Redactor:  `publish-core/redactor.py` — fail-closed; built-in universal patterns + **your** denylist loaded from `~/.claude/config/x-denylist.txt` (copy `publish-core/x-denylist.sample.txt` there; see `references/REDACTOR-DENYLIST.md`)
- Cap ledger: `publish-core/cap_ledger.py` — surface `x` (cap from `X_DAILY_CAP`)
- X client:   `publish-core/x_client.py` — OAuth1.0a, dry-run by default
- Arm flag:   `~/.claude/state/publishers-armed` (absent = DISARMED)
- Self-test:  `publish-core/selftest.py` — proves the redactor + cap before you trust them

## Credentials

The X client reads four env vars: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`,
`X_ACCESS_TOKEN_SECRET` (OAuth1.0a user-context, from your X app's keys). Populate
the environment however you manage secrets — e.g.:

```bash
# .env file:
export X_API_KEY=...        # then `source ~/.x.env` before running, or:
env $(cat ~/.x.env | xargs) python3 ~/.claude/skills/x/publish-core/x_client.py post --text "…" --send
# Doppler:   doppler run -- python3 .../x_client.py post --text "…" --send
# 1Password: op run -- python3 .../x_client.py post --text "…" --send
# CI:        set them as repo/Action secrets and expose via env:
```

Nothing is hard-coded; with no creds present the client still dry-runs with
synthetic values, and a live send is impossible.

## Procedure (run in order; stop at the first gate that blocks)

1. **Compose** the post (≤280 chars). For autonomous posts, genericize — private
   nouns are forbidden (step 2).

2. **Redact / abstain (fail-closed):**
   ```bash
   printf '%s' "$TEXT" | python3 ~/.claude/skills/x/publish-core/redactor.py --check -
   ```
   Exit 0 = clean → continue. Exit 3 = ABSTAIN → do **not** post; show the hit
   classes, genericize, re-check.
   *Safe to genericize:* `acme-platform` → "our platform", `@acme.com` → "internal
   email", a specific host → "a build box", a teammate's name → "a colleague".
   *Never publish (genericizing won't fix it):* an unpatched security bug,
   confidential business logic, infra internals. If you can't genericize
   confidently, **stop** — never publish past an abstain.

3. **Cap pre-check (informational):**
   ```bash
   python3 ~/.claude/skills/x/publish-core/cap_ledger.py check x
   ```
   Exit 0 = room. Exit 4 = AT CAP → stop ("do not continue: X cap reached today").
   This is a read-only heads-up only; the **authoritative** cap gate is the atomic
   reservation the client makes on `--send` (step 4) — do **not** rely on this
   check to enforce the cap (two concurrent sessions can both pass it).

4. **Arm check + post.**
   - **DISARMED (default)** — run a DRY-RUN and report it's disarmed:
     ```bash
     python3 ~/.claude/skills/x/publish-core/x_client.py post --text "$TEXT"
     ```
   - **ARMED** — send live (creds come from env, never hard-coded):
     ```bash
     python3 ~/.claude/skills/x/publish-core/x_client.py post --text "$TEXT" --send
     ```
   On `--send` the client **atomically reserves the cap slot before the POST**
   (an `at_cap`-then-`incr` race would let two concurrent sessions both publish,
   so the reservation is a single flock-guarded check-and-increment). At cap it
   refuses with exit 4 and sends nothing. The client also records its own receipt
   to `~/.claude/state/x-receipts.jsonl`. There is **no separate post-send
   increment step** — the reservation already counted the publish.

## First run (smoke test before trusting autonomy)

```bash
# 1. install YOUR denylist outside the skill (survives skill updates):
mkdir -p ~/.claude/config
cp ~/.claude/skills/x/publish-core/x-denylist.sample.txt ~/.claude/config/x-denylist.txt
$EDITOR ~/.claude/config/x-denylist.txt                  # add your hosts/products/clients
# 2. prove the guards (stable; no fixture editing needed):
python3 ~/.claude/skills/x/publish-core/selftest.py
# 3. dry-run — no creds needed, nothing sent:
python3 ~/.claude/skills/x/publish-core/x_client.py post --text "hello"
# 4. arm + first live post (then verify it appears on the account):
touch ~/.claude/state/publishers-armed
/x my first real post
```

## Hard rails

- **Never** print a token/secret/auth-header value. The client masks them; keep it.
- A live send requires BOTH the arm flag AND real creds in env. Disarmed or
  missing creds → the client refuses and sends nothing.
- Manual or autonomous, the redactor + cap apply identically.
- **Install your denylist before first use** — without `~/.claude/config/x-denylist.txt`
  the redactor still catches secret-shaped tokens and RFC-1918 IPs (built-in), but
  NOT your hostnames/products/clients. `--check` warns when that file is absent.
- For the autonomous trigger (a hook that nudges the agent when a signal
  surfaces), see `references/HOOK-PATTERN.md` — it's an adapt-it pattern (signal
  detection is yours to define); hooks NUDGE, they never post.
