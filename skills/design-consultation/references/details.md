# Detailed sections (moved from SKILL.md spine, lazy-loaded)

_Load when the spine points you here._

## Phase 3: The Complete Proposal

This is the soul of the skill. Propose EVERYTHING as one coherent package.

**AskUserQuestion Q2, present the full proposal with SAFE/RISK breakdown:**

```
Based on [product context] and [research findings / my design knowledge]:

AESTHETIC: [direction], [one-line rationale]
DECORATION: [level], [why this pairs with the aesthetic]
LAYOUT: [approach], [why this fits the product type]
COLOR: [approach] + proposed palette (hex values), [rationale]
TYPOGRAPHY: [3 font recommendations with roles], [why these fonts]
SPACING: [base unit + density], [rationale]
MOTION: [approach], [rationale]

This system is coherent because [explain how choices reinforce each other].

SAFE CHOICES (category baseline, your users expect these):
  - [2-3 decisions that match category conventions, with rationale for playing safe]

RISKS (where your product gets its own face):
  - [2-3 deliberate departures from convention]
  - For each risk: what it is, why it works, what you gain, what it costs

The safe choices keep you literate in your category. The risks are where
your product becomes memorable. Which risks appeal to you? Want to see
different ones? Or adjust anything else?
```

The SAFE/RISK breakdown is critical. Design coherence is table stakes, every product in a category can be coherent and still look identical. The real question is: where do you take creative risks? The agent should always propose at least 2 risks, each with a clear rationale for why the risk is worth taking and what the user gives up. Risks might include: an unexpected typeface for the category, a bold accent color nobody else uses, tighter or looser spacing than the norm, a layout approach that breaks from convention, motion choices that add personality.

**Options:** A) Looks great, generate the preview page. B) I want to adjust [section]. C) I want different risks, show me wilder options. D) Start over with a different direction. E) Skip the preview, just write DESIGN.md.

### Your Design Knowledge (use to inform proposals, do NOT display as tables)

**Aesthetic directions** (pick the one that fits the product):
- Brutally Minimal: Type and whitespace only. No decoration. Modernist.
- Maximalist Chaos: Dense, layered, pattern-heavy. Y2K meets contemporary.
- Retro-Futuristic: Vintage tech nostalgia. CRT glow, pixel grids, warm monospace.
- Luxury/Refined: Serifs, high contrast, generous whitespace, precious metals.
- Playful/Toy-like: Rounded, bouncy, bold primaries. Approachable and fun.
- Editorial/Magazine: Strong typographic hierarchy, asymmetric grids, pull quotes.
- Brutalist/Raw: Exposed structure, system fonts, visible grid, no polish.
- Art Deco: Geometric precision, metallic accents, symmetry, decorative borders.
- Organic/Natural: Earth tones, rounded forms, hand-drawn texture, grain.
- Industrial/Utilitarian: Function-first, data-dense, monospace accents, muted palette.

**Decoration levels:** minimal (typography does all the work) / intentional (subtle texture, grain, or background treatment) / expressive (full creative direction, layered depth, patterns)

**Layout approaches:** grid-disciplined (strict columns, predictable alignment) / creative-editorial (asymmetry, overlap, grid-breaking) / hybrid (grid for app, creative for marketing)

**Color approaches:** restrained (1 accent + neutrals, color is rare and meaningful) / balanced (primary + secondary, semantic colors for hierarchy) / expressive (color as a primary design tool, bold palettes)

**Motion approaches:** minimal-functional (only transitions that aid comprehension) / intentional (subtle entrance animations, meaningful state transitions) / expressive (full choreography, scroll-driven, playful)

**Font recommendations by purpose:**
- Display/Hero: Satoshi, General Sans, Instrument Serif, Fraunces, Clash Grotesk, Cabinet Grotesk
- Body: Instrument Sans, DM Sans, Source Sans 3, Geist, Plus Jakarta Sans, Outfit
- Data/Tables: Geist (tabular-nums), DM Sans (tabular-nums), JetBrains Mono, IBM Plex Mono
- Code: JetBrains Mono, Fira Code, Berkeley Mono, Geist Mono

**Font blacklist** (never recommend):
Papyrus, Comic Sans, Lobster, Impact, Jokerman, Bleeding Cowboys, Permanent Marker, Bradley Hand, Brush Script, Hobo, Trajan, Raleway, Clash Display, Courier New (for body)

**Overused fonts** (never recommend as primary, use only if user specifically requests):
Inter, Roboto, Arial, Helvetica, Open Sans, Lato, Montserrat, Poppins, Space Grotesk.

Space Grotesk is on the list specifically because every AI design tool converges on it
as "the safe alternative to Inter." That's the convergence trap. Treat it the same as
Inter: only use if the user asks for it by name.

**Anti-convergence directive:** Across multiple generations in the same project, VARY
light/dark, fonts, and aesthetic directions. Never propose the same choices twice
without explicit justification. If the user's prior session used Geist + dark + editorial,
propose something different this time (or explicitly acknowledge you're doubling down
because it fits the brief). Convergence across generations is slop.

**AI slop anti-patterns** (never include in your recommendations):
- Purple/violet gradients as default accent
- 3-column feature grid with icons in colored circles
- Centered everything with uniform spacing
- Uniform bubbly border-radius on all elements
- Gradient buttons as the primary CTA pattern
- Generic stock-photo-style hero sections
- system-ui / -apple-system as the primary display or body font (the "I gave up on typography" signal)
- "Built for X" / "Designed for Y" marketing copy patterns

### Coherence Validation

When the user overrides one section, check if the rest still coheres. Flag mismatches with a gentle nudge, never block:

- Brutalist/Minimal aesthetic + expressive motion: "Heads up: brutalist aesthetics usually pair with minimal motion. Your combo is unusual, which is fine if intentional. Want me to suggest motion that fits, or keep it?"
- Expressive color + restrained decoration: "Bold palette with minimal decoration can work, but the colors will carry a lot of weight. Want me to suggest decoration that supports the palette?"
- Creative-editorial layout + data-heavy product: "Editorial layouts are gorgeous but can fight data density. Want me to show how a hybrid approach keeps both?"
- Always accept the user's final choice. Never refuse to proceed.

---

## Phase 5: Design System Preview (default ON)

This phase generates a visual preview of the proposed design system.

### HTML Preview Page

Generate a polished HTML preview page and open it in the user's browser. This page is the first visual artifact the skill produces, it should look beautiful.

```bash
PREVIEW_FILE="/tmp/design-consultation-preview-$(date +%s).html"
```

Write the preview HTML to `$PREVIEW_FILE`, then open it:

```bash
open "$PREVIEW_FILE"
```

### Preview Page Requirements

The agent writes a **single, self-contained HTML file** (no framework dependencies) that:

1. **Loads proposed fonts** from Google Fonts (or Bunny Fonts) via `<link>` tags
2. **Uses the proposed color palette** throughout, dogfood the design system
3. **Shows the product name** (not "Lorem Ipsum") as the hero heading
4. **Font specimen section:**
   - Each font candidate shown in its proposed role (hero heading, body paragraph, button label, data table row)
   - Side-by-side comparison if multiple candidates for one role
   - Real content that matches the product (e.g., civic tech, government data examples)
5. **Color palette section:**
   - Swatches with hex values and names
   - Sample UI components rendered in the palette: buttons (primary, secondary, ghost), cards, form inputs, alerts (success, warning, error, info)
   - Background/text color combinations showing contrast
6. **Realistic product mockups**, this is what makes the preview page powerful. Based on the project type from Phase 1, render 2-3 realistic page layouts using the full design system:
   - **Dashboard / web app:** sample data table with metrics, sidebar nav, header with user avatar, stat cards
   - **Marketing site:** hero section with real copy, feature highlights, testimonial block, CTA
   - **Settings / admin:** form with labeled inputs, toggle switches, dropdowns, save button
   - **Auth / onboarding:** login form with social buttons, branding, input validation states
   - Use the product name, realistic content for the domain, and the proposed spacing/layout/border-radius. The user should see their product (roughly) before writing any code.
7. **Light/dark mode toggle** using CSS custom properties and a JS toggle button
8. **Clean, professional layout**, the preview page IS a taste signal for the skill
9. **Responsive**, looks good on any screen width

The page should make the user think "oh nice, they thought of this." It's selling the design system by showing what the product could feel like, not just listing hex codes and font names.

If `open` fails (headless environment), tell the user: *"I wrote the preview to [path], open it in your browser to see the fonts and colors rendered."*

If the user says skip the preview, go directly to Phase 6.

---
