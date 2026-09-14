# Changelog

All notable changes to the orion-skills library. This project follows Semantic
Versioning (https://semver.org): adding a skill is a MINOR bump, a non-breaking change to
an existing skill is a PATCH, and removing or breaking a skill is a MAJOR bump.

## [Unreleased]

### Fixed

- `readonly` hook: a `json.py` (or `json/` package) in the session directory no
  longer disables the gate. The harness runs hooks from the session directory and
  `python3 -` put it first on the import path, so an audited repo carrying that file
  turned an active marker into an allow and ran its own code on every edit attempt.
  The hook and `readonly-mode.sh` now run python isolated (`-I`). A fail-closed
  denial now prints the marker path and recovery commands on stderr instead of
  blocking silently; `status` runs the hook file directly and reports UNKNOWN for a
  hook the harness could not execute or start (exit 126/127); the hook drains stdin
  past its 16 KiB cap in the background, so a large payload never meets a closed pipe
  and a caller that stalls mid-write cannot hold the decision. The self-test runs the
  hook file directly, as the harness does.
- `readonly` hook: a marker that is not a regular file (a named pipe, a device, a
  socket) or is larger than 64 KiB now denies immediately. Previously a named pipe or
  an endless device at the marker path made the hook hang until the harness killed it,
  which lets the write run, and a pipe preloaded with `{"active": false}` could be read
  as a cleared marker. The hook now checks the file type before opening anything,
  opens without blocking, re-checks the open descriptor, and reads at most 64 KiB;
  `readonly-mode.sh on` refuses a reason too long to fit. The self-test adds those
  cases (including an oversized marker that parses as cleared) and now kills a hung
  hook's whole process group instead of orphaning its child.

### Changed

- Added a verified Codex CLI starter set for `reprobe-stale-premise`,
  `prove-control-binds`, and `prove-deploy-is-live`, with independent
  `$skill-installer` requests, non-overwriting manual local-install guidance,
  and a compatibility contract in CI.
- Quoted `reprobe-stale-premise` frontmatter so it is valid YAML and passes the
  OpenAI skill validator.
- Quoted `goal-prompt` frontmatter so strict YAML loaders stop skipping it (the
  `skills` CLI listed 25 of 26 skills), and added a contract test that parses every
  skill's frontmatter strictly (duplicate keys rejected, matching the CLI's parser)
  instead of only the Codex starter set.
- Documented listing and installing skills with the `skills` CLI, pinned to the
  version verified for Claude Code, including its telemetry opt-out.

## [0.5.1] - 2026-07-24

### Changed

- Normalized punctuation library-wide: every em, en, and horizontal-bar dash (446 occurrences across 37 files) is now a comma, colon, or hyphen. No behavior change. The sweep covers project docs, `SKILL.md` prose, `references/`, and the comments, docstrings, and console strings in `publish-core`; no regex pattern, denylist entry, or test fixture was altered, and the `publish-core` selftests still pass 19/19 and 43/43. Two generator templates (`pre-compact` handoff packs, `incident-as-code` solution docs) were emitting long dashes into every artifact they produced, which this also stops.

## [0.5.0] - 2026-07-08

Catalog has grown from 25 skills to 26.

### Added

- **delegate**: hands a scoped subagent, bulk, or background task to a non-Anthropic model CLI (Codex on a ChatGPT plan, Grok on a metered xAI key, or a free local model via Ollama) so it runs off the Anthropic budget with that vendor's native tool calling, behind a sandbox and env-scrub gate. Shells out to each vendor's own CLI rather than a router-proxy under `ANTHROPIC_BASE_URL` (a proxy corrupts tool calls). Security rails enforced in code: no sandbox-bypass flags, a whitelist environment scrub, absolute-path CLI resolution, and a read-only sandbox default.

## [0.4.0] - 2026-07-06

Catalog has grown from 21 skills to 25.

### Added

- **office-hours**: YC-style product ideation with six forcing questions, wedge and specificity pressure, and a builder brainstorm mode; saves a design doc.
- **investigate**: systematic debugging in four phases with an Iron Law: no fixes without root cause.
- **design-consultation**: a full design-system consultation (aesthetic, typography, color, layout, motion) that produces DESIGN.md as the project's design source of truth.
- **document-release**: post-ship documentation sync; reads all project docs, cross-references the diff, and updates them to match what actually shipped.

## [0.3.0] - 2026-07-06

Catalog has grown from 19 skills to 21.

### Added

- **reprobe-stale-premise**: re-probe any claim you did not just verify before acting on it; a handoff premise, a teammate diagnosis, or a stale registry state is a hypothesis, not a fact.
- **triage-fanout-verdicts**: read multi-agent fan-out verdicts honestly; an abstention or crashed lens is PENDING, never a verdict. Ships a deterministic triage helper.

### Changed

- **learn-capture**: optional confidence/scope calibration metadata on new notes.
- **goal-prompt**: deterministic validation checklist for emitted conditions plus context-economy guidance for the fired run.
- **author-workflow-fanout**: new unbounded-agent-hoard lint rule; the shipped linter gained wrapper-aware no-catch handling (safe and schema-bound wrappers recognized) and hardened numeric handling.
- **scope-guard**: non-goals clarification (write scope, not concurrent-session racing).

## [0.2.0] - 2026-07-04

Catalog has grown from 10 skills to 19.

### Added

- **orion-deep-research**: durable, fact-checked deep research with honest abstention accounting, an independent judge-gate, and persistence of the cited report.
- **oss-loop**: carry an OSS tool from idea to a published release, with a human touching only the irreversible gates.
- **chain-launcher**: surface the exact implement-phase command after a research or decision plan is approved.
- **tools-router**: an auth-aware, low-token index of the CLIs and MCP servers an agent can reach, preferring a working CLI over its MCP.
- **prove-deploy-is-live**: prove a deploy actually serves on its real route, because green CI, docker ps, and /health 200 all lie.
- **prove-control-binds**: prove a gate, hook, monitor, or reaper fires by injecting a synthetic violation and watching it block.
- **design-fail-closed-gate**: author unattended and self-policed gates that fail closed by construction.
- **author-workflow-fanout**: author a multi-agent fan-out correctly, with per-agent error handling, pipeline vs barrier choice, budget and cap loops, and bulk results written to disk.
- **tdd-loop**: drive a spec to a CI-green PR through a self-correcting RED/GREEN/REFACTOR loop where every green binds to an artifact; ships with advisory computational sensor gates (mutation, behavioral, and optional property-based) that RUN rather than read the diff, complementing the inferential reviewer roles, plus a coverage-is-not-a-quality-proxy red flag.

## [0.1.0] - 2026-06-21

Initial public release: 10 skills (gist, goal-prompt, incident-as-code, learn-capture, pre-compact, pre-pr, readonly, scope-guard, ship, x).

[0.2.0]: https://github.com/OrionArchitekton/orion-skills/releases/tag/v0.2.0
[0.1.0]: https://github.com/OrionArchitekton/orion-skills/releases/tag/v0.1.0
