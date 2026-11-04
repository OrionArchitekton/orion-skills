# Delegate executable selection

## Contract and threat model

An authorized caller chooses Codex or Grok. The operator controls PATH and installs
those CLIs outside the workspace. Repository content is untrusted: an attacker may
plant executable files and symlinks anywhere in that workspace, including paths
referenced by PATH or by an outside launcher. The OS, Python, operator environment,
external installation directories and installers are trusted. This check does not
authenticate publisher identity, inspect launcher contents or dependencies, prevent
hard-link aliases, or defeat same-user mutation between the last check and exec.

The workspace is the nearest enclosing directory with a `.git` marker (directory
or worktree file), or the current directory when there is no enclosing marker.
Nested repositories are separate workspaces; non-Git callers must start at the
workspace root. Marker selection and the working directory are caller inputs;
a hostile process changing them is outside the contract. This is path selection
hardening, not a filesystem sandbox or an installation allowlist.

## Scenarios and acceptance criteria

1. A workspace-planted first PATH hit is denied before subprocess invocation.
   Empty and relative first selections, absolute workspace selections, workspace
   subdirectories, outside symlinks through or into the workspace, broken links
   and symlink loops all fail with DelegateError. An unsafe first hit is not
   replaced by a later executable. A disabled-check canary must prove the same
   harmless planted fixture would otherwise execute.
2. Outside absolute system, user, custom and group-writable installations remain
   selectable. Ordinary files, nvm version directories, Volta multicall links,
   asdf/mise shims, paths containing spaces and outside symlink chains retain
   the selected absolute launcher as argv[0]. Validation must follow filesystem
   traversal without collapsing `..` across symlinks. Launcher identity must not
   change to the resolved target's basename.
3. The selected path is checked again immediately before subprocess invocation,
   without another PATH lookup. Replacing a launcher with a workspace symlink
   between argv construction and that check is denied. Changes after the last
   check are explicitly outside the guarantee; immutable execution is not claimed.
4. Provider selection, argv suffixes, environment whitelist, sandbox defaults,
   stdin handling, timeout/fanout results and bypass-flag denial retain their
   existing contracts. Ollama's HTTP path is unchanged.

## Platform and compatibility decision

Use native pathlib/os/shutil path handling without POSIX account databases or
fixed installation roots. Linux fixtures qualify actual local process execution;
macOS and native Windows execution remain unqualified until tested there.
Simulated Windows path checks do not establish Windows process support.

Rejecting workspace-local and relative selected installs breaks previously
accepted behavior. Recommend a MAJOR release (next major: 1.0.0), subject to the
maintainer's compatibility decision and separate release approval. No version
is reserved or bumped here. Migration means deliberately choosing an existing
external installation and absolute PATH entries, or having the operator install
one separately; there is no automatic installation or trust-file override.

Plugin helper relocation remains outside this change; the documented direct
installation helper is still required. Loading a skill grants no execution right.
Research prerequisites and existing Codex qualification pins remain unchanged.

## Test seam and sequence

Use the resolver-to-subprocess seam: disposable executable fixtures for harmless
invocation/denial, with recorded argv/stdin/env and no real providers. Sequence:
workspace first-hit denial and disabled canary; outside launcher compatibility
and symlink traversal; pre-spawn path replacement and unchanged provider controls.
The compatibility matrix distinguishes actual Linux fixture runs, structural
checks, and native platforms that were not run. Full source CI checks are offline
with isolated HOME/config/cache/TMPDIR and bounded Git discovery.
