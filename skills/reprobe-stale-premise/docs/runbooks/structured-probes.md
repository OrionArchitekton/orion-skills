---
verified: 2026-11-02
review_after: 2027-02-02
topics: [premise-verification, local-read-only-probes]
references: [../../premise_probes.py, ../../SKILL.md, ../../LICENSE.orion]
---

# Optional local structured observations

## Invocation and input

Run explicitly with Python 3.10+ on a POSIX host supporting descriptor-relative
no-follow reads. Keep the normal manual premise check for Git/PR/runtime checks.
There is no automatic invocation, installation, service or network access.

```bash
python /path/to/reprobe-stale-premise/premise_probes.py \
  --root /absolute/local/source --input /absolute/premises.json
```

A single JSON document has exactly `schema_version: 1` and `premises` (1..32).
Each premise has exactly `id` (unique 1..64 ASCII letters/digits/underscore/hyphen),
`claim` (1..1024 characters) and `probe`. Use public-safe IDs; they are reported.
The helper tests the predicate, not the truth of arbitrary prose in `claim`.

```json
{"schema_version":1,"premises":[{"id":"feature","claim":"The local feature flag is enabled","probe":{"kind":"file_contains","path":"config.txt","expect":"feature=enabled"}}]}
```

| Kind | Required probe keys | Meaning |
|---|---|---|
| `path_exists` | `kind`, `path` | An existing regular file; reads no content |
| `file_contains` | `kind`, `path`, `expect` | Literal UTF-8 substring, 1..1024 characters |
| `file_sha256` | `kind`, `path`, `expect` | Exact lowercase 64-hex SHA-256 of full bytes |

No extra keys are accepted for supported probes. Unsupported kinds (including
shell, command, Git revision, HTTP and mutation probes) return unknown without
source inspection. There is no execution opt-in. Use full-file SHA-256 to pin
local bytes; it does not prove a Git revision, commit ancestry or remote state.

## Paths, bounds and observation limits

Choose a trusted local root explicitly, as an absolute directory. Root ancestors
and source paths cannot contain symlinks or dot/dot-dot components. Source paths
are relative, at most 240 ASCII characters / 16 nonempty components, using
letters, digits, dot, underscore, hyphen and slash. Directories, sockets, FIFOs,
devices and other nonregular targets are unknown. Manifest is a regular file,
maximum 65536 UTF-8 bytes; original manifest path components are preserved and
checked without dot/dot-dot normalization. Source content maximum 1048576 bytes
per probe. One extra
byte detects growth. JSON duplicate keys, nonfinite numbers and malformed inputs
fail closed. Maximum stdout is 65536 bytes; there is no report-file write flag.

The helper opens no-follow, nonblocking descriptors, holds directory descriptors,
checks source metadata before/after reading and re-stats the final name. Ancestor
name/device/inode/type bindings are rechecked; unrelated siblings above the root
do not invalidate observations. Root replacement stays unknown. Detected changes
produce unknown without a partial hash. No source bytes, configuration, Git or
operator state are written. Filesystem access-time accounting may occur on reads.
This is a local observation, not a sandbox, atomic multi-file snapshot, filesystem
integrity verifier or authorization decision. Mount changes, hostile filesystems,
blocking kernel behavior and concealed races exceed its assurance. Recheck close
to action; observations can drift immediately after return.

## Output, monitoring and validation

Output is one JSON report with `schema_version`, `all_confirmed`, `counts` and
`results`. Every result has `premise_id` (null when invalid), `premise_sha256`
(canonical sorted compact JSON), `started_at`, `finished_at` (UTC), `status`,
`reason` (fixed code), and `source` (null when unavailable). Whole-document failures
use null premise ID and the hash of JSON null. Source includes `path_sha256`,
`root_device`, `root_inode`, `device`, `inode`, `size`, `mtime_ns`, `ctime_ns`;
completed content observations also include `sha256`. Correlate the input manifest
with its hash to recheck. Inputs, reports and hashes may themselves be sensitive.
No raw claim, expectation, path, source content or OS exception text is printed.

| Status | Interpretation |
|---|---|
| `confirmed` | Supported predicate matched the bounded observation |
| `drifted` | Readable content refutes the expected literal or digest |
| `missing` | Inspected target/component was absent before opening |
| `unknown` | Invalid, unsupported, denied, changing, oversized or unavailable |

Counts include all four statuses. Only a nonempty, wholly confirmed set produces
`all_confirmed: true` and exit 0. Everything else exits 1; no-refutations is not
all-confirmed. Reasons such as `unsupported_operation`, `missing_source`,
`changed_during_read` and `invalid_document` preserve why a check could not pass.
The CLI's `--help`/argument errors use ordinary argparse behavior (exits 0/2).

Validate using synthetic files under a temporary root, then change/remove one
and verify drifted/missing. Never run private production checks as a self-test.
Keep reports private; manual checks remain available for every omitted operation.

## Rollout and rollback

Adopt only through your normal reviewed source delivery and explicit invocation.
No hooks or scheduling are added. To stop using the helper, stop invoking it and
use the unchanged manual procedure. Reverting the extension's source commit
removes the optional helper/docs while preserving that procedure. This extension
does not expand native Codex qualification or alter the existing installer pin.
