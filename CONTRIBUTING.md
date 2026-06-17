# Contributing to orion-skills

Thanks for your interest. This is a **curated, opinionated personal library** of Claude
Code skills, not a community catalog — so the contribution model is intentionally narrow.

## What's welcome

- **Bug reports.** A skill's instructions are unclear, contradictory, or wrong; a path or
  command is broken; the frontmatter `description` doesn't match what the skill does.
- **Portability fixes.** A skill assumes something that doesn't hold on another OS, shell,
  or agent runtime (Codex, etc.).
- **Small clarity improvements** to existing skills — typos, tightened wording, a better
  worked example.

Open an issue first. For a small fix, a PR referencing that issue is fine.

## What's generally not accepted

- **New skills.** The set is deliberately small. New-skill PRs will usually be declined —
  not because the idea is bad, but because curation is the point. Fork freely instead;
  MIT makes that easy.
- **Large rewrites** of an existing skill's approach.

## Ground rules for any PR

- **No secrets, ever.** No API keys, tokens, real hostnames, internal URLs, or private
  paths — in code, examples, or commit messages. PRs that add them will be closed.
- **Keep `SKILL.md` lean.** Follow the progressive-disclosure convention: well under
  ~500 lines, with depth pushed into `references/`.
- **Match the house style.** kebab-case skill directories; a sharp, trigger-oriented
  `description`; second-person, actionable prose.
- Keep commits focused and explain the *why* in the message.

## Code of Conduct

Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating,
you agree to uphold it.
