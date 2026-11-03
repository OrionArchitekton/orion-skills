---
verified: 2026-11-02
review_after: 2027-02-02
topics: [orion-skills, claude-code, plugin, loading, rollback]
references:
  - .claude-plugin/plugin.json
  - README.md
  - tests/test_claude_plugin_contract.py
  - tests/test_distribution_contract.py
  - tests/fixtures/distribution/required-files.json
  - specs/optional-claude-plugin-spec.md
  - skills/orion-deep-research/PROVENANCE.md
---

# Optional Claude Code plugin

The plugin is session-local installation convenience for this repository's existing
29 skill definitions. Tested CLI: **Claude Code 2.1.316, Linux/POSIX**. Published
collection/plugin version: [**0.7.1**](https://github.com/OrionArchitekton/orion-skills/releases/tag/v0.7.1).
The published v0.7.0 has no plugin manifest and remains unchanged. A plugin namespace
is not a grant to publish, delegate, install hooks or change settings.

## Load a reviewed clone or archive

Clone the repository and select v0.7.1, or extract that release's source archive
containing the manifest. Keep the whole repository together: skill-only copies are direct
installs, not the plugin. Do not nest the skills under `.claude-plugin/`.

```bash
git clone https://github.com/OrionArchitekton/orion-skills.git "orion skills"
cd "orion skills"
git checkout --detach 13ee89202f6a730e8b79326343bb885d0a82eda5 # v0.7.1
claude plugin validate . --strict
```

The checkout selects the published release commit. For a tar/zip source archive,
extract it first and point at the resulting directory holding `.claude-plugin/`
and `skills/`. Loading an extracted directory is the qualified archive route;
direct zip loading is not qualified here.

Run from the project you want to work on, using an absolute, quoted plugin path:

```bash
claude --plugin-dir "/absolute/path/to/orion skills"
```

This flag loads the directory for that invocation without a marketplace install.
Do not copy the whole plugin into a global skills directory as part of this route.
Keep the plugin checkout separate from the consumer project. Direct skill copying
and the pinned skills CLI remain documented in the README.

## Inspect and invoke

Offline inspection on the tested CLI needs no prompt, login or model call:

```bash
claude --plugin-dir "/absolute/path/to/orion skills" plugin details orion-skills
```

Expected inventory: **29 skills, 0 agents, 0 hooks, 0 MCP servers, 0 LSP servers**.
This lists component IDs; it does not execute their procedures or verify their
external prerequisites. During an authorized interactive session use
`/orion-skills:pre-pr` or `/orion-skills:ship`. All bundled IDs use that prefix.
Any `/pre-pr`, `/ship`, `/x`, etc. reference in a bundled skill or reference document
means the corresponding `/orion-skills:<name>` when you select the bundled copy.
A bare command can instead select a separately installed skill; do not use bare
names to infer which source ran. Built-in commands such as `/compact` stay built-in.
The existing operator-only flags for `readonly`, `gist` and `ship` are retained.
No additional allowed-tools or default permission rules are supplied.

The native validator may suggest a marketplace install line and report a missing
listing icon as a directory-profile finding. Those are listing advice, outside
this loading route; no marketplace is owned or provided by this repository.
Use strict manifest validation without the directory-submission profile.

## Helper paths and compatibility

Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` in loaded plugin skill Markdown.
It is not an environment variable to assume exists in a Bash tool command or a
manual terminal. Use the `# Plugin:` assignment shown by the loaded skill instead
of its direct-install assignment. In a manual terminal substitute the actual
absolute plugin directory yourself. Preserve double quotes around helper paths,
especially for directories with spaces. Keep durable state/config outside the
plugin directory so selecting another version preserves it.

| Skills | Qualified package behavior and boundaries |
| --- | --- |
| `pre-pr`, `ship`, `apply-review-findings`, `reassert-guards-on-rewrite`, `incident-as-code`, `learn-capture`, `goal-prompt`, `pre-compact`, `oss-loop`, `chain-launcher`, `prove-deploy-is-live`, `prove-control-binds`, `design-fail-closed-gate`, `reprobe-stale-premise`, `triage-fanout-verdicts`, `investigate`, `document-release` | Definitions and accompanying assets are discoverable and retained. Prose procedures use the active host's tools and approvals. A synthetic pre-PR scenario exercises the prose checklist; this is not native model execution of every skill. |
| `readonly` | Quoted plugin helper path and synthetic marker lifecycle qualified. No enforcement hook is registered by loading. Deliberate hook opt-in and denial canary required; Bash writes remain outside its matcher. |
| `x`, `gist` | Quoted plugin helper paths and local redaction fixtures qualified. Existing arm flags, caps, denylist and approval requirements remain. No send or external fetch qualifies the plugin; loading does not create arm flags. Never arm a publisher just to test packaging. |
| `grokbot` | Quoted bundled script location checked. No webhook task or desktop action exercised. Existing credentials, platform setup and human outward-action decisions remain necessary. |
| `scope-guard`, `tools-router` | Procedures are discoverable; paired hook/recon setup remains separate and opt-in. Loading alone provides no structural protection or scheduled recon. |
| `author-workflow-fanout`, `tdd-loop` | Bundled helpers retained; their Workflow/native host prerequisites are not provisioned. Existing offline helper checks remain applicable. |
| `office-hours`, `design-consultation` | References and notices retained; host tool capabilities still determine execution. Loading does not install browser tooling or write profiles. |
| `orion-deep-research` | Requires a compatible Claude Workflow tool and output prerequisites. Native execution remains unqualified; retain its provenance/evidence limits. Plugin discovery does not supply that executor. |
| `delegate` | Discoverable, but its documentation still points at a direct-install helper path. Plugin-only execution is not qualified: use its existing deliberate direct installation if needed. Do not alter its executable-selection policy to make packaging pass. Hardening stays deferred. |

All 29 definitions being discovered is not a claim that all 29 workflows execute
from a plugin-only setup. Codex support remains the three pinned verification
skills in the README. This qualification establishes no Cowork, browser or native
Workflow compatibility. Do not edit the plugin cache to provide credentials,
state, hook registrations or additional permissions.

## Validate and monitor a chosen copy

Before loading a new version, validate the manifest and inspect the inventory
using the commands above. Run the existing distribution and standalone checks on
the extracted directory, using the repository's pinned test requirements and a
disposable HOME/config/cache/TMPDIR. Clear inherited Git overrides and give any
Git fixture its own discovery ceiling outside operator-state repositories. See
the source-release runbook for the complete existing offline suite.

The focused package test executes documented helper assignments in a cache-shaped
path with spaces, with synthetic readonly markers and denylist fixtures. Native
inventory and manifest validation are separate evidence; that test does not
simulate native invocation or silently install a plugin to obtain discovery.
For a real authorized session, confirm the namespaced command and loaded helper
path identify the chosen version before relying on its behavior. Validate any
separately registered control with a denial canary before calling it protective.

## Update, removal and rollback

Updates are explicit. Review a new commit/archive in a separate directory, repeat
validation/inventory, then start a new session with its absolute path. Keep the
previous reviewed directory for rollback. The manifest version is metadata; it
does not fetch code or reserve a collection release. No `plugin update` or
marketplace path is implemented or promised here.

To remove this loading path, end the session and omit `--plugin-dir` from the next
invocation (and from any wrapper you deliberately created). With no persistent
installation made by this route, there is no marketplace uninstall to run.
To roll back, select the prior reviewed directory on the next invocation.
Direct skill installs, external configuration, durable ledgers and deliberately
registered hooks are independent; this flag does not remove or restore them.

## Reference basis

Checked against the installed CLI rather than assuming current docs match it:
[plugin overview](https://code.claude.com/docs/en/plugins),
[manifest/layout/substitution reference](https://code.claude.com/docs/en/plugins-reference),
[distribution options](https://code.claude.com/docs/en/plugins/publish).
