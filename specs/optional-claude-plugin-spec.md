# Optional Claude Code plugin

## Outcome and terminology

The **plugin** is an optional session-local loading path for the existing skill
collection. A **direct install** copies an individual skill to a harness skill
directory. Both consume the same skill source and retain their own invocation
names. Loading is not permission to execute a skill or arm its controls.

## Scenarios and acceptance criteria

1. A user loads a clone or extracted source archive as a plugin. Claude Code
   validates its manifest and discovers the collection under `orion-skills`.
   All 29 skill definitions, bundled helpers, standalone notices, licenses and
   provenance remain present. No duplicate skill tree or external symlink is used.
2. A user invokes a prose skill with `/orion-skills:pre-pr`. Cross-skill references
   such as `/ship` mean `/orion-skills:ship` for the bundled copy. Direct installs
   retain `/pre-pr` and `/ship`. Existing operator-only frontmatter is preserved.
3. A user relocates the package, including to a cache-shaped path with spaces.
   The readonly helper and the x/gist/grokbot command paths locate bundled files
   from the loaded skill directory rather than a presumed global installation.
   Manual copy instructions remain available. No executable policy changes occur.
4. Loading adds no hooks, MCP servers, services, credentials, telemetry,
   updaters or permission grants. Publishing stays disarmed; hook-dependent
   controls require separate opt-in and canary verification. Research still needs
   a compatible Workflow tool and its native execution remains unqualified.
   Delegate hardening stays deferred and its existing direct-install path is a
   documented plugin limitation rather than a new supported execution claim.
5. A user updates or removes this loading path explicitly by selecting another
   reviewed checkout/archive or omitting the session flag. There is no marketplace
   catalog, installation by marketplace name, or automatic update promise.
   The published v0.7.0 and all three Codex qualification pins are preserved.

## Test seam decision

Use native Claude Code manifest validation and offline component inventory as the
primary consumer seams where supported by the tested CLI. Use existing distribution
and standalone contracts on relocated archives plus synthetic readonly helper
execution to cover retained assets and path quoting. A static catalog audit is
supporting evidence, never native discovery. No model/provider calls, publishing,
delegation or operator harness installation are allowed for qualification.

## Scope and limitations

Qualification targets Claude Code 2.1.316 on Linux/POSIX. Component discovery does
not establish successful execution of every skill. Codex support remains the
existing three-skill starter; Cowork, browser and native Workflow support are not
established. Proposed next collection/plugin version is 0.7.1, subject to later
release approval; no version is reserved by this source change.
