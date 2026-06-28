---
name: tools-router
description: Use when an agent harness has many CLIs and MCP servers and the agent keeps being told which exist or which to use, and you want a low-token, periodically-refreshed index that prefers a working CLI over its MCP and flags unauthenticated tools. Triggers include "build a tools index", "which CLIs/MCPs are available", CLI-vs-MCP preference, auth-aware tool dedup, a session-start tools injector, "stop telling the agent to use tool X".
---

# Tools Router

## Overview

An agent reasons better when it reliably knows its own tools. The tools-router gives every
session a low-token, trustworthy map of the CLIs and MCP servers it can reach, which surface
to prefer, and which are unauthenticated — without a human naming tools each time.

**Core principle: build the index OUT of band, inject it CHEAPLY, and make every judgment
AUTH-AWARE and SECRET-SAFE.** Two planes:

1. A **periodic recon generator** that PROBES auth/health and RENDERS a compact index + flags.
2. A **thin, fail-open session injector** that injects the pre-rendered index and does no probing.

The split is load-bearing: probing is slow and secret-bearing, so it must never run on the
session hot path; the injector just reads a cached artifact and assumes-authed (the recon earns that).

## When to use

- The agent keeps being told "use the X CLI" / "check the Y MCP" — it doesn't know its surface.
- Both a CLI and an MCP cover the same capability and you want one preferred (CLI is cheaper on
  context, often broader access) without losing the other when it's the only one that works.
- You want unauthenticated tools surfaced before the agent confidently calls a dead one.

**Not for:** a single known tool (just call it); a surface small enough to hold in the system
prompt by hand.

## The two planes

**Plane 1 — periodic recon generator** (a timer/cron/CI job, NOT the session). Probe each CLI's
read-only identity command and each MCP's health, then render. Four disciplines, each below.

**Plane 2 — fail-open injector** (session start). Read the PRE-RENDERED compact table and inject
it; do zero probing and zero subprocess spawning. If the table is missing or malformed, inject
nothing and exit success — a session must never block on the index. Prepend a one-line banner when
there are flags or the table is stale (older than your recon interval × a few), so a missed recon
surfaces instead of silently serving stale auth.

## Disciplines (the non-obvious half — get these wrong and the index lies)

| Discipline | Rule |
|---|---|
| **Auth-aware dedup** | Redundancy is relative to which side WORKS, not which exists. Recommend dropping the side that is NOT the sole working provider. The working side can be EITHER. |
| **Secret-safe capture** | NEVER persist raw probe stdout. Capture an enum status + a non-secret identity only; redact defensively. |
| **Per-tool auth detection** | One rule for all tools is wrong. Use an affirmative predicate over exit code AND a content signal, per tool. |
| **Fail-soft parsing** | The tool list may not be machine-readable. Pin to status WORDS (not glyphs/format); fail-soft unparseable rows to UNKNOWN, never drop. |

### Auth-aware dedup — the inversion that bites

"A CLI exists, so drop the redundant MCP" is a trap. A provider's MCP can be **live while its CLI
is logged out** — the existence rule would remove the working provider for a broken one. Compare
the *working/authed* state of both sides:

- working CLI + dead/unauthed MCP → recommend dropping the MCP.
- **working MCP + unauthed CLI → flag the CLI; KEEP the MCP** (the inversion).
- both work → a surface judgment for a human, not an auto-kill.
- Always **recommend-only and human-gated** — never auto-disable a provider.

### Secret-safe capture — the probe output is the secret

Auth probes print secrets (a `config` dump can echo live API keys to stdout). If you persist raw
probe output into the rendered index, you leak credentials into a file the agent reads — and, in a
repo with a secret-scanner pre-commit gate, you can silently block every commit. Capture only an
enum (`authed`/`unauthed`/`config_present`/`indeterminate`/`unknown`) plus a non-secret identity
(account, email, org), run a fail-closed redactor over every field, and add a test asserting no
secret shape reaches any rendered string.

### Per-tool auth detection — exit code alone lies

Many CLIs exit 0 while printing "not logged in"; some report auth only via a side effect; some are
**env-var based** (auth depends on an environment variable, so a probe run without the runtime env
is *indeterminate*, not unauthed). Two specific traps:

- **config-present ≠ auth-verified.** A local-config read tells you a key is *stored*, not that it's
  *live* — it cannot detect a revoked/expired key. Mark it `config_present`, not `authed`.
- **masked-failure.** `probe-command || version-command` always exits 0 (the fallback fires on
  failure and succeeds), so RC reports "authed" even with no credential. Use an affirmative
  predicate ("found a logged-in marker"), never "didn't see an error."

## Reference implementation

`reference-recon.py` — the generator pattern in ~150 lines (fail-soft list parse, per-tool auth
spec table, secret-safe capture, auth-aware dedup, compact render). `session-injector.sh` — a thin,
fail-open session-start injector. Both are illustrative skeletons to adapt, not drop-in code.

## Common mistakes

| Mistake | Fix |
|---|---|
| Dedup by existence ("a CLI exists → drop the MCP") | Dedup by which side WORKS; keep a live MCP whose CLI is logged out. |
| Persisting raw probe stdout into the index | Capture enum + non-secret identity; redact; test that no secret renders. |
| One auth rule (usually `exit==0`) for all tools | Per-tool affirmative predicate over exit + content; handle env-var and config-present. |
| Probing at session start | Probe in the periodic recon only; the injector reads a cached table, fail-open. |
| Auto-disabling a "redundant" provider | Recommend-only, human-gated — removal is irreversible-ish config surgery. |

## Boundary

This skill teaches the PATTERN and its disciplines. The mechanics are your harness's:
- how a session-start hook is registered and what shape its output takes;
- how the periodic job is scheduled (systemd timer, cron, CI) and kept alive;
- where the CLI list and MCP-server list come from, and your tool runtime's PATH;
- your repo's secret-scanner config and commit gates.

Defer all of those to your environment's own contract; keep the disciplines above intact.
