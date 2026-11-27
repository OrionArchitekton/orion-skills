# Orion Architekton Workflow Skills

A Claude plugin of ten Markdown-only skills that make a coding agent finish work properly: check a branch before opening a PR, stay inside an agreed scope, and don't call anything done until it's verified at runtime.

## Included skills

| Skill | What it does |
| --- | --- |
| `pre-pr` | Preflight a branch before opening a pull request: base branch, scope, diff review, and a scan of the diff for committed credentials. |
| `ship` | Take a finished change from green tests through a PR to verified-live, without claiming done before runtime confirms it. |
| `prove-deploy-is-live` | Prove a deploy is actually serving the new build: version identity, live traffic, and the changed behaviour. |
| `prove-control-binds` | Before calling a gate, hook, timer, or alert "armed", watch it fire against a real trigger. |
| `design-fail-closed-gate` | Design unattended gates and hooks so the safe verdict is the default and errors block instead of passing. |
| `scope-guard` | Declare the files and areas a task may touch, then report every edit against that boundary. |
| `goal-prompt` | Build a self-contained goal prompt and terminal condition for a long autonomous run, with recon first. |
| `chain-launcher` | After you approve a plan, surface the exact next command for the implement phase without firing it. |
| `incident-as-code` | Close a resolved incident by committing a solutions doc (and a runbook if it recurs) to the affected repo. |
| `learn-capture` | At the end of a task, write the lessons learned to your agent memory or the repo's docs so the next pass goes faster. |

## Example prompts

1. "Run pre-pr on this branch before I open the pull request."
2. "We just merged the fix. Use prove-deploy-is-live to confirm production is running the new build."
3. "Use scope-guard: you may only touch `src/billing/`. Refactor the invoice rounding and report every file you changed."
4. "The outage is root-caused and fixed. Use incident-as-code to write up the postmortem in this repo."

## Data & Privacy

Every skill in this plugin is a local Markdown instruction file. The plugin contains no code, makes no network calls, collects no telemetry, and needs no credentials, API keys, or accounts. Anything the agent does while following a skill happens through the tools and permissions you already granted it.

## Support

Report problems or ask questions at https://github.com/OrionArchitekton/orion-skills/issues.

## License

MIT. See the repository's `LICENSE` file.
