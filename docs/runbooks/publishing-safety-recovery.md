---
verified: 2026-11-02
review_after: 2027-02-02
topics: [publishing, redaction, cap-ledger, recovery]
references:
  - skills/x/publish-core/redactor.py
  - skills/x/publish-core/cap_ledger.py
  - skills/gist/publish-core/gist_client.py
  - tests/test_publish_safety_contract.py
---

# Recover a blocked publishing helper

A redactor configuration failure returns exit 3. Cap state that cannot be read,
parsed or validated returns exit 5. Neither failure permits a send or reserves
a slot. This guide does not authorize publication, changing arm flags or retries.

## Diagnose and preserve

Stop new sends while investigating. Preserve the denylist or ledger with its
permissions before repair. Keep these backups private: they may contain private
rules or usage evidence. Do not paste raw configuration into reports.

For redaction, inspect the reported failure class and line locally. The default
custom denylist may be absent; an explicit `X_DENYLIST_FILE` is required. Correct
its path, permissions, UTF-8 encoding or invalid regex. The supported format is
one Python regex per non-comment line, not a directory or structured rules object.
Do not remove a configured rule or unset its path merely to bypass a refusal.

For caps, preserve damaged bytes. Reconcile usage from known receipts and native
published state before restoring a trusted ledger. Buckets use valid UTC dates
(`YYYY-MM-DD`) or ISO weeks (`YYYY-Www`); counts are nonnegative JSON integers in
surface-to-count objects. Shared ledgers may contain other surfaces: retain them.
Do not delete state, replace it with `{}`, lower counts or discard history to
make a reservation pass. If consumption cannot be established, leave sending
blocked and obtain the operator's decision. An absent first-use ledger is valid
only when no prior usage has been lost.

## Validate and monitor

Run the affected bundled selftest with temporary HOME/config/state and no live
credentials. Run `python -m pytest tests/test_publish_safety_contract.py` in the
source checkout. Check the real candidate with `redactor.py --check` and inspect
cap state read-only with `cap_ledger.py check <surface>` before any separately
authorized send. Every nonzero guard status blocks continuation. Observe that
denied attempts leave ledger bytes unchanged and produce no new public object.

A timeout or error after a send started keeps its reservation. Verify the native
result of that original attempt and preserve its receipt; never automatically
retry, release its slot or create a replacement. There is no automatic refund.

## Rollback

Before deploying these source changes, preserve the previous package and private
configuration. If a repair must be undone, stop sends and restore the trusted
backup while preserving all later consumption evidence. Do not roll back safety
code to bypass a refusal. An unresolved state or protection failure stays blocked
until the operator has reconciled it. This source task performs no installation.
