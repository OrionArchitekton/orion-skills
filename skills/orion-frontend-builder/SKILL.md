---
name: orion-frontend-builder
description: Use when implementing directed frontend specs into code with @orion/registry primitives, semantic landmarks, >=44px primary CTA targets, self-hosted @fontsource-variable fonts, orion-media assets, and prefers-reduced-motion guards.
---

# Orion Frontend Builder

Executes Stage 4 (Implementation) and Stage 7 (Targeted Iteration) of the 9-stage web lifecycle after `orion-web-director` locks `DESIGN.md` and `tokens/brand.tokens.json`.

## Build Contract

1. **Preflight:** Confirm the canonical-home preflight passed (`orion-check-canonical-web-home` exit `0` when installed, or portable `git rev-parse --show-toplevel` + `git worktree list` check) and read `DESIGN.md` plus `tokens/brand.tokens.json`.
2. **Accessible Primitives (`@orion/registry`):** Consume `@orion/registry` Base UI and React Aria components styled strictly through consumer CSS tokens (`--bg`, `--surface`, `--text`, `--accent`). Never re-implement accessible dialogs, tabs, popovers, or menus from scratch.
3. **Semantic Landmarks & Headings:** Render exactly one `<header>`, `<nav>`, `<main>`, and `<footer>` at page shell level (never inside repeated cards). Keep one visible `<h1>` per page above the `900px` desktop fold with strictly sequential `h1 -> h2 -> h3` heading levels.
4. **Hit Targets & Contrast:** Size every primary CTA and interactive control at `>= 44px` height/tap target (`min-h-[44px] min-w-[44px]`). Verify default, hover, focus-visible, and disabled states against `colorjs.io` (`>= 4.5:1` normal text, `>= 3.0:1` large text).
5. **Self-Hosted Typography:** Install `@fontsource-variable/*` packages (or `pyftsubset` WOFF2 bundles in `public/fonts/`) instead of runtime external font CDNs.
6. **Media Pipeline (`orion-media`):** Prepare raster/SVG assets with `orion-media` (`sharp`, `SVGO`, `vtracer`) with explicit `width`, `height`, `alt`, and SPDX-verified asset vault provenance. Use click-to-play facades instead of auto-loaded hero video payloads (`initial page transfer <= 600 KB`).
7. **Reduced Motion & Freeze Safety:** Include `@media (prefers-reduced-motion: reduce)` in global CSS disabling continuous animations and transitions. Never use `U+2013`, `U+2014`, or `U+2015` dashes in JSX, copy, `<title>`, or JSON-LD.

## Hand-Off to Render & Validate

- Stage 5: Run `orion-web-capture --repo <worktree> --out <bundle>` (or `--site`) to generate `1280x900`, `768x1024`, and `375x812` fold + full captures, `@axe-core/playwright`, `html-validate`, `colorjs.io`, overflow, fold, and dash checks.
- Stage 6: Dispatch fresh-context `web-render-reviewer` on the bundle before declaring implementation ready.
- Stage 8: Run `orion-web-audit` for Lighthouse CI (`Perf >= 0.90`, `A11y >= 0.95`, `SEO >= 0.95`), Unlighthouse multi-route crawl, `/llms.txt`, canonical, and `schema-dts` JSON-LD verification.

Load [Primitives, Assets, and Verification](references/primitives-and-assets.md) for concrete token wiring, hit-target rules, and pre-commit unit test patterns.
