# Changelog

All notable changes to the orion-skills library. This project follows Semantic
Versioning (https://semver.org): adding a skill is a MINOR bump, a non-breaking change to
an existing skill is a PATCH, and removing or breaking a skill is a MAJOR bump.

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
