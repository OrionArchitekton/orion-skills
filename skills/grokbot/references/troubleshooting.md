# grokbot troubleshooting

## grokbot-send exit codes

| Exit | Meaning | Do |
|---|---|---|
| 0 | Accepted (and with `--wait`, the result arrived) | Nothing. |
| 2 | Usage error, or `--wait` with a request id that already has a result | Fix the arguments, or `--collect` that id, or pick a new id. |
| 3 | Missing or invalid config: URL or key unset; URL not https, malformed, or carrying credentials; key with whitespace (often a trailing newline from copy-paste); or `GROKBOT_OUTBOX_DIR` missing | Fix the environment. Neither value is ever echoed. |
| 4 | Not sent (DNS failure, refused connection, TLS failure), or refused by the webhook with a 4xx or a redirect | No run started, so it is safe to fix and resend. A 401 or 404 usually means the webhook trigger was deleted or replaced. Add a new trigger and update the secrets. |
| 5 | Accepted, but no result before `--timeout`, or `--collect` found nothing yet or found a file still being written | `grokbot-send --collect <request_id>` later. |
| 6 | **Outcome unknown**: the request may have reached Grok Bot, but no usable reply arrived (timeout, dropped connection, garbled response, a 5xx gateway error, or a 303) | **Do not resend.** `--collect <request_id>`, or `grokbot-read show <bot> --grep <request_id>`. |

## Request ids

Use a new request id for every task (the default generates one). A reused id is refused
only when its result file already exists. If an earlier run with that id is still going,
its late result would be read as the new task's result.

## A `--wait` result never arrives

- **The desktop app must be RUNNING on the machine that holds the outbox.** Local execution
  goes through it.
- Check the local-execution permission. Under "Ask every time", an approval raised by a
  webhook run expires after about 10 minutes, and the write never happens.
- Check the paths. `GROKBOT_OUTBOX_BOT_DIR` must be the folder as the APP sees it: a
  Windows path when the app runs on Windows and your agent runs in WSL.
- Read what the bot did: `grokbot-read show <bot> --grep <request_id>`.

## After a restart

| What restarted | Sending tasks | Driving the UI |
|---|---|---|
| Your agent session, or WSL | Keeps working | Re-attach the DevTools client |
| The desktop app (update, reboot) | Works again once the app is up | The debug port is gone. Relaunch with the flag, and ask the user first |
