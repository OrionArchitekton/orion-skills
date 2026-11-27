---
name: prove-control-binds
description: "Use when declaring any control 'armed', 'protecting', 'green', or 'done', or when auditing one: gates (pre-commit/pre-push hooks, CI merge gates, secret scanners), timers, reapers/GC, monitors/alerts, capture hooks. Symptoms: 'the hook is installed', 'CI is green', 'the monitor shows OK', 'the reaper ran without errors', 'the gate passed' asserted without ever watching the control FIRE against a violation. Green has two indistinguishable causes: nothing to catch, or catching nothing."
---

# Prove The Control Binds

## Overview

A control is proven by watching it FIRE against a deliberate violation,
never by watching it stay green. Silent no-op controls pass every casual
check: the hook runs (and scans nothing), CI passes (and runs a subset),
the monitor is OK (and its producer aged out), the reaper exits 0 (and
selected nothing). A recorder hook that dies silently while green can lose
a day of captures before anyone notices; this skill is the canary-first
audit that catches that class.

## When to use

- Before reporting any gate/timer/automation "armed", "protecting",
  "capturing", or "done".
- When auditing existing controls, closing a hardening arc, or
  decommissioning a producer a monitor watches.
- NOT for authoring a new gate (that is design-fail-closed-gate) and NOT
  for deploy liveness (that is prove-deploy-is-live); this PROVES an
  existing control fires.

## Procedure

1. Name the negative path: the exact input or state the control must
   block, flag, reap, or alert on. If you cannot name it, the audit
   cannot pass.
2. Inject a canary: a synthetic violation in a sandbox or reversible
   form (fabricated secret assembled from fragments, synthetic drift,
   a fake orphan, a silenced producer, a skipped capture).
3. Watch the control FIRE from its own output: blocking exit code, alert
   event, reap log line, BLOCKED message. Your inference that it "would
   have" fired does not count.
4. Probe the binding seam: is the control actually in the execution
   path? (See the no-op shapes table.)
5. Reapers/trimmers/GC: selection-model check. Run once against the
   KNOWN live leak and require acted-on count > 0. "Armed + green +
   reaped 0" over a real leak is an alibi, not remediation.
6. Record the canary proof (command + output) in the arc or runbook
   before declaring armed.

## Known silent-no-op shapes

| Shape | Mechanism |
|-------|-----------|
| Shadowed hook | `core.hooksPath` (global) makes `.git/hooks/*` dead code |
| Empty pathspec | `git diff -- '**'` / wrong-dir pathspec silently matches nothing |
| Subset CI | required check runs a file list; new/moved tests never gate |
| Vacuous skip | `importorskip` / conditional skip makes the gate pass without running |
| Invisible failure | hook writes stderr + exit 0; harness shows nothing; capture silently dead |
| Aged-out monitor | Alertmanager/monitor OK while the producer stopped reporting |
| Reaper alibi | selection/liveness model spares everything; exits green having reaped 0 |
| Relative gate | gate compares candidate vs baseline only; absolute failures launder through |

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "It ran without errors" | So does a control that scans nothing |
| "The hook is installed and executable" | Installed is not invoked; probe the resolution path |
| "CI is green" | Green subset CI is a hermeticity hole, not protection |
| "The monitor shows OK" | OK-state persists after the producer dies |
| "I read the code; the logic is right" | The seam, not the logic, is where controls die |
| "A canary is overkill for this small gate" | The canary takes one minute; the silent no-op can cost a day of captures |

## Red flags

- The word "armed" or "protected" in your report with no canary command
  beside it.
- An audit that only exercised the happy path.
- A reaper/trimmer declared working with acted-on count = 0.
- Declaring a monitor healthy without probing its producer.

## Related

Siblings in this collection: **design-fail-closed-gate** (authors the gate);
**prove-deploy-is-live** (deploy liveness). If the control was recently
refactored or ported, first confirm the guard survived the rewrite before
spending a canary to prove it binds.

## Boundary

This is the auditing discipline, not a tool. Wire the canary in your own
harness: the injection form (sandbox, reversible, or fabricated-from-fragments),
the block signal you watch for (exit code, alert event, reap log line), and
where you record the proof (arc note, runbook, PR) are your repo's mechanics.
The discipline is invariant: name the negative path, inject it, and watch the
control fire from its own output before you call it armed.
