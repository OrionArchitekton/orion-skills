---
name: reassert-guards-on-rewrite
description: "Use when refactoring, porting or replacing a path that enforces authentication, tenant isolation, validation, redaction, idempotency, quotas or scoped-operation limits."
---

# Reassert guards on rewrite

A guard must still control the protected effect after a rewrite. A passing
happy path, matching fields or unchanged guard counts cannot establish that.

## Procedure

1. Identify the original and candidate revisions, guarded entry points and
   protected effects. If either source is unavailable, leave verification
   unresolved. Use the consumer repository's contract and declared checks.
2. Inventory each original safety property. Record its old enforcement site,
   new enforcement site and disposition: preserved, moved, superseded or
   unresolved. Superseded requires an explicit reason and equivalent or stronger
   protection; a lower textual count alone says nothing about safety.
3. Trace every affected entry point to the effect. A moved check must execute
   before the effect on every route. Inspect sibling wrappers, alternate modes
   and direct callers for bypasses. Enumerate gaps outside your authorized scope;
   obtain the needed ownership before repairing them.
4. Exercise each prohibited condition at the actual entry points. Require both
   denial and evidence that no protected effect occurred. Also exercise the
   allowed case. A raised exception after a write is a failed guard.
5. Record commands, revisions, observed effects and remaining uncertainty in a
   guard ledger. For commit-specific claims, execute against source materialized
   from that immutable revision without working-tree overlays; a clean Git
   status can hide changed bytes. Label uncommitted proof with its patch/tree identity, not as proof
   that HEAD contains the change. Re-read the final candidate after repairs.
   Accept only when
   every relevant guard has binding evidence; otherwise report the precise gap.

Textual searches and optional external diff tools are advisory. They can miss
changed ordering, bypasses or semantics, and flag harmless consolidation.
Equal regex/count scores never certify safety. Missing inputs, tool errors and
unrun negative paths are inconclusive, never a clean verdict.

For scoped operations, compare the intended scope, unaffected survivor set and
effective guard configuration before and after. A broader operation requires
separate authority. Missing survivor evidence leaves acceptance blocked.

## Worked example and evidence

[The tenant-write example](examples/guarded_write.py) contains an original
guard, a dropped guard, an unsafe move after the write and a safe move into a
shared wrapper. With Python 3, run it from this directory:

```sh
python3 examples/guarded_write.py
```

For both `api` and `batch`, an allowed write appends once. A denied request must
raise and leave the recorder empty. The unsafe move still raises, with the same
textual guard counts, but has already appended. The safe move guards both paths.
The example is illustrative; apply the same probe to the real consumer boundary.

| Guard | Candidate | Evidence required | Disposition |
|---|---|---|---|
| Tenant equality before write | Dropped | Negative probe appends | Unresolved; reject |
| Tenant equality before write | After append | Raises but appends | Unresolved; reject |
| Tenant equality before write | Shared wrapper | Both paths deny, zero appends; allowed cases pass | Moved; supported |

## Prerequisites and authority

Read access to both revisions and the contract, and authority to run the
consumer's focused checks, are prerequisites. Python 3 is only needed for the
example. There is no bundled safety analyzer or required sibling skill.
This procedure grants no source-write, commit, push, deployment, installation,
service, hook, credential or external-communication authority.

Retain [provenance](PROVENANCE.md) and the [notice](LICENSE.orion) with a standalone copy.
