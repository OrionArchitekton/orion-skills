---
name: office-hours
description: |
  YC Office Hours product ideation: startup mode (six forcing questions on demand, wedge, specificity) plus builder mode (design-thinking brainstorm); saves a design doc. Proactively invoke (do NOT answer directly) for "is this worth building", "I have an idea", "brainstorm this", "office hours", or any new product concept explored before code is written.
---

## Phase 1: Context Gathering

Understand the project and the area the user wants to change.

```bash
SLUG=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')
BRANCH=$(git branch --show-current 2>/dev/null || echo main)
BRANCH=${BRANCH:-main}
BRANCH=${BRANCH//\//-}
```

1. Read `CLAUDE.md`, `TODOS.md` (if they exist).
2. Run `git log --oneline -30` and `git diff origin/main --stat 2>/dev/null` to understand recent context.
3. Use Grep/Glob to map the codebase areas most relevant to the user's request.
4. **List existing design docs for this project:**
   ```bash
   setopt +o nomatch 2>/dev/null || true  # zsh compat
   PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
   mkdir -p "$PROJECT_ROOT/docs/design"
   ls -t "$PROJECT_ROOT"/docs/design/*-design-*.md 2>/dev/null
   ```
   Design docs are deliverable artifacts: they live under `docs/design/` in the project
   (not a Claude-local home) so they can be committed like any other doc.
   If design docs exist, list them: "Prior designs for this project: [titles + dates]"
5. **Ask: what's your goal with this?** This is a real question, not a formality. The answer determines everything about how the session runs.

   Via AskUserQuestion, ask:

   > Before we dig in, what's your goal with this?
   >
   > - **Building a startup** (or thinking about it)
   > - **Intrapreneurship**: internal project at a company, need to ship fast
   > - **Hackathon / demo**: time-boxed, need to impress
   > - **Open source / research**: building for a community or exploring an idea
   > - **Learning**: teaching yourself to code, vibe coding, leveling up
   > - **Having fun**: side project, creative outlet, just vibing

   **Mode mapping:**
   - Startup, intrapreneurship: **Startup mode** (Phase 2A). Load `references/details.md` and execute Phase 2A from it before continuing.
   - Hackathon, open source, research, learning, having fun: **Builder mode** (Phase 2B)

6. **Assess product stage** (only for startup/intrapreneurship modes):
   - Pre-product (idea stage, no users yet)
   - Has users (people using it, not yet paying)
   - Has paying customers

Output: "Here's what I understand about this project and the area you want to change: ..."

## Phase 2B: Builder Mode (Design Partner)

Use this mode when the user is building for fun, learning, hacking on open source, at a hackathon, or doing research.

### Operating Principles

1. **Delight is the currency**: what makes someone say "whoa"?
2. **Ship something you can show people.** The best version of anything is the one that exists.
3. **The best side projects solve your own problem.** If you're building it for yourself, trust that instinct.
4. **Explore before you optimize.** Try the weird idea first. Polish later.

**Wild exemplar:**

STRUCTURED (avoid): "Consider adding a share feature. This would improve user retention by enabling virality."

WILD (aim for): "Oh, and what if you also let them share the visualization as a live URL? Or pipe it into a Slack thread? Or animate the generation so viewers see it draw itself? Each one's a 30-minute unlock. Any of them turn this from 'a tool I used' into 'a thing I showed a friend.'"

Both are outcome-framed. Only one has the 'whoa.' Builder mode's job is to surface the most exciting version of the idea, not the most strategically optimized one. Lead with the fun; let the user edit it down.

### Response Posture

- **Enthusiastic, opinionated collaborator.** You're here to help them build the coolest thing possible. Riff on their ideas. Get excited about what's exciting.
- **Help them find the most exciting version of their idea.** Don't settle for the obvious version.
- **Suggest cool things they might not have thought of.** Bring adjacent ideas, unexpected combinations, "what if you also..." suggestions.
- **End with concrete build steps, not business validation tasks.** The deliverable is "what to build next," not "who to interview."

### Questions (generative, not interrogative)

Ask these **ONE AT A TIME** via AskUserQuestion. The goal is to brainstorm and sharpen the idea, not interrogate.

- **What's the coolest version of this?** What would make it genuinely delightful?
- **Who would you show this to?** What would make them say "whoa"?
- **What's the fastest path to something you can actually use or share?**
- **What existing thing is closest to this, and how is yours different?**
- **What would you add if you had unlimited time?** What's the 10x version?

**Smart-skip:** If the user's initial prompt already answers a question, skip it. Only ask questions whose answers aren't yet clear.

**STOP** after each question. Wait for the response before asking the next.

**Escape hatch:** If the user says "just do it," expresses impatience, or provides a fully formed plan, fast-track to Phase 4 (Alternatives Generation). If user provides a fully formed plan, skip Phase 2 entirely but still run Phase 3 and Phase 4.

**If the vibe shifts mid-session** (the user starts in builder mode but says "actually I think this could be a real company" or mentions customers, revenue, fundraising), upgrade to Startup mode naturally. Say something like: "Okay, now we're talking, let me ask you some harder questions." Then switch to the Phase 2A questions. Load `references/details.md` and execute Phase 2A from it before continuing.

---

## Phase 2.5: Related Design Discovery

After the user states the problem (first question in Phase 2A or 2B), search existing design docs for keyword overlap.

Extract 3-5 significant keywords from the user's problem statement and grep across design docs:
```bash
setopt +o nomatch 2>/dev/null || true  # zsh compat
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
grep -li "<keyword1>\|<keyword2>\|<keyword3>" "$PROJECT_ROOT"/docs/design/*-design-*.md 2>/dev/null
```

If matches found, read the matching design docs and surface them:
- "FYI: Related design found: '{title}' by {user} on {date} (branch: {branch}). Key overlap: {1-line summary of relevant section}."
- Ask via AskUserQuestion: "Should we build on this prior design or start fresh?"

This surfaces prior sessions on the same project; earlier design docs for this repo will show up automatically from `docs/design/`.

If no matches found, proceed silently.

---

## Phase 2.75: Landscape Awareness

Apply the Search Before Building framework (three layers, eureka moments) from the preamble's Search Before Building section.

After understanding the problem through questioning, search for what the world thinks. This is NOT competitive research (that's a design-consultation skill's job, if you have one). This is understanding conventional wisdom so you can evaluate where it's wrong.

**Privacy gate:** Before searching, use AskUserQuestion: "I'd like to search for what the world thinks about this space to inform our discussion. This sends generalized category terms (not your specific idea) to a search provider. OK to proceed?"
Options: A) Yes, search away  B) Skip (keep this session private)
If B: skip this phase entirely and proceed to Phase 3. Use only in-distribution knowledge.

When searching, use **generalized category terms**: never the user's specific product name, proprietary concept, or stealth idea. For example, search "task management app landscape" not "SuperTodo AI-powered task killer."

If WebSearch is unavailable, skip this phase and note: "Search unavailable, proceeding with in-distribution knowledge only."

**Startup mode:** WebSearch for:
- "[problem space] startup approach {current year}"
- "[problem space] common mistakes"
- "why [incumbent solution] fails" OR "why [incumbent solution] works"

**Builder mode:** WebSearch for:
- "[thing being built] existing solutions"
- "[thing being built] open source alternatives"
- "best [thing category] {current year}"

Read the top 2-3 results. Run the three-layer synthesis:
- **[Layer 1]** What does everyone already know about this space?
- **[Layer 2]** What are the search results and current discourse saying?
- **[Layer 3]** Given what WE learned in Phase 2A/2B, is there a reason the conventional approach is wrong?

**Eureka check:** If Layer 3 reasoning reveals a genuine insight, name it: "EUREKA: Everyone does X because they assume [assumption]. But [evidence from our conversation] suggests that's wrong here. This means [implication]." Log the eureka moment (see preamble).

If no eureka moment exists, say: "The conventional wisdom seems sound here. Let's build on it." Proceed to Phase 3.

**Important:** This search feeds Phase 3 (Premise Challenge). If you found reasons the conventional approach fails, those become premises to challenge. If conventional wisdom is solid, that raises the bar for any premise that contradicts it.

---

## Phase 3: Premise Challenge

Before proposing solutions, challenge the premises:

1. **Is this the right problem?** Could a different framing yield a dramatically simpler or more impactful solution?
2. **What happens if we do nothing?** Real pain point or hypothetical one?
3. **What existing code already partially solves this?** Map existing patterns, utilities, and flows that could be reused.
4. **If the deliverable is a new artifact** (CLI binary, library, package, container image, mobile app): **how will users get it?** Code without distribution is code nobody can use. The design must include a distribution channel (GitHub Releases, package manager, container registry, app store) and CI/CD pipeline, or explicitly defer it.
5. **Startup mode only:** Synthesize the diagnostic evidence from Phase 2A. Does it support this direction? Where are the gaps?

Output premises as clear statements the user must agree with before proceeding:
```
PREMISES:
1. [statement]: agree/disagree?
2. [statement]: agree/disagree?
3. [statement]: agree/disagree?
```

Use AskUserQuestion to confirm. If the user disagrees with a premise, revise understanding and loop back.

---

**Before continuing:** Load `references/details.md` and execute Phase 3.5 (Cross-Model Second Opinion) from it before continuing to Phase 4.

## Phase 4: Alternatives Generation (MANDATORY)

Produce 2-3 distinct implementation approaches. This is NOT optional.

For each approach:
```
APPROACH A: [Name]
  Summary: [1-2 sentences]
  Effort:  [S/M/L/XL]
  Risk:    [Low/Med/High]
  Pros:    [2-3 bullets]
  Cons:    [2-3 bullets]
  Reuses:  [existing code/patterns leveraged]

APPROACH B: [Name]
  ...

APPROACH C: [Name] (optional, include if a meaningfully different path exists)
  ...
```

Rules:
- At least 2 approaches required. 3 preferred for non-trivial designs.
- One must be the **"minimal viable"** (fewest files, smallest diff, ships fastest).
- One must be the **"ideal architecture"** (best long-term trajectory, most elegant).
- One can be **creative/lateral** (unexpected approach, different framing of the problem).
- If the second opinion (Codex or Claude subagent) proposed a prototype in Phase 3.5, consider using it as a starting point for the creative/lateral approach.

**RECOMMENDATION:** Choose [X] because [one-line reason mapped to the founder's stated goal].

Emit ONE AskUserQuestion that lists every alternative (A/B and optionally C) as numbered options, using the preamble's AskUserQuestion Format section. The AskUserQuestion call is a tool_use, not prose; write the question text and call the tool. If no AskUserQuestion variant is callable in this session, follow the preamble's "Tool resolution" fallback: in plan mode, write `## Decisions to confirm` into the plan file and ExitPlanMode; outside plan mode, output the decision brief as prose and stop. Never silently auto-decide.

**STOP.** Do NOT proceed to Phase 4.5 (Founder Signal Synthesis), Phase 5 (Design Doc), Phase 6 (Closing), or any design-doc generation until the user responds. A "clearly winning approach" is still an approach decision and still needs explicit user approval before it lands in the design doc. Writing the recommendation in chat prose and continuing forward is the failure mode this gate exists to prevent.

---

## Phase 4.5: Founder Signal Synthesis

Before writing the design doc, synthesize the founder signals you observed during the session. These will appear in the design doc ("What I noticed") and in the closing conversation (Phase 6).

Track which of these signals appeared during the session:
- Articulated a **real problem** someone actually has (not hypothetical)
- Named **specific users** (people, not categories: "Sarah at Acme Corp" not "enterprises")
- **Pushed back** on premises (conviction, not compliance)
- Their project solves a problem **other people need**
- Has **domain expertise**: knows this space from the inside
- Showed **taste**: cared about getting the details right
- Showed **agency**: actually building, not just planning
- **Defended premise with reasoning** against cross-model challenge (kept original premise when Codex disagreed AND articulated specific reasoning for why; dismissal without reasoning does not count)

Count the signals. You'll use this count in Phase 6 to determine which tier of closing message to use.

### Builder Profile Append

After counting signals, append a session entry to the builder profile. This is the single
source of truth for all closing state (tier, resource dedup, journey tracking).

```bash
STATE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.office-hours"
# Protect the private state dir BEFORE the first write: git's local exclude file
# ignores it immediately without mutating the tracked .gitignore. No-op outside git.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) && mkdir -p "$GIT_DIR/info" \
  && grep -qxF '.office-hours/' "$GIT_DIR/info/exclude" 2>/dev/null \
  || { [ -n "$GIT_DIR" ] && echo '.office-hours/' >> "$GIT_DIR/info/exclude"; }
mkdir -p "$STATE_ROOT"
```

This is project-local state (not a Claude-local home), so on first use in a project,
suggest to the user: add `.office-hours/` to the project's `.gitignore` (it holds
personal session state, not a deliverable).

Append one JSON line with these fields (substitute actual values from this session):
- `date`: current ISO 8601 timestamp
- `mode`: "startup" or "builder" (from Phase 1 mode selection)
- `project_slug`: the SLUG value computed in Phase 1
- `signal_count`: number of signals counted above
- `signals`: array of signal names observed (e.g., `["named_users", "pushback", "taste"]`)
- `design_doc`: path to the design doc that will be written in Phase 5 (construct it now)
- `assignment`: the assignment you will give in the design doc's "The Assignment" section
- `resources_shown`: empty array `[]` for now (populated after resource selection in Phase 6)
- `topics`: array of 2-3 topic keywords that describe what this session was about

```bash
STATE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.office-hours"
# Protect the private state dir BEFORE the first write: git's local exclude file
# ignores it immediately without mutating the tracked .gitignore. No-op outside git.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) && mkdir -p "$GIT_DIR/info" \
  && grep -qxF '.office-hours/' "$GIT_DIR/info/exclude" 2>/dev/null \
  || { [ -n "$GIT_DIR" ] && echo '.office-hours/' >> "$GIT_DIR/info/exclude"; }
jq -cn --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg mode "MODE" \
  --arg slug "${SLUG:-unknown}" --argjson n N --argjson signals SIGNALS_ARRAY \
  --arg doc "DOC_PATH" --arg assignment "ASSIGNMENT_TEXT" --argjson topics TOPICS_ARRAY \
  '{date:$date,mode:$mode,project_slug:$slug,signal_count:$n,signals:$signals,design_doc:$doc,assignment:$assignment,resources_shown:[],topics:$topics}' \
  >> "$STATE_ROOT/builder-profile.jsonl" 2>/dev/null || true
# jq --arg guarantees valid JSON even when the assignment or topics contain
# quotes/newlines; a raw interpolated echo corrupted the JSONL on such input.
```

This entry is append-only. The `resources_shown` field will be updated via a second append
after resource selection in Phase 6 Beat 3.5.

---

## Phase 5: Design Doc

Write the design document to the project directory.

```bash
SLUG=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
mkdir -p "$PROJECT_ROOT/docs/design"
USER=$(whoami)
DATETIME=$(date +%Y%m%d-%H%M%S)
BRANCH=$(git branch --show-current 2>/dev/null || echo main)
BRANCH=${BRANCH:-main}
BRANCH=${BRANCH//\//-}
```

**Design lineage:** Before writing, check for existing design docs on this branch:
```bash
setopt +o nomatch 2>/dev/null || true  # zsh compat
if [ -n "$BRANCH" ]; then
  PRIOR=$(ls -t "$PROJECT_ROOT"/docs/design/*-$BRANCH-design-*.md 2>/dev/null | head -1)
else
  PRIOR=""
fi
```
If `$PRIOR` exists, the new doc gets a `Supersedes:` field referencing it. This creates a revision chain: you can trace how a design evolved across office hours sessions.

Write to `docs/design/{user}-{branch}-design-{datetime}.md` (project root). This is a
deliverable artifact, not Claude-local state: commit it like any other doc.

After writing the design doc, tell the user:
**"Design doc saved to: {full path}. Use it as the seed for a build prompt (`/goal-prompt`), or a future office-hours session will link it automatically via the `Supersedes:` chain."**

### Startup mode design doc template:

```markdown
# Design: {title}

Generated by /office-hours on {date}
Branch: {branch}
Repo: {owner/repo}
Status: DRAFT
Mode: Startup
Supersedes: {prior filename; omit this line if first design on this branch}

## Problem Statement
{from Phase 2A}

## Demand Evidence
{from Q1: specific quotes, numbers, behaviors demonstrating real demand}

## Status Quo
{from Q2: concrete current workflow users live with today}

## Target User & Narrowest Wedge
{from Q3 + Q4: the specific human and the smallest version worth paying for}

## Constraints
{from Phase 2A}

## Premises
{from Phase 3}

## Cross-Model Perspective
{If second opinion ran in Phase 3.5 (Codex or Claude subagent): independent cold read, steelman, key insight, challenged premise, prototype suggestion. Verbatim or close paraphrase. If second opinion did NOT run (skipped or unavailable): omit this section entirely; do not include it.}

## Approaches Considered
### Approach A: {name}
{from Phase 4}
### Approach B: {name}
{from Phase 4}

## Recommended Approach
{chosen approach with rationale}

## Open Questions
{any unresolved questions from the office hours}

## Success Criteria
{measurable criteria from Phase 2A}

## Distribution Plan
{how users get the deliverable: binary download, package manager, container image, web service, etc.}
{CI/CD pipeline for building and publishing: GitHub Actions, manual release, auto-deploy on merge?}
{omit this section if the deliverable is a web service with existing deployment pipeline}

## Dependencies
{blockers, prerequisites, related work}

## The Assignment
{one concrete real-world action the founder should take next, not "go build it"}

## What I noticed about how you think
{observational, mentor-like reflections referencing specific things the user said during the session. Quote their words back to them; don't characterize their behavior. 2-4 bullets.}
```

### Builder mode design doc template:

```markdown
# Design: {title}

Generated by /office-hours on {date}
Branch: {branch}
Repo: {owner/repo}
Status: DRAFT
Mode: Builder
Supersedes: {prior filename; omit this line if first design on this branch}

## Problem Statement
{from Phase 2B}

## What Makes This Cool
{the core delight, novelty, or "whoa" factor}

## Constraints
{from Phase 2B}

## Premises
{from Phase 3}

## Cross-Model Perspective
{If second opinion ran in Phase 3.5 (Codex or Claude subagent): independent cold read, coolest version, key insight, existing tools, prototype suggestion. Verbatim or close paraphrase. If second opinion did NOT run (skipped or unavailable): omit this section entirely; do not include it.}

## Approaches Considered
### Approach A: {name}
{from Phase 4}
### Approach B: {name}
{from Phase 4}

## Recommended Approach
{chosen approach with rationale}

## Open Questions
{any unresolved questions from the office hours}

## Success Criteria
{what "done" looks like}

## Distribution Plan
{how users get the deliverable: binary download, package manager, container image, web service, etc.}
{CI/CD pipeline for building and publishing, or "existing deployment pipeline covers this"}

## Next Steps
{concrete build tasks: what to implement first, second, third}

## What I noticed about how you think
{observational, mentor-like reflections referencing specific things the user said during the session. Quote their words back to them; don't characterize their behavior. 2-4 bullets.}
```

---

## Spec Review Loop

Before presenting the document to the user for approval, run an adversarial review.

**Step 1: Dispatch reviewer subagent**

Use the Agent tool to dispatch an independent reviewer. The reviewer has fresh context
and cannot see the brainstorming conversation, only the document. This ensures genuine
adversarial independence.

Prompt the subagent with:
- The file path of the document just written
- "Read this document and review it on 5 dimensions. For each dimension, note PASS or
  list specific issues with suggested fixes. At the end, output a quality score (1-10)
  across all dimensions."

**Dimensions:**
1. **Completeness**: Are all requirements addressed? Missing edge cases?
2. **Consistency**: Do parts of the document agree with each other? Contradictions?
3. **Clarity**: Could an engineer implement this without asking questions? Ambiguous language?
4. **Scope**: Does the document creep beyond the original problem? YAGNI violations?
5. **Feasibility**: Can this actually be built with the stated approach? Hidden complexity?

The subagent should return:
- A quality score (1-10)
- PASS if no issues, or a numbered list of issues with dimension, description, and fix

**Step 2: Fix and re-dispatch**

If the reviewer returns issues:
1. Fix each issue in the document on disk (use Edit tool)
2. Re-dispatch the reviewer subagent with the updated document
3. Maximum 3 iterations total

**Convergence guard:** If the reviewer returns the same issues on consecutive iterations
(the fix didn't resolve them or the reviewer disagrees with the fix), stop the loop
and persist those issues as "Reviewer Concerns" in the document rather than looping
further.

If the subagent fails, times out, or is unavailable, skip the review loop entirely.
Tell the user: "Spec review unavailable, presenting unreviewed doc." The document is
already written to disk; the review is a quality bonus, not a gate.

**Step 3: Report and persist metrics**

After the loop completes (PASS, max iterations, or convergence guard):

1. Tell the user the result, summary by default:
   "Your doc survived N rounds of adversarial review. M issues caught and fixed.
   Quality score: X/10."
   If they ask "what did the reviewer find?", show the full reviewer output.

2. If issues remain after max iterations or convergence, add a "## Reviewer Concerns"
   section to the document listing each unresolved issue. Downstream skills will see this.

3. Append metrics:
```bash
ANALYTICS_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.office-hours/analytics"
mkdir -p "$ANALYTICS_DIR"
echo '{"skill":"office-hours","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","iterations":ITERATIONS,"issues_found":FOUND,"issues_fixed":FIXED,"remaining":REMAINING,"quality_score":SCORE}' >> "$ANALYTICS_DIR/spec-review.jsonl" 2>/dev/null || true
```
Replace ITERATIONS, FOUND, FIXED, REMAINING, SCORE with actual values from the review.

---

Present the reviewed design doc to the user via AskUserQuestion:
- A) Approve: mark Status: APPROVED and proceed to handoff
- B) Revise: specify which sections need changes (loop back to revise those sections)
- C) Start over: return to Phase 2

---

## Important Rules

- **Never start implementation.** This skill produces design docs, not code. Not even scaffolding.
- **Questions ONE AT A TIME.** Never batch multiple questions into one AskUserQuestion.
- **The assignment is mandatory.** Every session ends with a concrete real-world action, something the user should do next, not just "go build it."
- **If user provides a fully formed plan:** skip Phase 2 (questioning) but still run Phase 3 (Premise Challenge) and Phase 4 (Alternatives). Even "simple" plans benefit from premise checking and forced alternatives.
- **Completion status:**
  - DONE: design doc APPROVED
  - DONE_WITH_CONCERNS: design doc approved but with open questions listed
  - NEEDS_CONTEXT: user left questions unanswered, design incomplete

## Boundary

This skill produces a design doc, not code, and it never invokes an implementation skill on
its own. Where you keep the design-doc state directory, which build-prompt skill you feed
the doc into, and how your project tracks design history beyond the `Supersedes:` chain are
your own conventions. The hard gate is the shape: no implementation before the doc is
approved, and every session ends with one concrete assignment.

## References (progressive disclosure)

To keep this skill lean, depth was moved to `references/` (load only when needed):

- Shared runtime preamble → `references/preamble.md`
- 4 detailed section(s) → `references/details.md`: Phase 2A: Startup Mode (YC Product Diagnostic), Phase 3.5: Cross-Model Second Opinion (optional), Visual Sketch (UI ideas only), Phase 6: Handoff (The Relationship Closing)
