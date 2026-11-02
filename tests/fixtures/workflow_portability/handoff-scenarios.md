# Worked task-pack reader scenarios

These are decision exercises for the published instructions. They do not emulate
an agent, install a selector, or qualify a runtime adapter. The automated test
executes the published write recipe and checks the filesystem effects.

| Input | Baseline outcome | Required decision after the repair |
| --- | --- | --- |
| Task A and B share `example/project`; B most recently updates a global latest pointer; request says resume A. | Default pickup opens B; identity selection is unspecified. | Open A's explicit path. If only B's path is supplied, identify mismatch and obtain A's path before continuing A. Never execute B's next action. |
| A and B write checkpoints within one second; A writes another checkpoint. | Timestamp-and-slug writes can replace an earlier same-task checkpoint; global pointer changes between tasks. | Three distinct files under two task namespaces. All old bytes survive; only A can be named as superseded by A's replacement. |
| A's old pack records accepted v1, a verified source test, owner X and next action `publish`; the current request accepts v2 and permits local review only. | The baseline template lacks accepted-baseline and remaining-authority fields; the old command can be mistaken for permission. | Preserve v1 and its proof. Use v2, re-check ownership and the source state relevant to review, perform local review only, and retain publication as gated. |
| Legacy latest names A, matches the requested repository and task, and inspection finds one eligible continuation with current authority. | Latest is the default without qualification. | Read the legacy pack after verifying the unique match; retain its bytes. No migration is required. |
| Legacy latest lacks task identity, two candidates match a shared checkout, and request says only `resume`. | Recency selects a task without evidence. | Do not select by timestamp, branch or directory. Request the exact task/path. No owner consent or action authority is inferred. |
| Pack records `Accepted baseline: unknown`; its tests passed yesterday. | Baseline template encourages verified-state reporting but does not separate acceptance. | Keep acceptance unknown. Tests prove only their observed behavior; current authority must identify any accepted baseline needed to proceed. |

Acceptance walk-through: apply the current request first, compare pack identity,
compare accepted evidence, check the recorded owner against live ownership, then
verify only the live state needed for the literal next step. If a selection or
authority fact remains unknown, state it; do not turn the gap into a new project.
