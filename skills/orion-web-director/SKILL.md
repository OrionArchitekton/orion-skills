---
name: orion-web-director
description: Use when starting or restyling any website or web app to direct the 9-stage studio lifecycle, choose an asymmetric layout archetype, pair typography, define OKLCH tonal tokens, and gate commercial licenses.
---

# Orion Web Director

Directs stages 1-3 and 9 of the 9-stage studio web lifecycle before implementation begins. Never jump straight to JSX or Tailwind classes without a checked canonical home, visual thesis, and token contract.

## The 9-Stage Studio Lifecycle

1. **Discovery:** Verify canonical repo ownership before editing: run `orion-check-canonical-web-home` when present (`command -v orion-check-canonical-web-home`, exit 0 required), or run the portable fallback (`git rev-parse --show-toplevel && git remote -v && git worktree list`) outside Orion workstations so edits never land in duplicate or legacy checkouts. Read `DESIGN.md` and `tokens/brand.tokens.json` if present, clarify audience, conversion goal, and polarity (dark or light).
2. **Creative Direction:** Write a one-sentence visual thesis, select one of the 8 asymmetric layout archetypes, pair display/body/mono typefaces, run a pre-code genericness self-check (confirming the thesis and palette would not fit an unrelated industry brief unchanged), and lock CRO proof-first fold rules (H1 + value proposition + proof + primary CTA visible within `1280x900` and `375x812`).
3. **Design System & Tokens:** Author `DESIGN.md` and W3C DTCG `tokens/brand.tokens.json`, map OKLCH tonal elevation layers, and pass `colorjs.io` WCAG 2.1 AA contrast (`>= 4.5:1` body/CTA, `>= 3.0:1` large display) before coding.
4. **Implementation:** Hand off to `orion-frontend-builder` (`@orion/registry`, semantic landmarks, `@fontsource-variable/*`, `>= 44px` hit targets, `orion-media`, `prefers-reduced-motion`).
5. **Render:** Capture `1280x900`, `768x1024`, and `375x812` fold + full bundles using `orion-web-capture` (with `--disable-gpu --use-angle=swiftshader-webgl --hide-scrollbars`).
6. **Critique:** Dispatch fresh-context `web-render-reviewer` against the captured bundle and reference.
7. **Iterate:** Apply only the smallest targeted fix per `BLOCKING` or `WARNING` finding, then re-capture.
8. **Validate:** Run `orion-web-audit` (`Perf >= 0.90`, `A11y >= 0.95`, `SEO >= 0.95`, Unlighthouse crawl, `/llms.txt`, canonical, JSON-LD `schema-dts`, zero `U+2013/2014/2015` dashes).
9. **Release:** Commit in an isolated `codex/` worktree, run `gitleaks`, open PR, and verify live deployment.

## Mandatory Gates

- **Canonical home preflight:** When `orion-check-canonical-web-home` is installed, `orion-check-canonical-web-home <target>` must exit `0` before any design or code edit; otherwise verify the active `git rev-parse --show-toplevel`, remote origin, and isolated feature worktree before editing.
- **Commercial license gate (SPDX):** Allow only `MIT`, `Apache-2.0`, `BSD-*`, `ISC`, `MPL-2.0`, `OFL-1.1`, and `CC0-1.0`. Reject `AGPL`, `GPL`, `BUSL`, or commercial-restricted tools (including Remotion, apca-w3, Lost Pixel, FLUX.1-dev, BRIA RMBG-2.0, and Depth-Anything-V2-Base/Large/Giant).
- **Zero long dashes:** Never emit `U+2013`, `U+2014`, or `U+2015` in copy, headings, titles, or JSON-LD.

## Reference Depth

Load [Archetypes, Tokens, and Motion Physics](references/archetypes-and-tokens.md) during Stages 2 and 3 for the 8 asymmetric layout archetypes, typography pairing rules, OKLCH tonal elevation recipe, AI-slop calibration rules, CRO fold checklist, UX microcopy discipline, and motion physics constraints.
