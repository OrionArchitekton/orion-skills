---
name: design-consultation
description: |
  Design consultation: understands your product, researches the landscape, proposes a
  complete design system (aesthetic, typography, color, layout, spacing, motion), and
  generates font+color preview pages. Creates DESIGN.md as your project's design source
  of truth. For an existing site with no DESIGN.md yet, infer the system from what's
  already shipped rather than starting fresh.
  Use when asked to "design system", "brand guidelines", or "create DESIGN.md".
  Proactively suggest when starting a new project's UI with no existing
  design system or DESIGN.md.
---

## Phase 0: Pre-checks

**Check for existing DESIGN.md:**

```bash
ls DESIGN.md design-system.md 2>/dev/null || echo "NO_DESIGN_FILE"
```

- If a DESIGN.md exists: Read it. Ask the user: "You already have a design system. Want to **update** it, **start fresh**, or **cancel**?"
- If no DESIGN.md: continue.

**Gather product context from the codebase:**

```bash
cat README.md 2>/dev/null | head -50
cat package.json 2>/dev/null | head -20
ls src/ app/ pages/ components/ 2>/dev/null | head -30
```

Look for office-hours output:

```bash
setopt +o nomatch 2>/dev/null || true  # zsh compat
ls .context/*office-hours* .context/attachments/*office-hours* 2>/dev/null | head -5
```

If office-hours output exists, read it; the product context is pre-filled.

If the codebase is empty and purpose is unclear, say: *"I don't have a clear picture of what you're building yet. Want to explore first with `/office-hours`? Once we know the product direction, we can set up the design system."*

## Phase 1: Product Context

Ask the user a single question that covers everything you need to know. Pre-fill what you can infer from the codebase.

**AskUserQuestion Q1, include ALL of these:**
1. Confirm what the product is, who it's for, what space/industry
2. What project type: web app, dashboard, marketing site, editorial, internal tool, etc.
3. "Want me to research what top products in your space are doing for design, or should I work from my design knowledge?"
4. **Explicitly say:** "At any point you can just drop into chat and we'll talk through anything, this isn't a rigid form, it's a conversation."

If the README or office-hours output gives you enough context, pre-fill and confirm: *"From what I can see, this is [X] for [Y] in the [Z] space. Sound right? And would you like me to research what's out there in this space, or should I work from what I know?"*

**Memorable-thing forcing question.** Before moving on, ask the user: *"What's the one
thing you want someone to remember after they see this product for the first time?"*

One sentence answer. Could be a feeling ("this is serious software for serious work"),
a visual ("the blue that's almost black"), a claim ("faster than anything else"), or
a posture ("for builders, not managers"). Write it down. Every subsequent design
decision should serve this memorable thing. Design that tries to be memorable for
everything is memorable for nothing.

---

## Phase 2: Research (only if user said yes)

If the user wants competitive research:

**Step 1: Identify what's out there via WebSearch**

Use WebSearch to find 5-10 products in their space. Search for:
- "[product category] website design"
- "[product category] best websites 2025"
- "best [industry] web apps"

**Step 2: Visual research via browser automation (if available)**

If you have a browser automation tool available in this environment (a Playwright/Puppeteer
MCP server, a headless-browser CLI, etc.), visit the top 3-5 sites in the space and capture
visual evidence: take a screenshot of each site and, where the tool supports it, pull a
structural snapshot of the page.

For each site, analyze: fonts actually used, color palette, layout approach, spacing density, aesthetic direction. The screenshot gives you the feel; the structural snapshot gives you layout data.

If a site blocks the headless browser or requires login, skip it and note why.

If no browser automation tool is available, rely on WebSearch results and your built-in design knowledge, this is fine.

**Step 3: Synthesize findings**

**Three-layer synthesis:**
- **Layer 1 (tried and true):** What design patterns does every product in this category share? These are table stakes, users expect them.
- **Layer 2 (new and popular):** What are the search results and current design discourse saying? What's trending? What new patterns are emerging?
- **Layer 3 (first principles):** Given what we know about THIS product's users and positioning, is there a reason the conventional design approach is wrong? Where should we deliberately break from the category norms?

**Eureka check:** If Layer 3 reasoning reveals a genuine design insight, a reason the category's visual language fails THIS product, name it: "EUREKA: Every [category] product does X because they assume [assumption]. But this product's users [evidence], so we should do Y instead."

Summarize conversationally:
> "I looked at what's out there. Here's the landscape: they converge on [patterns]. Most of them feel [observation, e.g., interchangeable, polished but generic, etc.]. The opportunity to stand out is [gap]. Here's where I'd play it safe and where I'd take a risk..."

**Graceful degradation:**
- Browser automation available: screenshots + structural snapshots + WebSearch (richest research)
- Browser automation unavailable: WebSearch only (still good)
- WebSearch also unavailable: agent's built-in design knowledge (always works)

If the user said no research, skip entirely and proceed to Phase 3 using your built-in design knowledge.

---

## Design Outside Voices (parallel)

Use AskUserQuestion:
> "Want outside design voices? Codex evaluates against OpenAI's design hard rules + litmus checks; Claude subagent does an independent design direction proposal."
>
> A) Yes, run outside design voices
> B) No, proceed without

If user chooses B, skip this step and continue.

**Check Codex availability:**
```bash
which codex 2>/dev/null && echo "CODEX_AVAILABLE" || echo "CODEX_NOT_AVAILABLE"
```

**If Codex is available**, launch both voices simultaneously:

1. **Codex design voice** (via Bash):
```bash
TMPERR_DESIGN=$(mktemp /tmp/codex-design-XXXXXXXX)
_REPO_ROOT=$(git rev-parse --show-toplevel) || { echo "ERROR: not in a git repo" >&2; exit 1; }
codex exec "Given this product context, propose a complete design direction:
- Visual thesis: one sentence describing mood, material, and energy
- Typography: specific font names (not defaults, no Inter/Roboto/Arial/system) + hex colors
- Color system: CSS variables for background, surface, primary text, muted text, accent
- Layout: composition-first, not component-first. First viewport as poster, not document
- Differentiation: 2 deliberate departures from category norms
- Anti-slop: no purple gradients, no 3-column icon grids, no centered everything, no decorative blobs

Be opinionated. Be specific. Do not hedge. This is YOUR design direction, own it." -C "$_REPO_ROOT" -s read-only -c 'model_reasoning_effort="medium"' --enable web_search_cached < /dev/null 2>"$TMPERR_DESIGN"
```
Use a 5-minute timeout (`timeout: 300000`). After the command completes, read stderr:
```bash
cat "$TMPERR_DESIGN" && rm -f "$TMPERR_DESIGN"
```

2. **Claude design subagent** (via Agent tool):
Dispatch a subagent with this prompt:
"Given this product context, propose a design direction that would SURPRISE. What would the cool indie studio do that the enterprise UI team wouldn't?
- Propose an aesthetic direction, typography stack (specific font names), color palette (hex values)
- 2 deliberate departures from category norms
- What emotional reaction should the user have in the first 3 seconds?

Be bold. Be specific. No hedging."

**Error handling (all non-blocking):**
- **Auth failure:** If stderr contains "auth", "login", "unauthorized", or "API key": "Codex authentication failed. Run `codex login` to authenticate."
- **Timeout:** "Codex timed out after 5 minutes."
- **Empty response:** "Codex returned no response."
- On any Codex error: proceed with Claude subagent output only, tagged `[single-model]`.
- If Claude subagent also fails: "Outside voices unavailable, continuing with primary review."

Present Codex output under a `CODEX SAYS (design direction):` header.
Present subagent output under a `CLAUDE SUBAGENT (design direction):` header.

**Synthesis:** Claude main references both Codex and subagent proposals in the Phase 3 proposal. Present:
- Areas of agreement between all three voices (Claude main + Codex + subagent)
- Genuine divergences as creative alternatives for the user to choose from
- "Codex and I agree on X. Codex suggested Y where I'm proposing Z, here's why..."

## Phase 4: Drill-downs (only if user requests adjustments)

When the user wants to change a specific section, go deep on that section:

- **Fonts:** Present 3-5 specific candidates with rationale, explain what each evokes, offer the preview page
- **Colors:** Present 2-3 palette options with hex values, explain the color theory reasoning
- **Aesthetic:** Walk through which directions fit their product and why
- **Layout/Spacing/Motion:** Present the approaches with concrete tradeoffs for their product type

Each drill-down is one focused AskUserQuestion. After the user decides, re-check coherence with the rest of the system.

---

## Prototype to decide (optional)

When a direction is genuinely uncertain and discussion isn't resolving it, build a **throwaway prototype that answers the one open question**, throwaway from day one, clearly marked, one command to run, located next to where it'll actually be used:

- **"What should this look like?"**: generate ~3 *structurally* different variations (not recolors) on a **single route**, switchable via a `?variant=` URL param and a `NODE_ENV`-gated floating switcher bar (use `router.replace` so the choice is shareable and reload-stable, and so it can't ship to production). Let the user flip between them live, then fold the winner into the DESIGN.md proposal.
- **"Does this state/logic model feel right?"**: build a tiny interactive terminal app that pushes the model through the cases that are hard to reason about on paper.

Pick the branch from the question (a page/component leads to UI variants; a backend/state model leads to a terminal app). Delete the prototype once it has answered the question.

## Phase 6: Write DESIGN.md & Confirm

**If in plan mode:** Write the DESIGN.md content into the plan file as a "## Proposed DESIGN.md" section. Do NOT write the actual file, that happens at implementation time.

**If NOT in plan mode:** Write `DESIGN.md` to the repo root with this structure:

```markdown
# Design System, [Project Name]

## Product Context
- **What this is:** [1-2 sentence description]
- **Who it's for:** [target users]
- **Space/industry:** [category, peers]
- **Project type:** [web app / dashboard / marketing site / editorial / internal tool]

## Aesthetic Direction
- **Direction:** [name]
- **Decoration level:** [minimal / intentional / expressive]
- **Mood:** [1-2 sentence description of how the product should feel]
- **Reference sites:** [URLs, if research was done]

## Typography
- **Display/Hero:** [font name], [rationale]
- **Body:** [font name], [rationale]
- **UI/Labels:** [font name or "same as body"]
- **Data/Tables:** [font name], [rationale, must support tabular-nums]
- **Code:** [font name]
- **Loading:** [CDN URL or self-hosted strategy]
- **Scale:** [modular scale with specific px/rem values for each level]

## Color
- **Approach:** [restrained / balanced / expressive]
- **Primary:** [hex], [what it represents, usage]
- **Secondary:** [hex], [usage]
- **Neutrals:** [warm/cool grays, hex range from lightest to darkest]
- **Semantic:** success [hex], warning [hex], error [hex], info [hex]
- **Dark mode:** [strategy, redesign surfaces, reduce saturation 10-20%]

## Spacing
- **Base unit:** [4px or 8px]
- **Density:** [compact / comfortable / spacious]
- **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64)

## Layout
- **Approach:** [grid-disciplined / creative-editorial / hybrid]
- **Grid:** [columns per breakpoint]
- **Max content width:** [value]
- **Border radius:** [hierarchical scale, e.g., sm:4px, md:8px, lg:12px, full:9999px]

## Motion
- **Approach:** [minimal-functional / intentional / expressive]
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(50-100ms) short(150-250ms) medium(250-400ms) long(400-700ms)

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| [today] | Initial design system created | Created by /design-consultation based on [product context / research] |
```

**Update CLAUDE.md** (or create it if it doesn't exist), append this section:

```markdown
## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.
```

**AskUserQuestion Q-final, show summary and confirm:**

List all decisions. Flag any that used agent defaults without explicit user confirmation (the user should know what they're shipping). Options:
- A) Ship it: write DESIGN.md and CLAUDE.md
- B) I want to change something (specify what)
- C) Start over

After shipping DESIGN.md, if the session produced screen-level mockups or page layouts
(not just system-level tokens), suggest generating a working HTML preview of the key
screens using the tokens just defined, a good next step before writing framework code.

---

## Important Rules

1. **Propose, don't present menus.** You are a consultant, not a form. Make opinionated recommendations based on the product context, then let the user adjust.
2. **Every recommendation needs a rationale.** Never say "I recommend X" without "because Y."
3. **Coherence over individual choices.** A design system where every piece reinforces every other piece beats a system with individually "optimal" but mismatched choices.
4. **Never recommend blacklisted or overused fonts as primary.** If the user specifically requests one, comply but explain the tradeoff.
5. **The preview page must be beautiful.** It's the first visual output and sets the tone for the whole skill.
6. **Conversational tone.** This isn't a rigid workflow. If the user wants to talk through a decision, engage as a thoughtful design partner.
7. **Accept the user's final choice.** Nudge on coherence issues, but never block or refuse to write a DESIGN.md because you disagree with a choice.
8. **No AI slop in your own output.** Your recommendations, your preview page, your DESIGN.md, all should demonstrate the taste you're asking the user to adopt.

## Boundary

This skill owns the design-system decision (aesthetic, typography, color, layout, spacing,
motion) and the DESIGN.md artifact it produces. It does not own implementation: turning
DESIGN.md into working components, choosing a component library, or wiring a CI/build step
for the preview page are your project's own conventions. If your toolset has a separate
design-review or design-to-code skill, hand off to it once DESIGN.md is approved.

## References (progressive disclosure)

To keep this skill lean, depth was moved to `references/` (load only when needed):

- Shared runtime conventions (AskUserQuestion format, voice, jargon glossary) → `references/preamble.md`
- 2 detailed section(s) → `references/details.md`: Phase 3: The Complete Proposal, Phase 5: Design System Preview (default ON)
