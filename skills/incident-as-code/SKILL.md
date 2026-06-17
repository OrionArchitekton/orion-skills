---
name: incident-as-code
description: Use when an incident/outage has been root-caused and resolved (or a postmortem is requested) — closes the incident by committing a solutions doc, and a runbook when the class is recurrent, into the AFFECTED repo. Triggers — "close the incident", "write it up", "postmortem", incident resolved, root cause found after an outage. An incident is NOT closed until the affected repo carries the artifact.
---

# Incident-as-Code — Close the Loop in the Affected Repo

Incident knowledge belongs in the repo that experienced the incident — versioned,
agent-agnostic, discoverable. Agent memory indexes; the repo owns. (If your project
has a runbook-persistence doctrine, this skill is its mechanism.)

## Preconditions

1. **Root cause is known.** If not, STOP and root-cause it first (a systematic
   debugging / investigation pass): no fixes, and no postmortems, without root
   cause. This skill is the terminal Document phase, not a replacement for
   investigation.
2. **The fix is verified** by independent runtime verification. Don't document an
   unverified fix as a solution.

## Steps

### 1. Identify the affected repo

The repo whose code/config/contract failed — not necessarily where the symptom
surfaced. If your project maintains a registry of repo homes, resolve the canonical
home there. Cross-repo incidents: the solutions doc goes in the repo that owns the
root cause; other repos get a one-line runbook cross-reference at most. If the root
cause is infra-host state (not any repo), the doc goes to your infrastructure repo's
`docs/solutions/`.

### 2. Write the solutions doc

Path: `docs/solutions/<YYYY-MM-DD>-<slug>.md` in the affected repo.
Schema:

```markdown
---
title: <one-line: the lesson, imperative voice>
date: <YYYY-MM-DD>
category: docs/solutions/<best-practices|incidents>
module: <subsystem>
problem_type: <incident|outage|degradation|best_practice>
component: <component>
severity: <critical|high|medium|low>
applies_when:
  - <condition that makes this relevant>
symptoms:
  - <what an operator/agent actually observes>
root_cause: <logic_error|config_drift|dependency|race|operational|...>
resolution_type: <code_fix|config_fix|process_fix|runbook>
related_components: [...]
tags: [...]
---

## What happened
<timeline: detection → diagnosis → fix → verification, with dates/SHAs>

## Root cause
<the actual mechanism, not the symptom>

## Resolution
<what fixed it, with refs to commits/PRs>

## Prevention
<what now stops recurrence: test, check, runbook, doctrine — link it>
```

`symptoms:` is the retrieval key — write it as the next agent would grep it
(error strings, observable states), not as you'd describe it in hindsight.

### 3. Decide: runbook too?

Create/update `docs/runbooks/<symptom>.md` ONLY when the class is recurrent or
procedural — a multi-step recovery someone will execute under pressure again
(seal recovery, restart ordering, rollback). One-off logic bugs fixed by code +
test: solutions doc only. Runbooks carry a freshness contract:

```yaml
---
title: <what this runbook recovers/operates>
verified: <today>
review_after: <today + 6 months>
topics: [<grep-able keywords>]
references:
  - path: <repo-relative path this runbook depends on>
---
```

If you mechanically check `references.path` (e.g. a weekly freshness job), list
only the paths whose disappearance should invalidate this runbook, no more.

### 4. Ship via PR

Worktree discipline applies (fresh worktree from current main, a consistent branch
prefix). Docs-only PRs may skip heavier review phases — that's expected, not an
error. The solutions doc may ride the fix PR itself when the incident was fixed
in-repo in the same session.

### 5. Cross-link memory

If an agent-memory note exists (or is warranted) for this incident, it gets
ONE line pointing at the repo artifact:
`Repo artifact: <repo>/docs/solutions/<file> (authoritative)`.
The memory note indexes; it never duplicates the content. If you maintain a
generated runbooks index, let it regenerate on its own schedule — do not
hand-edit it.

## Right-sizing

- Trivial, non-recurring, fully fixed by a test-backed code change → solutions
  doc only, brief.
- Don't manufacture runbooks to look thorough — a wrong-but-plausible runbook
  is worse than none (it misleads during the next incident).
- Severity in the doc reflects production impact, not effort spent.
