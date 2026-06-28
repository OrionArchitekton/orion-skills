# orion-skills

A small, curated library of original [Claude Code](https://docs.claude.com/en/docs/claude-code) skills for disciplined agent workflows.

These are workflow- and finish-discipline skills — not tool wrappers. They encode the
boring, high-leverage habits that keep an autonomous coding agent honest: don't claim
done until runtime is verified, don't write outside your declared scope, capture what
you learned so the next session is cheaper, and turn a loose task into a fire-ready
autonomous prompt.

## What are Agent Skills?

A [skill](https://www.agentskills.io) is a folder with a `SKILL.md` file: YAML
frontmatter (`name`, `description`) plus a Markdown body the agent loads on demand.
Claude Code auto-loads any skill under `~/.claude/skills/`. Skills keep specialized
procedures out of the base prompt and pull them in only when the task matches.

## Install

Claude Code auto-loads skills from `~/.claude/skills/` (v2.1.157+) — **no marketplace or
plugin required.** Copy any skill directory you want:

```bash
# one skill
cp -r skills/ship ~/.claude/skills/ship

# or all of them
cp -r skills/* ~/.claude/skills/
```

Then invoke a skill by name in Claude Code (e.g. `/ship`, `/pre-pr`), or let the model
auto-invoke it when the `description` matches the task. Skills that should only be
operator-invoked (never model-auto-invoked) carry `disable-model-invocation: true` in
their frontmatter.

## Skills

| Skill | What it does | Invoke when |
|---|---|---|
| [`readonly`](skills/readonly/SKILL.md) | Structural read-only session mode — sets a marker a PreToolUse hook reads to DENY every file-mutating tool until cleared. | An audit/research/census where nothing should change. |
| [`scope-guard`](skills/scope-guard/SKILL.md) | Declares + self-audits write scope; with a paired hook, blocks out-of-scope writes mechanically. | Infra or multi-file work where edits must stay inside a boundary. |
| [`ship`](skills/ship/SKILL.md) | Finish-discipline gates: RED/GREEN tests → PR → adversarial fail-open review → independent runtime verification before "done". | You are about to say "done", "fixed", "deployed", or "shipped". |
| [`pre-pr`](skills/pre-pr/SKILL.md) | Repo-contract-aware preflight: detect base branch, run repo-local checks, secret-scan the diff, report severity-graded findings. | Before `gh pr create` / pushing a new PR branch. |
| [`incident-as-code`](skills/incident-as-code/SKILL.md) | Closes a resolved incident by committing a `docs/solutions/` doc (and a runbook when recurrent) into the affected repo. | An incident is root-caused and fixed, or a postmortem is asked for. |
| [`learn-capture`](skills/learn-capture/SKILL.md) | The compound loop's closing step: route accreted lessons to durable homes (agent memory vs repo `AGENTS.md`). | After a review, merge, or substantial task — "what did we learn?". |
| [`goal-prompt`](skills/goal-prompt/SKILL.md) | Turns a loose task into a fire-ready autonomous goal prompt: recon-grounded, rails-locked, with a transcript-checkable terminal condition. Builds the prompt; never fires it. | You want to author a `/goal` or `/deep-research` prompt for a hands-off run. |
| [`pre-compact`](skills/pre-compact/SKILL.md) | Captures a session into a persistent, queryable context pack so a fresh instance resumes with zero re-derivation. Engine-agnostic. | Before `/compact`, near the context limit, or handing off in-progress work. |
| [`x`](skills/x/SKILL.md) | Post to X (Twitter) — manually or autonomously — behind a fail-closed safety harness: a redactor that abstains rather than leak, a per-day cap, and an arm-flag so it ships DISARMED. Direct OAuth1.0a, stdlib-only. | An agent should publish a short note to X, safely — manual or hands-off. |
| [`gist`](skills/gist/SKILL.md) | Publish an embeddable PUBLIC gist of ALREADY-public content — fetched over the unauthenticated raw URL so world-readability is structural, not a promise. Redactor backstop, per-day cap, ships DISARMED, human-gated. The safe pattern for a code surface. | You want to share/embed a file that is already in a public repo, safely. |
| [`tdd-loop`](skills/tdd-loop/SKILL.md) | Drives a spec to a CI-green PR through a self-correcting RED→GREEN→REFACTOR loop where every "green" binds to an artifact — a computed non-empty diff fed to reviewers, a clean secret-scan report, a captured suite exit code — never self-report. Self-contained; the gates are harness-agnostic. | You're implementing a feature/bugfix that must land as a hardened PR with no failing tests or unreviewed security-sensitive changes. |
| [`oss-loop`](skills/oss-loop/SKILL.md) | Carries an OSS tool from idea to a shipped, published release through one loop where the agent does everything reversible and a human touches only the irreversible gates — publish, merge, tag, DNS, secrets. Composes your prompt/research/TDD/launch skills; it does not reimplement them. | You're taking an OSS tool (or its next version) from spec to a published release hands-off, stopping at the irreversible gates. |
| [`chain-launcher`](skills/chain-launcher/SKILL.md) | Surfaces the exact next command for the implement phase after you approve a research/decision plan — a frictionless hand-off that never auto-crosses the human approval gate. | You just approved a research/decision plan and want the implement-phase command without re-deriving it. |
| [`tools-router`](skills/tools-router/SKILL.md) | A periodic recon builds a low-token, auth-aware index of the CLIs + MCP servers an agent can reach (preferring a *working* CLI over its MCP) and a thin fail-open hook injects it; redundancy is judged by which side actually works — never existence — and probe output is captured as redacted enums, never raw secrets. | The agent keeps being told which tool exists or which to use, and you want it to just know its surface. |

### Worked examples (one per skill)

- **`readonly`** — Starting a "no writes, just census the repo" pass:
  `~/.claude/scripts/readonly-mode.sh on "audit: dependency graph"` → do the read-only
  work → `~/.claude/scripts/readonly-mode.sh off`. Any `Edit`/`Write` between the two is
  denied by the hook.
- **`scope-guard`** — "Only touch `src/api/` this session." Activate, declare
  `allowed: ["src/api/**"]` / `excluded: ["src/db/**"]`; an attempt to edit
  `src/db/schema.sql` is reported as a Scope Violation and stopped.
- **`ship`** — You fixed an auth check and want to call it done. `ship` makes you prove the
  test went RED→GREEN, re-request approval on the *post-edit* diff, hunt fail-open paths,
  and hit the health endpoint — before the word "done".
- **`pre-pr`** — Before opening a PR, it detects the base branch from repo convention (not
  assuming `main`), greps the diff for credential patterns, and prints a
  `CLEAR | ISSUES` report with BLOCKING / WARNING / INFO findings.
- **`incident-as-code`** — A cache stampede is root-caused and patched. The skill writes
  `docs/solutions/2026-06-17-cache-stampede.md` (with grep-able `symptoms:`) into the
  affected repo and ships it via PR — the incident isn't "closed" until that lands.
- **`learn-capture`** — After the fix, you realized a config flag was load-bearing in a
  non-obvious way. `learn-capture` filters it against the "non-obvious / reusable /
  actionable" test and writes a one-note lesson to your agent memory or the repo's
  `AGENTS.md`.
- **`goal-prompt`** — "Build me a goal prompt to audit our timers." It runs two-tier recon
  to correct false premises, assembles a phased read-only brief, and emits a terminal
  condition the small `/goal` evaluator can actually check — then hands you the exact
  `/goal` line to fire yourself.
- **`pre-compact`** — Context is at 90%. The skill verifies what *actually* shipped
  (not what you remember), writes a decision-shaped pack to a durable directory, and points
  a `LATEST.md` at it so the next instance resumes from evidence, not narrative.
- **`x`** — An autonomous loop has a one-line lesson worth sharing. It drafts the post,
  the fail-closed redactor checks it (ABSTAIN → don't publish), the per-day cap is checked,
  and — only if you've armed the system — it sends via direct OAuth1.0a; otherwise it
  dry-runs and prints the signed request's shape without sending. Ships DISARMED.
- **`gist`** — You want to embed a file from a public repo on a page. `/gist` fetches it
  over the unauthenticated raw URL (a 200 proves it's already world-readable), runs the
  redactor backstop, and — only if you've armed the system — `gh gist create --public`s it;
  otherwise it prints the dry-run plan and creates nothing. Human-gated, ships DISARMED.
- **`tdd-loop`** — "Implement the rate-limit feature and open a PR." The loop refuses to
  start without a spec and a clean branch, drives one vertical slice at a time
  (RED→GREEN→REFACTOR), then computes the diff and feeds *that* to a security +
  adversarial review, re-asserts a clean secret-scan report, and captures the full-suite
  exit code as the last action before the PR — each gate proven by an artifact you can
  re-read, not "I checked".
- **`oss-loop`** — "Ship v0.4 of my CLI." It builds the research prompt, you approve the
  plan, and it drives the change to a CI-green PR via `tdd-loop` — then STOPS: tagging,
  merging, and publishing to the package/image registry are *your* gates. After you merge
  it verifies the package index actually shows v0.4 live (because "merged" is not
  "published") and captures the lesson. The agent never crosses an irreversible gate.
- **`chain-launcher`** — You just approved the plan from a research run and need the
  implement step. Instead of re-typing the command, `chain-launcher <topic>` finds the
  paired implement launcher you saved and prints its fire line verbatim — you eyeball it
  and fire. It removes the friction of the hand-off without ever crossing the approval
  gate for you.
- **`tools-router`** — Your agent keeps being told "use the X CLI, not the Y MCP." A
  periodic recon probes each tool's auth + each MCP's health and renders a compact table;
  it recommends dropping a redundant MCP *only* when a working CLI covers it — and keeps a
  live MCP whose CLI is logged out (flagging the CLI instead) — capturing auth as redacted
  enums, never raw probe output. A fail-open hook injects the table at session start, so
  the agent just knows its surface.

## Authoring conventions

These skills follow Anthropic's authoring guidance:

- **Progressive disclosure** — keep `SKILL.md` lean (well under ~500 lines); push depth
  into `references/` files the agent loads only when needed (see `goal-prompt`).
- **Naming** — kebab-case directory names; verb-led for actions (`ship`, `learn-capture`),
  noun for domains.
- **A sharp `description`** — it is the only thing the model sees when deciding whether to
  invoke; state *when* to use the skill, with trigger phrases.

## License & attribution

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Dan Mercede.

`learn-capture` operationalizes the **"compound loop"** idea (plan → work → review →
capture) popularized by [Every](https://every.to)'s writing on compounding engineering.
The concept is credited here as a courtesy; the skill's prose and routing are original.

## Contributions

This is a curated personal library, not a community catalog. Issues and bug reports are
welcome; new-skill pull requests are generally **not** accepted (the set is deliberately
small and opinionated). See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md).
