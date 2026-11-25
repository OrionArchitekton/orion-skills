# Archetypes, Tokens, and Motion Physics

## 8 Asymmetric Layout Archetypes

Pick one deliberate composition instead of centered stacks or generic 3-card rows:

1. **Split Editorial Hero:** 60/40 asymmetric grid; primary thesis + CTA left, live artifact or interactive proof right, pinned above `900px`.
2. **Sticky Index + Scroll Narrative:** Left sticky section rail (`top: 2rem`), right long-form narrative with inline metrics and diagrams.
3. **Asymmetric Bento Proof Grid:** 12-column grid mixing 7-col anchor module and 5-col telemetry/quote cards without uniform 3-up clone cards.
4. **Full-Bleed Architectural Frame:** Edge-to-edge structural hairline borders (`1px solid`), oversized display headline top-left, dense specification footer right.
5. **Spec Sheet / Technical Matrix:** Monospace tabular-nums ledger + interactive filter strip for OSS tools, benchmarks, or developer APIs.
6. **Founder Letter + Telemetry Sidebar:** Narrow `65ch` prose column paired with a compact live-status/evidence rail.
7. **Interactive Stage + Minimal Rail:** Product demo canvas occupying 70% of the desktop fold alongside a concise capability selector.
8. **Modular Works Showcase:** Theme-adaptive host polarity (`dark` or `light` inherited from hub CSS variables) with distinct hero pacing per project.

## Typography Pairing

- Pair a distinctive display face (editorial serif or geometric display) with a crisp readable body sans and `tabular-nums` monospace for numbers/code.
- Never default to Inter, Roboto, Arial, or system-ui everywhere.
- Self-host via `@fontsource-variable/*` and `pyftsubset` so webfonts never flicker or leak requests to third-party CDNs.

## OKLCH Tonal Elevation

- Define surface steps in `oklch(L C H)` rather than pure `#000000` / `#ffffff` or muddy gray shadows:
  - Canvas base -> Surface +0.03 L -> Elevated card +0.06 L (dark polarity) or -0.03 L / -0.05 L (light polarity).
  - Reserve saturated chroma (`C >= 0.14`) strictly for primary CTAs and semantic status badges.
  - Validate every foreground/background pair with `colorjs.io` (`WCAG21 >= 4.5:1` body/buttons, `>= 3.0:1` large headings >= 24px or >= 18.66px bold).

## CRO Proof-First Fold Rules

- Above `1280x900` desktop fold and `375x812` mobile fold: display full `<h1>`, concrete value proposition, verifiable proof signal (metric, artifact, or live state), and primary CTA.
- Never bury the `<h1>` under a splash video, decorative hero banner, or oversized spacer.

## Motion Physics

- Prefer CSS Scroll-Driven animations (`animation-timeline: view()`), native View Transitions (`@view-transition`), and damped spring curves (`stiffness: 260, damping: 28` via MIT `motion`) for interactive panels only.
- Every stylesheet with animation or transition MUST include `@media (prefers-reduced-motion: reduce)` resetting durations and transforms safely.
