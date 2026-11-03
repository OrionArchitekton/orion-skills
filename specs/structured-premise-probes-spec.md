# Optional structured premise probes

## Outcome and test seam

Keep the manual premise-check procedure usable. An operator may explicitly invoke a
standalone Python helper against a chosen local directory to recheck bounded
premises. It grants no execution, mutation, publication or native-host qualification.
The existing qualified three-skill contract and installer pin remain unchanged.

Decision: exercise the public JSON CLI end to end in isolated temporary directories;
use direct module calls only for deterministic read-error and race injection. No
private orchestration, installed skills, provider or network service is involved.

## Contract

Input is UTF-8 JSON with exactly `schema_version: 1` and `premises`, a list of
1..32 objects. Each premise has exactly `id`, `claim`, `probe`. IDs are unique
1..64 ASCII letters/digits/underscores/hyphens. Claims are nonempty strings of at
most 1024 characters. They are descriptions, not executable instructions. A probe
has `kind` and root-relative `path`, plus `expect` for content checks:

- `path_exists`: confirms an existing regular file (no directory inventory).
- `file_contains`: literal nonempty UTF-8 substring of at most 1024 characters.
- `file_sha256`: exact lowercase 64-hex SHA-256; pins complete file bytes.

Paths are at most 240 ASCII characters, at most 16 nonempty components, using
letters, digits, dot, underscore, hyphen and slash. Absolute paths, dot/dot-dot
components, all symlinks (including root ancestors), nonregular inputs and
special devices are unavailable. A missing inspected file/component is `missing`;
an unavailable root is `unknown`. Roots must be explicit absolute directories.

Only bounded local descriptor reads and metadata inspection are allowed. No
commands, subprocesses, external calls, Git discovery, credential handling,
source writes, recursive traversal or permissive mode. Git/PR/runtime/operator
checks in the manual procedure remain manual. Unsupported kinds return `unknown`
with `unsupported_operation` and do not inspect the proposed source.

## Results and aggregation

Every result carries the public-safe premise ID (or null if invalid), canonical
premise SHA-256, UTC observation start/end, status, fixed reason code and source
identity when available. Do not echo claim, expectation, input path, file contents,
exception text or absolute root. Source metadata includes path SHA-256, opened
root device/inode and file device/inode, size, mtime/ctime nanoseconds; completed
content reads include content SHA-256. These are local evidence, not a signature
or authorization, and may still be sensitive. Keep reports private as appropriate.

Statuses: `confirmed`, `drifted` (refuted by readable differing content), `missing`
(target absent), `unknown` (invalid, unsupported, denied, oversized, nonregular,
undecodable, changed during read, unavailable observation). A file's existence
never confirms the prose of a broader claim. No content observation is inferred
from missing/unknown. Every probe is freshly evaluated; no cached trust.

The report carries counts for all four statuses. `all_confirmed` is true ONLY for
a nonempty valid set where every result is confirmed. CLI exits 0 only then;
otherwise 1. Invalid whole documents produce an explicit unknown report and exit
1, never a traceback or an empty success. Duplicate JSON keys and nonfinite JSON
numbers are invalid. Malformed individual premises stay visible as unknown;
duplicate IDs invalidate the whole document to prevent ambiguous attribution.

## Bounds and stability

Manifest input is a regular non-symlink file limited to 65536 bytes. Content reads
are limited to 1048576 bytes per source; at most one extra byte detects growth.
Existence reads no content. Output is at most 65536 UTF-8 bytes, with fixed reason
codes and bounded identifiers, metadata and hashes. Unsupported POSIX descriptor
features return unknown rather than falling back to unsafe reads.

Descriptors use no-follow and nonblocking flags. Hold directory descriptors;
compare directory and file metadata before/after reads and re-stat the final name.
Detected replacement, disappearance, resize or metadata change returns unknown,
without publishing a partial digest. Observation is a bounded local snapshot,
not an atomic multi-file transaction or a promise of future stability. Hostile
filesystems, mount changes, kernel behavior and perfectly concealed races exceed
this helper's assurance; use trusted local regular files and recheck before action.

## Independently demoable scenarios / acceptance

1. A regular file with the expected literal/digest confirms, with identity and time
   but no raw content. Changed content drifts; rerunning observes new bytes.
2. Missing file and missing parent report missing. Denied reads, invalid UTF-8,
   directories, symlinks, FIFOs/devices, oversized input/content and detected races
   report unknown promptly; sources remain unmodified.
3. Mixed confirmed/drifted/missing/unknown results retain every distinction.
   Confirmed plus unknown, unsupported-only, empty and malformed sets cannot pass.
   Shell/string/Git/HTTP probes never execute or call out, regardless of extra flags.
4. A temporary standalone skill copy includes its helper, contract/runbook and MIT
   notice; runs without the repository or private state. All existing offline
   entrypoints pass. Catalog stays at 29 skills, manual steps and pin unchanged.

## Provenance and delivery

Implementation, fixtures and helper documentation are independently authored for
this public MIT repository. Private recon material is read-only design evidence;
its redistribution rights are unconfirmed, so no implementation/text is copied.
Research release hold and delegate deferral remain intact. Source commits only;
release, installation, provider use and runtime activation require separate authority.
