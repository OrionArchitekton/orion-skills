# grokbot troubleshooting

## grokbot-send exit codes

| Exit | Meaning | Do |
|---|---|---|
| 0 | Accepted (and with `--wait`, the result arrived) | Nothing. |
| 2 | Usage error, or a request id that was already sent from this machine or already has a result | Fix the arguments, or `--collect` that id, or pick a new id. |
| 3 | Missing or invalid config: URL or key unset; URL not https, malformed, or carrying credentials; key with whitespace (often a trailing newline from copy-paste); or `GROKBOT_OUTBOX_DIR` missing | Fix the environment. Neither value is ever echoed. |
| 4 | Not sent (DNS failure, refused connection, TLS failure), or refused by the webhook with a 4xx (the response body is never shown) | No run started, so it is safe to fix and resend (the id is released). A 401 or 404 usually means the webhook trigger was deleted or replaced. Add a new trigger and update the secrets. |
| 5 | Accepted (HTTP 200), but no result file within `--timeout`; or `--collect` found nothing yet, or a file still being written | The run may still be going: `grokbot-send --collect <request_id>` later. |
| 6 | **Outcome unknown**: the request may have reached Grok Bot, but no usable reply arrived (a timed-out POST, dropped connection, garbled response, any redirect, a 2xx other than 200, or a 5xx) | **Do not resend.** `--collect <request_id>`, or `grokbot-read show <bot> --grep <request_id>`. |

## Request ids

Use a new request id for every task (the default generates one). Every id sent is recorded
in `GROKBOT_STATE_DIR` (default `~/.local/state/grokbot/sent`), and a repeat is refused, so
two runs can never share one result file. An id is released only when the send provably
started no run (exit 3 or 4). The ledger is per machine: don't reuse ids across machines.

## A `--wait` result never arrives

- **The desktop app must be RUNNING on the machine that holds the outbox.** Local execution
  goes through it.
- Check the local-execution permission. Under "Ask every time", an approval raised by a
  webhook run expires after about 10 minutes, and the write never happens.
- Check the paths. `GROKBOT_OUTBOX_BOT_DIR` must be the folder as the APP sees it: a
  Windows path when the app runs on Windows and your agent runs in WSL.
- Read what the bot did: `grokbot-read show <bot> --grep <request_id>`.
- The bot is asked to write `<request_id>.md.tmp` and rename it when complete, so a
  half-written result is never read. A lingering `.tmp` file means the write stalled.

## After a restart

| What restarted | Sending tasks | Driving the UI |
|---|---|---|
| Your agent session, or WSL | Keeps working | Re-attach the DevTools client |
| The desktop app (update, reboot) | Works again once the app is up | The debug port is gone. Relaunch with the flag, and ask the user first |
