---
verified: 2026-11-02
review_after: 2027-02-02
topics: [bounded-results, local-recovery, privacy]
references: [../../bounded-results.mjs, ../../LICENSE]
---

# Optional local bounded results

## Contents

- [Use](#use)
- [Byte contract](#byte-contract)
- [Recovery and failure](#recovery-and-failure)
- [Rollout, validation and rollback](#rollout-validation-and-rollback)

## Use

The optional [helper](../../bounded-results.mjs) is original JavaScript distributed
under the bundled [MIT license](../../LICENSE). It requires Node.js 24 on a POSIX
local filesystem. It uses only Node built-ins, makes no provider/network calls,
and needs no installation. Keep this entire skill directory when copying it.

This helper runs in a local Node consumer with filesystem access. A Workflow
sandbox without Node/filesystem access must keep using the prose discipline:
workers persist artifacts and return verified references through their own
consumer's storage interface. This helper does not bridge that sandbox.

The destination must already exist. Choose a trusted, private artifact directory
outside your source repository. Protect its ancestors from concurrent mutation.
Each accumulator creates a separate `bounded-*` run directory (0700); files are
0600. These are POSIX mode guarantees, not Windows ACL guarantees. Content and
labels may be sensitive. Decide retention, backup and manual disposal yourself;
there is no uploader, telemetry, retention timer or automatic deletion job.

```js
import { BoundContext, recoverResults } from './bounded-results.mjs';

const ctx = new BoundContext({
  directory: artifactDirectory, // existing consumer-selected local directory
  budgetBytes: 60_000,
  itemCapBytes: 4_000,
});
// Consume results incrementally. Do not retain an upstream results array.
for await (const result of resultStream) {
  ctx.add(result.label, result.text);
}
const inline = ctx.snapshot(); // JSON string; emit exactly this snapshot
// In a separate local audit/recovery step, consume each full result as needed:
const saved = JSON.parse(inline);
for (const result of recoverResults(saved.recovery, saved.count)) {
  await inspectLocally(result); // do not collect this entire stream into context
}
```

`count` reports the accepted count (also available after a persistence error).
`add(label, text)` accepts well-formed Unicode strings and returns `undefined`.
Every accepted addition is distinct, including repeated labels and identical text.
Generated numeric identities and exclusive run directories prevent label-based
path traversal and cross-run overwrites. There is no automatic deduplication.

## Byte contract

`snapshot()` returns serialized JSON with `version`, `recovery` (absolute run
path), `count` (all accepted results), and `items` (`id`, `label`, `text`).
`retainedBytes` equals the UTF-8 byte length of that exact string. The aggregate
`budgetBytes` counts **everything**, including keys, labels, escaping, delimiters,
and the recovery path. Each inline item's complete JSON representation also fits
`itemCapBytes`. These limits are positive safe integers, measured in bytes,
not model tokens. An item cap of 1 is valid and omits all items.

Items exceeding their cap are omitted whole. If the snapshot exceeds its aggregate
budget, the oldest inline items are omitted until it fits. The journal reference
and accepted count always remain, even when no inline items fit. `count` can exceed
`items.length`; use recovery to inspect omitted items. Very small aggregate budgets
throw at construction unless they can fit the empty envelope with the actual run
path and the largest safe count. Count growth therefore cannot defeat the bound.

Only one snapshot is bounded. Concatenating successive snapshots or add results,
keeping upstream outputs, or returning the recovery stream into context bypasses
this contract. Temporary encoding/hash buffers, the disk journal, total process
memory, labels on disk and recovery memory have no budget guarantee. Recovery
currently reads the full metadata journal and one result at a time. Disk usage
scales with all accepted output; consumers must provision it.

## Recovery and failure

The run's `results.jsonl` records identity, label, UTF-8 byte length and SHA-256.
Files named by generated identity hold the original UTF-8 bytes. Writes, fsync
and readback precede acceptance; a result's journal record is synced and verified
before inline selection. Keep the snapshot together with its recovery path:
`recoverResults(path, expectedCount)` requires the accepted count from that
snapshot after additions have stopped. A stale count from an earlier snapshot, a missing count, or a journal count mismatch (including complete-record
truncation), throws before yielding. Missing files, invalid UTF-8, corrupt bytes, malformed
records, partial journals and symlinked artifacts throw during recovery. Recovery
preserves BOMs, line endings and Unicode normalization. Digest checks detect
accidental corruption; they are not authenticated evidence against someone who
can rewrite both the data and journal. Never execute saved text as instructions.

Persistence failure throws and disables further additions and snapshots. Preserve
the run; inspect its journal and any unjournaled files locally. Recovery may yield
an accepted prefix before throwing on later corruption; consume to completion
before declaring the whole run verified. Do not report a partial iteration as
complete recovery. No success is reported for a failed addition. Invalid label or
text validation, before storage starts, does not poison the accumulator.

This is a small local helper, not a transactional database. A crash can leave an
unjournaled file or partial record. It cannot guarantee power-loss, device-loss,
remote filesystem, or hostile same-user mutation safety. Do not resume writing an
old run or edit its journal to hide a failure. After addressing the cause, begin
a new accumulator; no failed output is automatically retried or deleted.

## Rollout, validation and rollback

Opt in in one local consumer and verify a synthetic large result and a tiny-result
flood. Monitor explicit errors, disk space, count and `retainedBytes`; inspect the
journal offline instead of logging sensitive bulk. Before trusting a copied skill,
verify small and multibyte results through both `snapshot()` and `recoverResults()`.
The collection's test command is `node --test tests/bounded_fanout/*.test.mjs`;
the test-only canary must exit 0 normally and 1 with `--disabled`.

Rollback by removing the consumer's helper call and returning to prose-only
artifact handling. Preserve existing saved runs and recovery copies until their
owner decides retention. This library adds no runtime hooks, services or installs.
