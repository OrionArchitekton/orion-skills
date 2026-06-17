---
name: learn-capture
description: |
  Closing step after a task / review / incident — capture the accreted lessons
  (what was misunderstood, which assumptions changed, what would speed the next
  pass) and write them DURABLY: behavioral lessons to your agent memory
  (feedback-note style), repo/doctrine lessons to the repo's AGENTS.md or docs/.
  Use for "capture learnings", "what did we learn", "close the loop", or at the
  end of substantial work. Makes the manual feedback-note habit self-closing
  (the compound loop's 4th step).
---

# Learn Capture — the compound loop's closing step

Plan → work → review → **capture**. The first three steps solve today's task; this
one makes the next task cheaper. It converts what the session learned into a durable
artifact so a future instance does not re-derive or repeat it. This is the
self-closing version of the manual feedback-note habit.

## When to invoke

- After a review, PR merge, incident close, or any substantial task lands.
- When the user says "capture learnings", "what did we learn", "close the loop",
  "write it up" (for a lesson, not an incident — incidents use `incident-as-code`).
- Proactively when the session surfaced a non-obvious correction: a wrong
  assumption, a gotcha, a decision-and-rationale, a repeated mistake.

Do NOT capture what is already recorded (code structure, git history, an existing
memory/AGENTS.md rule) or what only mattered to this one conversation.

## What makes a lesson worth capturing

A durable lesson is **non-obvious, reusable, and actionable**. Test each candidate:

1. Would a fresh instance get this wrong without the note? (non-obvious)
2. Will it recur on similar tasks? (reusable)
3. Can the note change a future action? (actionable)

If all three: capture it. If it is a one-off or self-evident from the repo, skip it.

## Where each lesson goes (route by scope)

| Lesson scope | Destination | Form |
|---|---|---|
| How I (the agent) should work — corrections, confirmed approaches, gotchas | your agent's memory store (e.g. a `feedback_*.md` note + a one-line index pointer) | the memory schema: fact + **Why:** + **How to apply:** |
| Repo/product behavior, conventions, constraints not derivable from code | that repo's `AGENTS.md` (or local `CLAUDE.md`) | a terse rule under the right section |
| A resolved incident's root cause + fix | `docs/solutions/<date>-<slug>.md` | use `incident-as-code` instead |
| Project state / decisions for an ongoing arc | your project's state register / status doc | per that register's header |

When in doubt between memory and AGENTS.md: behavioral/agent-facing → memory;
contract/repo-facing that another contributor needs → AGENTS.md.

## Process

1. **Reflect** — in 2-4 bullets, name what changed this session: a wrong assumption
   corrected, a decision + its rationale, a gotcha hit, a faster path found.
2. **Filter** — drop anything failing the three-question test above.
3. **Route** — assign each surviving lesson a destination from the table.
4. **Write** — durable, concise, second-person-actionable. For memory files follow
   the schema (frontmatter `type: feedback|project|user|reference`, body with
   **Why:** and **How to apply:**); link related notes with `[[name]]`; add the
   index pointer line. For AGENTS.md, add the minimal rule, do not restructure.
5. **Confirm** — list what you captured and where, in one line each.

## Hard rails

- **Memory and AGENTS.md are authority surfaces — additive, minimal diffs only.**
  Do not restructure AGENTS.md or rewrite existing memory; append or update one note.
- Convert relative dates to absolute before writing.
- Never store secrets or PII in a lesson.
- A lesson is evidence-for-canon, not canon: if it would change doctrine, surface it
  for the operator rather than silently encoding a doctrine change.
- One note per distinct lesson; do not batch unrelated lessons into one file.

## Portability

Plain Markdown, tool-agnostic. Under other agent runtimes, write the same files via
your runtime's file-write mechanism — the destinations and schema are identical;
only the write mechanism differs.
