# orion-skills

Part of [Cosmocrat OS](https://www.cosmocrat.ai/), a family of independent tools for human-directed AI work. [Choose a starting workflow](https://www.cosmocrat.ai/docs). This project keeps its own installation identifiers, releases, license and support boundaries.

A curated library of Orion-authored and adapted agent skills for disciplined coding-agent
workflows. The full library targets
[Claude Code](https://docs.claude.com/en/docs/claude-code); a narrowly validated
starter set also supports [Codex CLI](https://developers.openai.com/codex/skills).

These are workflow- and finish-discipline skills, not tool wrappers. They encode the
boring, high-leverage habits that keep an autonomous coding agent honest: don't claim
done until runtime is verified, don't write outside your declared scope, capture what
you learned so the next session is cheaper, and turn a loose task into a fire-ready
autonomous prompt.

## What are Agent Skills?

A [skill](https://www.agentskills.io) is a folder with a `SKILL.md` file: YAML
frontmatter (`name`, `description`) plus a Markdown body the agent loads on demand.
Claude Code and Codex load skills from their supported local skill directories.
Skills keep specialized procedures out of the base prompt and pull them in only
when the task matches.

## Install

### Claude Code

Claude Code auto-loads skills from `~/.claude/skills/` (v2.1.157+); **no marketplace or
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

### Optional Claude Code plugin

A clone or extracted source archive can also be loaded for one session, using
Claude Code **2.1.316** (the qualified version):

```bash
claude --plugin-dir "/absolute/path/to/orion-skills"
```

The plugin is published in [**v0.7.1**](https://github.com/OrionArchitekton/orion-skills/releases/tag/v0.7.1).
Use that release's source archive or a checkout of its tag, containing
`.claude-plugin/plugin.json`. Published **v0.7.0** predates the plugin manifest.
Invoke bundled skills as `/orion-skills:pre-pr`, `/orion-skills:ship`, etc.
The same `skills/` tree backs both loading paths. Direct installs above still use
`/pre-pr` and `/ship`; choose one copy deliberately if you also installed it directly.

Loading registers no hooks or MCP servers, grants no permissions, and does not arm
publishing. Some skills require additional setup; discovery is not qualification
of every workflow. See the [plugin loading and compatibility runbook](docs/runbooks/claude-plugin.md)
for clone/archive loading, helper paths, explicit updates/removal, per-skill limits,
and the existing Workflow prerequisite. No marketplace is provided; updates are manual. Codex qualification remains exactly the three skills below.

### Gemini CLI extension

The repository root is also a skills-only
[Gemini CLI extension](https://geminicli.com/docs/extensions/reference/):
`gemini-extension.json` declares the extension and Gemini CLI discovers every
`skills/*/SKILL.md` as an agent skill. It adds no MCP servers, hooks, commands or
context file.

```bash
gemini extensions install https://github.com/OrionArchitekton/orion-skills
gemini skills list   # the 32 skills appear under the orion-skills extension
```

**Compatibility:** under Gemini CLI only skill discovery is verified (Gemini CLI
0.70.0 lists all 32); no workflow is qualified on that host. Claude Code is the
target for the full library and Codex for the three skills below. Several skills
depend on Claude Code features and will not work as written under Gemini CLI:
`orion-deep-research` and `author-workflow-fanout` (Claude Code Workflow tool),
`readonly` and `scope-guard` (Claude Code PreToolUse hooks and tool names), and
`x`, `gist`, `grokbot` and `readonly` helper paths written for direct installs or
`${CLAUDE_PLUGIN_ROOT}`. Treat the rest as prose procedures that use whatever
tools and approvals the Gemini host provides.

### skills CLI

The [`skills` CLI](https://github.com/vercel-labs/skills) can list and install skills
straight from this repository. The commands below are pinned to `skills@1.5.26`, the
version verified for Claude Code; `npx` downloads that CLI package into its cache on
first use.

```bash
# see what the repository offers; installs no skills
npx skills@1.5.26 add OrionArchitekton/orion-skills --list

# install one skill globally for Claude Code
npx skills@1.5.26 add OrionArchitekton/orion-skills --skill ship -g -a claude-code
```

The CLI sends anonymous usage telemetry by default; set `DISABLE_TELEMETRY=1` to opt
out. The other agents the CLI can target have not been validated against this library.

### Codex CLI

The verified Codex starter set contains exactly these three portable
verification disciplines:

- [`reprobe-stale-premise`](skills/reprobe-stale-premise/SKILL.md)
- [`prove-control-binds`](skills/prove-control-binds/SKILL.md)
- [`prove-deploy-is-live`](skills/prove-deploy-is-live/SKILL.md)

In Codex, run each installer request as a separate prompt. If one skill already
exists, inspect or update that installation deliberately, then continue with
the other prompts; one existing destination cannot prevent the other skills
from being installed.

```text
$skill-installer Install https://github.com/OrionArchitekton/orion-skills/tree/main/skills/reprobe-stale-premise
```

```text
$skill-installer Install https://github.com/OrionArchitekton/orion-skills/tree/main/skills/prove-control-binds
```

```text
$skill-installer Install https://github.com/OrionArchitekton/orion-skills/tree/main/skills/prove-deploy-is-live
```

Or, from the root of a clone, copy missing skills to Codex's user skill
location. This fallback preserves an existing destination instead of
overwriting it:

```bash
(
  set -eu
  mkdir -p "$HOME/.agents/skills"
  for skill in reprobe-stale-premise prove-control-binds prove-deploy-is-live; do
    destination="$HOME/.agents/skills/$skill"
    if [ -e "$destination" ] || [ -L "$destination" ]; then
      printf 'preserving existing skill: %s\n' "$skill"
      continue
    fi
    cp -r "skills/$skill" "$destination"
  done
  for skill in reprobe-stale-premise prove-control-binds prove-deploy-is-live; do
    if [ ! -f "$HOME/.agents/skills/$skill/SKILL.md" ]; then
      printf 'incomplete skill installation: %s\n' "$skill" >&2
      exit 1
    fi
  done
)
```

The skills become available on the next turn; restart Codex if a new skill does
not appear. Invoke one explicitly as `$reprobe-stale-premise`,
`$prove-control-binds`, or `$prove-deploy-is-live`, or let its description match
the task.

This is direct local skill installation, not a plugin-directory listing. It
requires no plugin marketplace. The skills use whatever Git, GitHub, runtime,
network, and approval capabilities the active Codex host provides; they do not
provision credentials or connectors. The wider library has not yet been
validated as a Codex set.

## Examples

Prompts that exercise real skills. With the plugin loaded, prefix explicit
invocations as `/orion-skills:<name>`.

1. **`pre-pr`**: "Run pre-pr on this branch before I open the PR." Detects the real
   base branch, runs the repo's declared checks, secret-scans the diff, and returns a
   Pre-PR Report (CLEAR or ISSUES, with BLOCKING / WARNING / INFO findings).
2. **`prove-deploy-is-live`**: "Production was just deployed. Prove
   https://app.example.com is serving the new build, not the old image." Checks
   version identity, a real-route serve and an end-to-end success terminus, and says
   "wired but unproven" when it cannot prove it.
3. **`reprobe-stale-premise`**: "The handoff says the login bug is still broken and
   the fix PR never merged. Check that before we act on it." Re-probes fetched origin,
   real PR state and a reproduction before any work starts.
4. **`ship`** (operator-invoked): `/orion-skills:ship` on a finished change. RED/GREEN
   tests, then a PR, a fail-open review, and an independent runtime check before
   "done".
5. **`goal-prompt`**: "Turn 'migrate the billing worker to the new queue' into a
   /goal prompt with a checkable stop condition." Builds the prompt; never fires it.
6. **`incident-as-code`**: "We root-caused last night's outage. Close it out."
   Commits a `docs/solutions/` write-up (plus a runbook if the class recurs) into the
   affected repo.

## Skills

The catalog contains 32 skills. `reassert-guards-on-rewrite` and
`apply-review-findings` were added in v0.7.0; v0.7.1 adds optional plugin loading
(29 skills); 1.0.0 adds `orion-web-director`, `orion-frontend-builder` and
`web-render-reviewer`.

| Skill | What it does | Invoke when |
|---|---|---|
| [`readonly`](skills/readonly/SKILL.md) | Structural read-only session mode, sets a marker a PreToolUse hook reads to DENY the file-editing tools (Edit/Write/MultiEdit/NotebookEdit) until cleared; shell writes via `Bash` are outside the matcher. | An audit/research/census where the file-editing tools should be structurally unavailable, not merely discouraged. |
| [`scope-guard`](skills/scope-guard/SKILL.md) | Declares + self-audits write scope; with a paired hook, blocks out-of-scope writes mechanically. | Infra or multi-file work where edits must stay inside a boundary. |
| [`ship`](skills/ship/SKILL.md) | Finish-discipline gates: RED/GREEN tests → PR → adversarial fail-open review → independent runtime verification before "done". | You are about to say "done", "fixed", "deployed", or "shipped". |
| [`pre-pr`](skills/pre-pr/SKILL.md) | Repo-contract-aware preflight: detect base branch, run repo-local checks, secret-scan the diff, report severity-graded findings. | Before `gh pr create` / pushing a new PR branch. |
| [`reassert-guards-on-rewrite`](skills/reassert-guards-on-rewrite/SKILL.md) | Traces original guards through a rewrite and probes denial before the protected effect on every affected entry point; includes a synthetic tenant-write example. | Refactoring, porting or replacing guarded behavior. |
| [`apply-review-findings`](skills/apply-review-findings/SKILL.md) | Revalidates attributed findings at the current target, records evidence-backed dispositions, and binds final verification to immutable source. | Addressing reviews after source or PR state has changed. |
| [`incident-as-code`](skills/incident-as-code/SKILL.md) | Closes a resolved incident by committing a `docs/solutions/` doc (and a runbook when recurrent) into the affected repo. | An incident is root-caused and fixed, or a postmortem is asked for. |
| [`learn-capture`](skills/learn-capture/SKILL.md) | The compound loop's closing step: route accreted lessons to durable homes (agent memory vs repo `AGENTS.md`). | After a review, merge, or substantial task, "what did we learn?". |
| [`goal-prompt`](skills/goal-prompt/SKILL.md) | Turns a loose task into a fire-ready autonomous goal prompt: recon-grounded, rails-locked, with a transcript-checkable terminal condition. Builds the prompt; never fires it. | You want to author a `/goal` or `/deep-research` prompt for a hands-off run. |
| [`orion-deep-research`](skills/orion-deep-research/SKILL.md) | Research workflow with honest abstention accounting, a bounded knowledge-gap loop, a judge gate, and durable cited reports. Research principles are portable; the executable requires a compatible Claude Workflow tool. Native execution support is unqualified; see the author-attested origin record and its evidence limits. | You need a deep, multi-source report and have verified the executor and output prerequisites in the skill. |
| [`pre-compact`](skills/pre-compact/SKILL.md) | Captures a session into a persistent, queryable context pack so a fresh instance resumes with zero re-derivation. Engine-agnostic. | Before `/compact`, near the context limit, or handing off in-progress work. |
| [`x`](skills/x/SKILL.md) | Post to X (Twitter), manually or autonomously, behind a fail-closed safety harness: a redactor that abstains rather than leak, a per-day cap, and an arm-flag so it ships DISARMED. Direct OAuth1.0a, stdlib-only. | An agent should publish a short note to X, safely, manual or hands-off. |
| [`gist`](skills/gist/SKILL.md) | Publish an embeddable PUBLIC gist of ALREADY-public content, fetched over the unauthenticated raw URL so world-readability is structural, not a promise. Redactor backstop, per-day cap, ships DISARMED, human-gated. The safe pattern for a code surface. | You want to share/embed a file that is already in a public repo, safely. |
| [`tdd-loop`](skills/tdd-loop/SKILL.md) | Drives a spec to a CI-green PR through a self-correcting RED→GREEN→REFACTOR loop where every "green" binds to an artifact, a computed non-empty diff fed to reviewers, a clean secret-scan report, a captured suite exit code, never self-report. Self-contained; the gates are harness-agnostic. | You're implementing a feature/bugfix that must land as a hardened PR with no failing tests or unreviewed security-sensitive changes. |
| [`oss-loop`](skills/oss-loop/SKILL.md) | Carries an OSS tool from idea to a shipped, published release through one loop where the agent does everything reversible and a human touches only the irreversible gates, publish, merge, tag, DNS, secrets. Composes your prompt/research/TDD/launch skills; it does not reimplement them. | You're taking an OSS tool (or its next version) from spec to a published release hands-off, stopping at the irreversible gates. |
| [`chain-launcher`](skills/chain-launcher/SKILL.md) | Surfaces the exact next command for the implement phase after you approve a research/decision plan, a frictionless hand-off that never auto-crosses the human approval gate. | You just approved a research/decision plan and want the implement-phase command without re-deriving it. |
| [`tools-router`](skills/tools-router/SKILL.md) | A periodic recon builds a low-token, auth-aware index of the CLIs + MCP servers an agent can reach (preferring a *working* CLI over its MCP) and a thin fail-open hook injects it; redundancy is judged by which side actually works, never existence, and probe output is captured as redacted enums, never raw secrets. | The agent keeps being told which tool exists or which to use, and you want it to just know its surface. |
| [`prove-deploy-is-live`](skills/prove-deploy-is-live/SKILL.md) | Proves a deploy is actually live via three proofs (version identity, real-route serve, end-to-end behavior), because green CI, `docker ps` healthy, and `/health` 200 all stay green while the running artifact is the old image or the real route is dead. | You are about to call a deploy/restart/cutover "live" or "fixed", or verifying someone else's "it's deployed" claim. |
| [`prove-control-binds`](skills/prove-control-binds/SKILL.md) | Proves a gate, hook, monitor, or reaper actually fires by injecting a synthetic violation and watching it block from its own output, never by trusting a green check (green has two indistinguishable causes: nothing to catch, or catching nothing). | You are about to report a control "armed"/"protecting"/"done", or auditing one. |
| [`design-fail-closed-gate`](skills/design-fail-closed-gate/SKILL.md) | Authors unattended and self-policed gates that fail CLOSED by construction: gate on a structured token not free-text prose, bind every green to a re-readable artifact, respect the harness's inverting exit-code semantics, and prove the gate denies before calling it armed. | You are authoring a PreToolUse/pre-commit/pre-push hook, secret scanner, CI merge gate, auto-reaper, or LLM self-review enforcer. |
| [`author-workflow-fanout`](skills/author-workflow-fanout/SKILL.md) | Lints a Claude Code Workflow fan-out script before launch: flags an `agent()` call with no `.catch` (one rate-limited call rejects the whole run), a budget loop unguarded on `budget.total` (it runs to the 1000-agent cap), and a missing `meta` block. An optional local Node.js 24/POSIX helper preserves exact results and bounds one complete JSON snapshot in UTF-8 bytes; prose-only use remains supported. | You are authoring or editing a Workflow scriptPath / multi-agent fan-out and want it to fail safe, not silently. |
| [`reprobe-stale-premise`](skills/reprobe-stale-premise/SKILL.md) | Offers optional bounded local file probes with explicit confirmed/drifted/missing/unknown results; preserves manual verification. Treats any inherited claim you did not just verify (a handoff's "still broken," a teammate's diagnosis, "tool X doesn't exist," a registry's "UNBUILT") as a hypothesis, not a fact, and re-probes live ground truth (fetched origin, real PR state, an actual reproduction) before you act on it. | You're about to fix, build, or rely on something based on a claim you inherited rather than just verified, especially on a shared multi-session box. |
| [`triage-fanout-verdicts`](skills/triage-fanout-verdicts/SKILL.md) | Reads verify/judge fan-out output by its MECHANISM fields (votes cast, reads completed, verifier errors) instead of its verdict label, so a rate-limited "all refuted" or a dead "survived the skeptic" never coerces into a real verdict; ships a bundled bucketing script that exits 3 on any pending claim. | You're relaying or acting on a fan-out of verify/judge/skeptic verdicts, especially a unanimous one or one that saw rate limits or timeouts. |
| [`investigate`](skills/investigate/SKILL.md) | Four-phase root-cause debugging discipline (investigate, analyze, hypothesize, implement), gated on a red-capable reproduction you've actually run before any hypothesis, and a regression test that fails before the fix and passes after. | You're asked to debug an error, fix a bug, or figure out why something that used to work just broke. |
| [`document-release`](skills/document-release/SKILL.md) | Reviews release docs against the feature branch after code commits, polishes CHANGELOG voice without rewriting history, and asks before bumping VERSION. | On the feature branch after code commits and before PR merge. |
| [`office-hours`](skills/office-hours/SKILL.md) | Product-ideation partner: startup mode pushes six forcing questions until "everyone wants this" becomes a named customer with real demand evidence; builder mode is an enthusiastic riff partner for side projects. Both modes end in a reviewed design doc and one concrete next action, never in code. | You have an idea you haven't validated yet, or you're asked "is this worth building". |
| [`design-consultation`](skills/design-consultation/SKILL.md) | Proposes a complete, coherent design system (aesthetic, typography, color, layout, spacing, motion) as one package, not a menu, with an explicit safe-choices-vs-risks breakdown, then generates a working HTML preview page and writes DESIGN.md as the project's source of truth. | Starting a new project's UI with no DESIGN.md yet, or asked for "design system" / "brand guidelines". |
| [`orion-web-director`](skills/orion-web-director/SKILL.md) | Directs stages 1-3 and 9 of the 9-stage studio web lifecycle: canonical home preflight, asymmetric layout archetype, typography pairing, OKLCH tonal elevation, CRO fold rules, and SPDX license gates before implementation. | Starting or restyling a website or web app before writing frontend code. |
| [`orion-frontend-builder`](skills/orion-frontend-builder/SKILL.md) | Implements directed web specs using `@orion/registry` primitives, semantic landmarks, `>=44px` CTA hit targets, self-hosted `@fontsource-variable/*` fonts, `orion-media` assets, and `prefers-reduced-motion` guards. | Building or iterating frontend components and pages from a locked `DESIGN.md` and token contract. |
| [`web-render-reviewer`](skills/web-render-reviewer/SKILL.md) | Fresh-context Stage-6 critique of `orion-web-capture` bundles (`375`/`768`/`1280` fold and full PNGs, Axe, `html-validate`, `colorjs.io`, links, forms, and detector) returning severity-graded findings. | Reviewing a captured frontend bundle before shipping or merging a web PR. |
| [`delegate`](skills/delegate/SKILL.md) | Hands a scoped subagent, bulk, or background task to a non-Anthropic model CLI (Codex on a ChatGPT plan, Grok on a metered xAI key, or a free local model via Ollama) so it runs off the Anthropic budget with that vendor's native tool calling, behind a sandbox and env-scrub gate. Shells out to each vendor's own CLI; it is not an `ANTHROPIC_BASE_URL` router-proxy (a proxy corrupts tool calls). | You want subagent/workflow fan-out to run on another model off your Anthropic allocation, without the router-proxy tool-calling trap. |
| [`grokbot`](skills/grokbot/SKILL.md) | Hands a task to a bot in xAI's Grok Bot desktop app through the documented routine webhook, and gets the result back through an outbox file the bot writes with the app's local execution, so no UI is touched. Also reads any bot's chat from the app's local cache. Never resends a task that might already be running (it reports the outcome as unknown instead), refuses webhook redirects, rejects path-like request ids, and spells out the webhook-key plus local-execution trade-off. | Work needs an always-on bot with its own logged-in browser, a schedule, or your connected apps, and you want the result back in your coding session. |

### Worked examples (one per skill)

- **`readonly`**: Starting a "census the repo without editing it" pass:
  `~/.claude/skills/readonly/scripts/readonly-mode.sh on "audit: dependency graph"` →
  do the read-only work → `... off`. Any `Edit`/`Write` between the two is denied by
  `skills/readonly/hooks/pretooluse-readonly.sh`, which ships here and is executable.
  Scope it honestly: the matcher covers the file-editing tools, so a write issued
  through the `Bash` tool (`rm`, `sed -i`, redirection) does not reach the hook. The
  [skill doc](skills/readonly/SKILL.md) states that boundary and what closing it costs.
  Prove the part that is enforced on your own machine with
  `python3 skills/readonly/selftest.py`: it fires the real hook and asserts that eleven
  marker shapes (malformed, empty, unreadable, a directory, a dangling symlink) all
  DENY, while two control cases still allow, so an always-blocking gate could not pass.
- **`scope-guard`**: "Only touch `src/api/` this session." Activate, declare
  `allowed: ["src/api/**"]` / `excluded: ["src/db/**"]`; an attempt to edit
  `src/db/schema.sql` is reported as a Scope Violation and stopped.
- **`ship`**: You fixed an auth check and want to call it done. `ship` makes you prove the
  test went RED→GREEN, re-request approval on the *post-edit* diff, hunt fail-open paths,
  and hit the health endpoint, before the word "done".
- **`pre-pr`**: Before opening a PR, it detects the base branch from repo convention (not
  assuming `main`), greps the diff for credential patterns, and prints a
  `CLEAR | ISSUES` report with BLOCKING / WARNING / INFO findings.
- **`reassert-guards-on-rewrite`**: A tenant check moves into a shared wrapper.
  Probe allowed and denied writes through both API and batch paths; a denial
  passes only when no write occurred. The bundled Python example catches a
  check moved after the effect even when textual guard counts are unchanged.
- **`apply-review-findings`**: A review targets an older commit. Re-read each
  finding at the current revision, distinguish a real defect from an already
  fixed or gated item, and run proof from immutable source before claiming the
  final commit resolves it. Hosted PR replies still need their own authority.
- **`incident-as-code`**: A cache stampede is root-caused and patched. The skill writes
  `docs/solutions/2026-06-17-cache-stampede.md` (with grep-able `symptoms:`) into the
  affected repo and ships it via PR, the incident isn't "closed" until that lands.
- **`learn-capture`**: After the fix, you realized a config flag was load-bearing in a
  non-obvious way. `learn-capture` filters it against the "non-obvious / reusable /
  actionable" test and writes a one-note lesson to your agent memory or the repo's
  `AGENTS.md`.
- **`goal-prompt`**: "Build me a goal prompt to audit our timers." It runs two-tier recon
  to correct false premises, assembles a phased read-only brief, and emits a terminal
  condition the small `/goal` evaluator can actually check, then hands you the exact
  `/goal` line to fire yourself.
- **`orion-deep-research`**: "Research the state of X and save it." It fans out searches, verifies each claim by first-hand source reading, marks a rate-limited claim `unverified` (never `refuted`), reflects once to chase the gaps its own findings expose, then writes a cited report with a verification-provenance ledger.
- **`pre-compact`**: Context is at 90%. The skill verifies what *actually* shipped
  (not what you remember), writes a decision-shaped pack to a durable directory, and points
  a `LATEST.md` at it so the next instance resumes from evidence, not narrative.
- **`x`**: An autonomous loop has a one-line lesson worth sharing. It drafts the post,
  the fail-closed redactor checks it (ABSTAIN → don't publish), the per-day cap is checked,
  and, only if you've armed the system, it sends via direct OAuth1.0a; otherwise it
  dry-runs and prints the signed request's shape without sending. Ships DISARMED.
- **`gist`**: You want to embed a file from a public repo on a page. `/gist` fetches it
  over the unauthenticated raw URL (a 200 proves it's already world-readable), runs the
  redactor backstop, and, only if you've armed the system, `gh gist create --public`s it;
  otherwise it prints the dry-run plan and creates nothing. Human-gated, ships DISARMED.
- **`tdd-loop`**: "Implement the rate-limit feature and open a PR." The loop refuses to
  start without a spec and a clean branch, drives one vertical slice at a time
  (RED→GREEN→REFACTOR), then computes the diff and feeds *that* to a security +
  adversarial review, re-asserts a clean secret-scan report, and captures the full-suite
  exit code as the last action before the PR, each gate proven by an artifact you can
  re-read, not "I checked".
- **`oss-loop`**: "Ship v0.4 of my CLI." It builds the research prompt, you approve the
  plan, and it drives the change to a CI-green PR via `tdd-loop`, then STOPS: tagging,
  merging, and publishing to the package/image registry are *your* gates. After you merge
  it verifies the package index actually shows v0.4 live (because "merged" is not
  "published") and captures the lesson. The agent never crosses an irreversible gate.
- **`chain-launcher`**: You just approved the plan from a research run and need the
  implement step. Instead of re-typing the command, `chain-launcher <topic>` finds the
  paired implement launcher you saved and prints its fire line verbatim, you eyeball it
  and fire. It removes the friction of the hand-off without ever crossing the approval
  gate for you.
- **`tools-router`**: Your agent keeps being told "use the X CLI, not the Y MCP." A
  periodic recon probes each tool's auth + each MCP's health and renders a compact table;
  it recommends dropping a redundant MCP *only* when a working CLI covers it, and keeps a
  live MCP whose CLI is logged out (flagging the CLI instead), capturing auth as redacted
  enums, never raw probe output. A fail-open hook injects the table at session start, so
  the agent just knows its surface.
- **`prove-deploy-is-live`**: You merged a PR, `docker ps` says healthy, and `/health`
  returns 200, so you are about to report it live. This skill makes you hit the real
  declared route and confirm the running image is the merge SHA first, catching the
  container still on the old image before it pages you at 3am.
- **`prove-control-binds`**: You installed a pre-commit secret scanner and CI is green.
  This skill has you feed it a real-format `ghp_`-shaped token in a sandbox and watch it
  actually block, so you can tell a working gate from one that scans nothing and passes
  everything (green has two causes: nothing to catch, or catching nothing).
- **`design-fail-closed-gate`**: You are writing a PreToolUse hook to block a destructive
  command. This skill stops the silent fail-open trap (in Claude Code, an `exit 1` crash
  lets the tool run anyway), showing the exit-code semantics and the structured-token gate
  that make the safe verdict the structural default.
- **`author-workflow-fanout`**: You are about to launch a 12-agent fan-out to review a
  diff. You run `python3 workflow_lint.py review.js` first; it flags one `agent()` with no
  `.catch` (a single rate-limited call would reject the whole `parallel()` at 90%) and a
  `while (budget.remaining() ...)` loop with no `budget.total` guard (it would run to the
  hard agent cap). You wrap the call in `.catch(() => null)`, guard the loop, then launch.
  For a local Node.js consumer, opt into the bundled bounded-results helper:
  persist each result, emit one byte-bounded snapshot, then recover all originals
  separately with the saved final count. The recovery path and metadata count
  toward the snapshot budget; total process memory and disk usage are unbounded.
- **`reprobe-stale-premise`**: A resumed handoff says "the auth bug is still broken."
  Before touching code, you `git fetch origin` and re-run the failing case: it already
  reproduces clean, someone fixed it hours ago. You report `ALREADY-FIXED` instead of
  re-patching a solved problem.
- **`triage-fanout-verdicts`**: A 12-agent verify fan-out comes back "10 of 12 refuted."
  Reading the mechanism fields shows 10 of those had zero completed reads (one throttle
  window), not a real consensus. `python3 scripts/triage_verdicts.py verify.json` exits 3,
  flagging the decision PENDING instead of killing the build on a false refutation.
- **`investigate`**: "The auth flow throws a 500, fix it." Before touching code, you build
  one command that reproduces the 500 on demand, confirm three hypotheses in turn (the
  first two don't match the evidence), then fix the third, root cause, and write a
  regression test that fails without the fix and passes with it.
- **`document-release`**: Your feature branch adds a new CLI flag; before merging,
  `document-release` checks that branch's diff and updates release docs. It adds the flag
  to README's usage table, flags the CHANGELOG entry for a voice pass, and asks before
  bumping VERSION.
- **`office-hours`**: "I have an idea for a tool that tracks X." Startup mode pushes past
  "people would use this" to "Sarah, the ops manager at a 50-person logistics company,
  would pay for this today," forces two distinct implementation approaches before any code
  gets written, and closes the session with one concrete assignment and a design doc saved
  to disk.
- **`design-consultation`**: You're starting a new dashboard with no design system yet.
  The skill proposes a full system in one pass, tells you which choices are safe category
  defaults and which are deliberate risks, generates an HTML preview you can open in a
  browser, and only then writes DESIGN.md.
- **`orion-web-director`**: Before restyling a marketing site or dashboard, it verifies the
  canonical checkout with `orion-check-canonical-web-home`, selects one of 8 asymmetric
  archetypes, locks OKLCH tonal tokens and CRO fold rules in `DESIGN.md`, and gates every
  dependency against the SPDX commercial allowlist.
- **`orion-frontend-builder`**: Implementing a landing page from `DESIGN.md`: it composes
  `@orion/registry` primitives styled via consumer CSS tokens, sets `>=44px` primary CTA
  targets, bundles `@fontsource-variable/*` locally, prepares assets via `orion-media`, and
  adds `@media (prefers-reduced-motion: reduce)` before handing off to `orion-web-capture`.
- **`web-render-reviewer`**: Given a capture bundle from `orion-web-capture`, it opens the
  `375`, `768`, and `1280` fold/full PNGs, phone tiles, `qa_report.json`, and `detector/report.json`
  in a fresh read-only context and emits `VERDICT: READY` or `VERDICT: FIX FIRST` with the
  smallest targeted fix per finding.
- **`delegate`**: "Run this bulk summarize off-budget." `should_delegate` flags it bulk plus
  cheap-ok, so it routes to a free local model via Ollama; a frontier-coding task routes to
  Codex on the ChatGPT plan, an X-search task to Grok on a metered key. Each spawns that
  vendor's own headless CLI (native tool calling, off the Anthropic budget) behind a rail set:
  no sandbox-bypass flags, a whitelist env-scrub, an absolute-path CLI resolve, and a
  read-only default. A proxy under `ANTHROPIC_BASE_URL` is avoided on purpose; it corrupts
  tool calls.
- **`grokbot`**: "Have the research bot list this week's three biggest changes on the
  competitor's pricing page." `grokbot-send --wait` posts the brief to the bot's routine webhook,
  the bot browses from its cloud computer and writes its answer to the outbox folder through the
  desktop app, and the agent prints it about 30 seconds later. A 200 only means the run started;
  the outbox file is the proof it finished, and a timeout is collected later rather than re-sent.

## Data, network and privacy

- The plugin itself collects and stores no personal data, and loading it (as a
  Claude Code plugin, Gemini CLI extension or direct skill copy) sends nothing
  anywhere. There is no telemetry and no MCP server.
- Skills operate on the user's local repository files. Some write local state on the
  user's machine: publish cap ledgers and logs (`x`, `gist`), the `readonly` session
  marker, and handoff / context-pack notes (`pre-compact`).
- A skill runs when the user invokes it or when the host agent selects it for a
  matching task. On hosts that honor `disable-model-invocation: true` (Claude Code,
  Codex), `readonly`, `gist` and `ship` are operator-invoked only; the others,
  including `x`, `delegate` and `grokbot`, can be selected by the agent. Gemini CLI
  0.70.0 does not read that field, so its model can activate any of the 32 skills,
  including `gist` and `ship`: the default approval mode asks the operator to
  confirm each activation, while auto-approval modes do not. Sends to a third party happen only when
  such a skill runs and the user has configured it with their own credentials:
  - `x`: posts text to the X API (`POST https://api.x.com/2/tweets`, OAuth 1.0a
    user context). Ships disarmed: nothing is sent until the user creates the arm
    flag. Once armed, the supported autonomous mode (an agent loop, optionally
    nudged by the Stop-hook pattern in `skills/x/references/HOOK-PATTERN.md`) can
    publish without a separate request or approval for each post, limited by the
    redactor and a daily cap (default 5, `X_DAILY_CAP`).
  - `gist`: fetches an already-public file from `raw.githubusercontent.com` and
    creates a public gist through the GitHub CLI (`gh gist create`, the user's `gh`
    login). Operator-invoked only, and ships disarmed behind two arm flags.
  - `delegate`: sends the task text to another vendor's own CLI or endpoint: OpenAI
    Codex (the user's ChatGPT login), xAI's `grok` CLI (the user's `XAI_API_KEY`), or
    Ollama's `/api/generate` at `OLLAMA_HOST` (default `http://localhost:11434`; a
    remote host only if the user sets one).
  - `grokbot`: `grokbot-send` posts the task to the user's own Grok Bot routine
    webhook (`GROKBOT_WEBHOOK_URL` / `GROKBOT_WEBHOOK_KEY`). `grokbot-read` only reads
    the desktop app's local chat cache.
- Other network use goes through the user's own tools and the host agent's
  approvals:
  - Git remote and GitHub (`git fetch` / `git push`, `gh pr` / `gh repo` /
    `gh auth status`, the user's login): `reprobe-stale-premise` (fetches origin and
    queries PR state), `document-release` (detects the platform and base branch,
    pushes), `ship` and `oss-loop` (open PRs), `pre-pr` and `ship`
    (`git remote show origin` queries the remote's default branch), `tools-router`
    (its recon runs `gh auth status` among other CLI probes).
  - The user's own services: `prove-deploy-is-live` sends HTTP requests to the
    deployment being verified.
  - Web search and fetch through the host agent's tools, when available. These can
    reach third-party sites the user has never visited (and expose the user's IP
    address to them, depending on the host's fetch path):
    `orion-deep-research` (searches and fetches sources), `office-hours`,
    `design-consultation` (also browser screenshots when a browser tool exists) and
    `investigate`. `investigate` can search automatically for an unfamiliar error
    after it instructs the agent to strip hostnames, paths and identifiers; there is
    no separate consent prompt beyond the host's own tool approvals.
- Third-party services (X, GitHub, OpenAI, xAI, Ollama hosts, Grok Bot, any search
  provider) retain data under their own terms. This project keeps no copy.
- Support: [GitHub Issues](https://github.com/OrionArchitekton/orion-skills/issues).
  Contact: dan@danmercede.com.

## Authoring conventions

These skills follow Anthropic's authoring guidance:

- **Progressive disclosure**: keep `SKILL.md` lean (well under ~500 lines); push depth
  into `references/` files the agent loads only when needed (see `goal-prompt`).
- **Naming**: kebab-case directory names; verb-led for actions (`ship`, `learn-capture`),
  noun for domains.
- **A sharp `description`**: it is the only thing the model sees when deciding whether to
  invoke; state *when* to use the skill, with trigger phrases.

## License & attribution

MIT, see [LICENSE](LICENSE). Copyright (c) 2026 Dan Mercede.

`office-hours`, `investigate`, `design-consultation` and `document-release`
include adaptations of [garrytan/gstack](https://github.com/garrytan/gstack),
Copyright (c) 2026 Garry Tan, MIT. Verified comparison revision:
`4f435e45c517822014a852804c3da57bab121516`. `investigate` also adapts
[Matt Pocock's diagnosing-bugs](https://github.com/mattpocock/skills),
Copyright (c) 2026 Matt Pocock, MIT; verified comparison revision:
`4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. These snapshots do not establish
the unrecorded original import revisions. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
and each adapted skill's `PROVENANCE.md` and license files. Preserve those files
when copying a skill on its own.

The research implementation's [origin record](skills/orion-deep-research/PROVENANCE.md)
records Dan Mercede's 2026-11-02 attestation that this is his own workflow,
independently built with Claude's assistance. The original authoring chat was not
recovered; the record states that evidence limit. Retain its standalone notice.
Future collection releases require final qualification and explicit release
approval. Tests do not establish native execution or rights.

`reassert-guards-on-rewrite` and `apply-review-findings` adapt first-party
procedures with Dan Mercede's confirmed MIT adaptation rights; Dan maintains
both. Their standalone provenance notes and Orion MIT notices travel with them.
The bounded-results helper is original MIT-licensed JavaScript with its own
bundled notice. These qualifications do not expand the verified Codex starter set.

`learn-capture` operationalizes the **"compound loop"** idea (plan → work → review →
capture) popularized by [Every](https://every.to)'s writing on compounding engineering.
The concept is credited here as a courtesy; the skill's prose and routing are original.

## Contributions

This is a curated personal library, not a community catalog. Issues and bug reports are
welcome; new-skill pull requests are generally **not** accepted (the set is deliberately
small and opinionated). See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md).
