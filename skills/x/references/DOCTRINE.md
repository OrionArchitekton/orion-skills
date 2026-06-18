# Autonomous-publishing safety doctrine

The reusable pattern behind `/x`. Any skill that lets an agent write to a public
surface (X, a blog, a gist, a public repo) should hold to these five rules. They
are why the X poster is a *discipline* skill, not a tool wrapper.

## 1. Dry-run is the proof

A build that verifies an autonomous publisher by *publishing* has already failed
its safety contract — it acted in the world before anyone confirmed it should, and
left an artifact that can't be recalled. Verify by **constructing** the action and
inspecting its shape, not by emitting it: the client signs the request and prints
method/URL/auth-present without sending. Independent verification = effect on
dry-run artifacts, never a live post.

## 2. Ship DISARMED

The system starts unable to act. A live send requires an explicit arm flag
(`~/.claude/state/publishers-armed`, absent by default) **and** real credentials
in the environment. An autonomous build must never leave a live public-posting
path armed before a human's first manual smoke test. Arming is a human act:
`touch` the flag, post once manually, verify, then leave it armed (or not).

## 3. The redactor is the guard — fail closed

Public surfaces often have no platform-side secret/PII scanner, so the redactor is
the *only* thing between private material and the world. It must **abstain when
uncertain**, not best-effort strip: any denylist hit → ABSTAIN → do not publish,
surface to a human to genericize. Abstaining on a borderline candidate is correct;
leaking once is not. A denylist is a backstop, not a proof — for screening real
source code, pair it with an entropy/allowlist scanner and keep code human-gated.

## 4. Hooks nudge — they never post

A shell hook can't run a skill or post anything; it can only emit
`additionalContext` to NUDGE the in-session model to consider publishing. So
"autonomous" means *no per-post human approval gate while a session is running* —
not a daemon posting while you're away. The model still executes in-session on the
nudge, through the same redactor + cap + arm gates. See `HOOK-PATTERN.md`.

## 5. Caps are host-global

The cap ledger lives in one file under `~/.claude/state/`, so multiple concurrent
sessions share one budget and one dedup set — no double-publish, no coordination
needed. Read the prior count at function entry, then write (a function that reads
its own just-written state can mask an off-by-one). At cap: "do not continue."

## Gate by artifact type

Match the human gate to the blast radius. Short prose (a tweet, a note) can
auto-publish behind the redactor + cap. **Code/config is a higher-risk surface**
(embedded secrets, real paths, env-var names that map your infra, internal
identifiers) — keep it human-gated and, ideally, publish only material that is
*already* public. The redactor's PUBLISH verdict is necessary, not sufficient, for
code.
