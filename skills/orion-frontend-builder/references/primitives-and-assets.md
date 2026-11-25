# Primitives, Assets, and Verification

## Consumer Token Wiring (`@orion/registry`)

Map W3C DTCG tokens (`tokens/brand.tokens.json`) to CSS custom properties so shared registry components inherit host polarity automatically:

- `--orion-bg` / `--orion-surface` / `--orion-surface-elevated` (OKLCH tonal steps)
- `--orion-fg` / `--orion-fg-muted` (must verify `>= 4.5:1` on every surface)
- `--orion-accent` / `--orion-accent-fg` / `--orion-accent-hover` (CTA fills + ink verified `>= 4.5:1` in default, hover, and focus-visible states)
- `--orion-border` / `--orion-radius-*` / `--orion-font-{display,sans,mono}` (plus `.orion-focus-ring` for high-contrast `:focus-visible` outlines `>= 3.0:1`)

## Primary CTA Hit Targets

- Minimum interactive target box: `min-height: 44px; min-width: 44px; padding-inline: 1.25rem;`.
- Keep primary action labels unambiguous (`<a>` with real `href` for navigation, `<button type="submit|button">` for actions; never clickable `<div>` or dead `href="#"`).

## Asset & Typography Budget (`orion-media`)

- Convert large PNG/JPEG hero photos to AVIF/WebP via `orion-media` (`sharp`) with explicit `width` and `height` attributes to prevent CLS (`<= 0.05`).
- Optimize inline and static SVGs with `SVGO` (preserve `viewBox`, strip fixed dimensions when responsive, add `aria-hidden="true"` on decorative icons).
- Subset variable fonts with `pyftsubset` or import `@fontsource-variable/*` weights actually rendered.

## Pre-Capture Unit Checks

Every frontend PR should include fast deterministic unit checks before running `orion-web-capture`:

1. `colorjs.io` token contrast test asserting `>= 4.5:1` normal / `>= 3.0:1` large across all brand surface pairs.
2. Zero long-dash test scanning built HTML, `<title>`, copy constants, and JSON-LD for `[\u2013\u2014\u2015]`.
3. `schema-dts` / JSON-LD validation and `@media (prefers-reduced-motion: reduce)` presence check.
