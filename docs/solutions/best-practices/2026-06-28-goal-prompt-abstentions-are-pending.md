---
title: Goal prompt verifier abstentions stay pending
verified: 2026-06-28
review_after: 2026-09-28
topics:
  - goal-prompt
  - verifier-fanout
  - regression-guard
references:
  - skills/goal-prompt/references/prompt-scaffold.md
  - tests/test_goal_prompt_scaffold_contract.py
---

# Goal prompt verifier abstentions stay pending

## Root Cause

The public goal-prompt scaffold did not carry the runtime scaffold's
three-state verifier guidance. A failed, null, or rate-limited verifier lens
could be treated like ordinary negative evidence, or dropped by a
`filter(Boolean)` cleanup, instead of remaining visible as unfinished work.

## Durable Lesson

Verifier fan-out needs an explicit abstention state. Treat unavailable verdicts
as `PENDING`, rerun that lens independently, and report the pending count until
it reaches zero. A synthesis step should not manually turn missing evidence into
ship or refute.

## Validation

`tests/test_goal_prompt_scaffold_contract.py` pins the public scaffold to the
three-state pattern and rejects the silent-drop `.catch(() => null)` idiom. The
GitHub Actions `tests` workflow runs the contract on every pull request.
