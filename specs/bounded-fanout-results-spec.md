# Recoverable bounded fan-out results

The optional JavaScript helper lets a local Node.js consumer publish one bounded
inline snapshot while preserving every accepted result in a consumer-selected
local destination. Existing prose-only workflows remain supported. This is a
local result accumulator, not a Workflow sandbox filesystem adapter or service.

## Observable scenarios and acceptance

1. **Retain before returning.** Adding a well-formed Unicode string stores its exact
   UTF-8 bytes and a journal record containing its label, identity, byte length and
   SHA-256 digest. Successful additions recover in arrival order after the original
   accumulator is discarded. Empty strings, duplicate labels and duplicate content
   remain distinct results; labels never become filenames.
2. **Bound one snapshot.** The budget unit is UTF-8 bytes of the complete serialized
   JSON snapshot, including recovery reference, count, keys, labels, escaping and
   punctuation. Each included item, serialized as JSON, also fits the item cap.
   Oversized items and oldest items under aggregate pressure are omitted whole
   from the snapshot; their originals remain in storage. Even a flood of tiny
   results fits because only one journal reference survives in the envelope.
   Neither a model token bound nor a whole-process memory/disk bound is claimed.
3. **Fail explicitly.** Budgets must be positive safe integers. The aggregate budget
   must fit an empty envelope with its actual recovery path and the largest safe
   count. Invalid budgets/labels, ill-formed Unicode, unsupported destinations,
   write/readback/sync/journal failures produce errors, never successful truncation.
   A persistence failure makes the accumulator unusable; preserve its files for
   inspection and start a new run only after handling the error.
4. **Recover with integrity.** Recovery requires the saved snapshot count, rejects count mismatch before yielding,
   and validates sequential identities, journal
   shape, byte lengths, SHA-256 and valid UTF-8. A missing, corrupt, partial or
   symlinked artifact produces an explicit error. Independent accumulators use
   exclusive private run directories so concurrent writes cannot overwrite one
   another. Storage uses generated filenames inside the selected destination.
5. **Qualify the control.** The same synthetic stream overruns the documented
   snapshot budget with bounding disabled and fits when enabled; both runs retain
   all original results. Tests include small, large, multibyte and escaped text,
   a many-result flood, duplicate labels, corruption and deterministic persistence
   failures. A standalone skill copy includes the helper, usage guide and MIT notice.

## Test seam and limits

Use the public `BoundContext.add()` / `snapshot()` and `recoverResults()` boundary
under Node's built-in offline test runner, with fixture-owned temporary directories.
No provider or Git fixture is needed. The test-only disabled control wraps the same
persistence boundary, replacing only inline selection. Filesystem errors are
injected at the Node filesystem seam; they must exercise real error propagation.

The destination must already exist on a trusted local filesystem. The consumer
controls its parent directories and prevents concurrent hostile filesystem mutation.
Run directories are mode 0700 and artifacts mode 0600 on POSIX; no Windows ACL
promise. File and journal fsync plus readback precede success; this is not a
transactional database or a guarantee against power loss/disk loss. A crash can
leave unjournaled files; recovery never silently accepts a partial journal.
Consumers own access control, retention, backups and manual disposal. There is no
automatic upload or deletion. Saved results and labels can contain sensitive data.

Only the latest snapshot is budgeted. Accumulating old snapshots, returning all
recovered results into context, retaining upstream arrays, or serializing the helper
object defeats that boundary. Process results incrementally and emit one snapshot.
