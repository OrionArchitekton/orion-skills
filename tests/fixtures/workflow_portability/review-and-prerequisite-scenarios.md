# Worked portability checks

| Consumer input | Observed baseline gap | Application of the repaired instructions |
| --- | --- | --- |
| API fallback changes on 401, while the existing suite only exercises 200. | File inventory and green preflight disclose no missing-seam warning. | Identify 401 fallback as changed behavior; API seam; no matching proof; report WARNING. Keep required repository checks load-bearing. |
| Markdown spelling correction, no recipe or behavior changes. | No explicit exclusion explains why extra tests are unnecessary. | Report INFO, prose-only coverage review not applicable. `git diff --check` and reference review suffice. |
| A documented recovery command changes. | It might be misclassified as docs-only despite changing supported behavior. | Name the CLI seam or an appropriate worked scenario. Missing proof is WARNING; a prose file extension does not exempt executable behavior. |
| Consumer has AGENTS.md and CI but no CLAUDE.md or optional `.claude` files. | Tool-specific preflight convention is prioritized. | Read AGENTS.md and CI, run declared checks; optional config/hook paths are not prerequisites. Do not install a hook. |
| Consumer is on a feature branch after committing code, prior to merge. | Frontmatter advertises after-merge use; body requires before-merge. | Trigger and body both apply before merge. Compare branch diff and update docs under current authority. |
| Consumer invokes after merging, on main. | Advertised trigger reaches an abort on main. | The repaired trigger applies before merge on a feature branch. A later documentation repair needs a separately scoped branch and release diff; do not treat main as this workflow's feature branch. |
| Consumer has TODOS.md but no `review/TODOS-format.md`, and bundled ship has four steps. | Reference to ship Step 5.5 cannot resolve. | Preserve existing TODOS format, inspect completion evidence from the diff, no external numbered-step dependency. |
| Research consumer has Node and Python but no Workflow tool. | Invocation asks for an unavailable executor without a prerequisite check. | Stop before invocation; report missing compatible Claude Workflow executor. No plain-Node execution or native-support claim. Separately authorized manual work is labeled manual. |
| Pure logic and simulated research tests pass. Native execution has not been observed. | Harness-agnostic lineage prose can be read as executable compatibility. | Report local test coverage only; native support unqualified, version 0.1.0 remains the private helper's own version. Author-attested origin is documented separately and does not establish runtime support. |

Reference audit: SKILL_DIR and RESEARCH_VAULT are consumer-supplied absolute paths.
The Workflow/agent facilities are explicit user prerequisites. Supporting
references and license links inside the changed skill directories must resolve
locally. Optional repository instruction files and TODO conventions are not
mandatory library dependencies. This file records worked decisions, not an
observed model compliance benchmark or live executor qualification.
