---
verified: 2026-11-02
review_after: 2026-12-02
topics: [delegate, executable-selection, compatibility]
references:
  - skills/delegate/scripts/delegate.py
  - skills/delegate/SKILL.md
  - specs/delegate-executable-selection-spec.md
  - tests/test_delegate_resolution_contract.py
---

# Delegate executable selection and compatibility

This source candidate rejects workspace-controlled CLI selections. It is not a
binary identity check, release, installation or permission to delegate.

The first executable selected by Python's native `shutil.which` must be absolute
and outside the workspace. Every traversed path, symlink and exposed junction
is checked. An unsafe first selection raises `DelegateError`; it does not select
a later CLI. Dispatch checks that same launcher again after argv/environment
construction, immediately before spawning. Its original path remains argv[0],
so multicall launchers keep their command identity. Ordinary outside installations
do not require a location allowlist, account database or new trust file.

The workspace is the nearest enclosing `.git` marker directory (including a
linked worktree's marker file), otherwise cwd. A nested repository defines its
own workspace; non-Git callers must start at their intended root. Caller cwd,
marker selection, OS, external installation directories and installers are
trusted. Group-writable installations remain accepted: other writers to those
installations are therefore trusted too. Do not treat this check as an ownership
or permissions policy.

## Compatibility matrix

All process evidence below uses disposable fixtures on Linux, Python 3.12.12.
Names such as `usr/bin` are layouts beneath a temporary root, not modifications
to system directories. No actual package manager, native model CLI or provider
was run. Passing a shim fixture proves launcher/argv handling, not its real
manager's dependency resolution.

| Platform / install shape | Source behavior | Evidence / qualification boundary |
| --- | --- | --- |
| Linux system `/usr/bin`, `/usr/local/bin` shapes outside workspace | Accepted | Actual fixture process runs, regular file, symlink and shell shim variants |
| Linux user `.local/bin` shape | Accepted | Same actual fixture process variants |
| Custom absolute prefix, including spaces | Accepted | Same actual fixture process variants; argv list needs no shell escaping |
| Group-writable custom file and directory | Accepted | Actual fixture process; ownership/mode enforcement deliberately absent |
| nvm versioned node/bin shape | Accepted | Actual fixture process variants; no nvm invocation |
| Volta bin / multicall symlink shape | Accepted, selected name retained | Actual fixture variants and basename-sensitive shell canary |
| asdf and mise shim shapes | Accepted | Actual fixture shell shim and symlink variants; no real manager invocation |
| Outside symlink chain and `link/../name` | Accepted if every traversed hop stays outside | Actual fixture run preserves kernel traversal and selected argv[0] |
| Workspace executable, relative or empty PATH first hit | Denied | Actual harmless disabled-control canary plus no-subprocess assertions |
| Outside launcher into/through workspace, including return outside | Denied | Real Linux symlinks, parent symlink and traversal fixtures |
| Launcher replaced by workspace link after argv construction | Denied at final check | Deterministic fixture replacement; no atomic exec guarantee |
| Missing/broken/cyclic/non-executable/directory selection | Denied | Resolver/subprocess seam; no provider fallback |
| macOS and Homebrew prefixes | No POSIX-only policy restriction | Native macOS execution, case-insensitive volume behavior and actual Homebrew launchers NOT RUN |
| Native Windows, drive/UNC paths, PATHEXT, `.exe` / `.cmd` | Uses native Path/os/shutil APIs | Native Windows process creation and launcher behavior NOT RUN; no Windows support qualification added |
| Filesystem identity alias / Windows junction branch | Denied when workspace-controlled | Mocked Linux structural tests only, not native case-insensitive/reparse-point verification |
| Direct helper copied to another absolute location | Source path independent | No plugin-only helper qualification added |
| Plugin-only helper resolution | Existing limitation retained | Usage still requires the deliberate direct-install helper path; plugin load grants no execution permission |

## Validate and interpret denials

From a disposable checkout, with isolated HOME/config/cache/TMPDIR, run:

```bash
python -m pytest -q tests/test_delegate_resolution_contract.py
```

Use the pinned test requirements for the full source suite and Node 24 for the
bundled Node tests. The focused tests construct harmless fake CLIs and never call
providers. A failed resolver raises `DelegateError` before subprocess invocation;
fanout reports that failure as pending. The command-line entrypoint exits nonzero.
Check the first PATH match and each symlink destination from the intended workspace
before approving a real run. A successful dry-run only checks current selection;
it grants no execution permission and does not guarantee later filesystem state.

Do not use a real model call as a security regression test or change operator
credentials, hooks, plugin caches or global installs to make tests pass.

## Compatibility decision and migration

Previously, any `shutil.which` result was converted to an absolute path. That
accepted workspace-local CLIs and relative PATH hits. This candidate intentionally
rejects those cases, even if the operator installed them deliberately. Under this
library's SemVer rule it is a **MAJOR** change: recommend 1.0.0 if this default is
approved, rather than publishing it as 0.7.2. No version/tag is reserved and the
plugin manifest remains at the released version. Native platform qualification
remains a separate prerequisite for any expanded support claim.

For an affected intentional install, first inspect a dry-run from the intended
workspace and choose an existing external CLI with an absolute PATH entry. If
none exists, the operator must separately authorize installation outside the
workspace. Merely putting an outside symlink in PATH does not migrate a target
that still lives inside the workspace. There is no automatic trust override or
silent fallback. Keep the released source until the compatibility decision is
approved; do not change Codex qualification pins or research/Workflow prerequisites.

## Limits, rollout and rollback

External launchers, interpreters, shim bodies, plugins and dependencies are trusted
and not inspected. Inherited child PATH/HOME access remains unchanged. A launcher
may itself load workspace code; path validation cannot certify its contents.
Hard-link aliases, mount/bind aliases and arbitrary same-user path/content changes
after the final check are outside this guarantee. A hostile same-user process can
still win a check-to-exec race. Use an OS sandbox and vetted installations for a
stronger boundary.

After review, keep this as source-only until separate merge/release approval and
an explicit compatibility decision. Monitor resolver denials in authorized runs;
do not auto-retry through a different CLI or relax the check. No service, timer,
provider or harness activation is needed. Before merge, rollback is closing the
candidate PR; after an independently approved merge, rollback is a reviewed revert
of its source commit. Preserve existing release tags and historical pins.
