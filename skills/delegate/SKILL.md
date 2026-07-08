---
name: delegate
description: Use when your Claude Code orchestrator should hand a scoped subagent, workflow, or background task to a NON-Anthropic model to keep it off the Anthropic budget - GPT via Codex (ChatGPT subscription), Grok (metered xAI key), or a free local model via Ollama. Triggers - "delegate this to codex/grok/gemma", "run this off-budget", "hand this to a cheaper model", "/delegate". NOT a router-proxy under ANTHROPIC_BASE_URL (that corrupts tool calls); this shells out to each vendor's own headless CLI so tool-calling stays native.
---

# delegate - off-Anthropic subagent delegation

Keep your Claude model orchestrating; push scoped subagent, bulk, or background work to a
non-Anthropic model CLI so it runs **off the Anthropic budget** with that vendor's **native**
tool calling. The mechanism is a headless-CLI subprocess, never an `ANTHROPIC_BASE_URL`
router-proxy: a proxy makes a non-Claude model speak Claude Code's Anthropic-shaped API, and the
translation shim corrupts tool calls (empty-string params, fake tool_use, mistranslated server
tools, infinite Read loops). Each vendor's own CLI speaks its own protocol natively, so the tool
loop stays intact and the work bills that vendor, not your Anthropic allocation.

## When to use (the decision)

Call `should_delegate(task)` (pure fn in `scripts/delegate.py`) or apply its rule directly:

| Task shape | Recommend | Why |
|---|---|---|
| off-budget + bulk + cheap-ok | **gemma** | free local model via Ollama, zero marginal cost |
| off-budget + needs X/Grok | **grok** | metered xAI key, X-search-grounded |
| off-budget + frontier coding | **codex** | GPT on the ToS-sanctioned ChatGPT subscription |
| not off-budget | **stay-claude** | keep it on the orchestrator |

Only delegate genuinely separable, well-scoped work.

**Terms-of-Service reality (the binding constraint, not the tooling).** Reusing a consumer
*subscription* inside a third-party harness is prohibited and enforced at most vendors. Codex on
a ChatGPT plan is the one sanctioned subscription path. Grok here uses a **metered API key**, not
a consumer login; the local Ollama lane has no subscription to reuse. Do NOT wire a consumer
Gemini, Grok, or Claude subscription through this layer; if you want those models, use their paid
API keys.

## Usage

```bash
D=~/.claude/skills/delegate/scripts/delegate.py
python3 "$D" codex "Refactor foo.py for readability" --dry-run   # inspect argv + env, run nothing
python3 "$D" codex "Summarize the diff in HEAD"                    # real off-budget codex run
# grok + gemma read their config from the environment at call time (keep secrets off the argv):
XAI_API_KEY=xai-...                          python3 "$D" grok "X sentiment on agentic coding"
OLLAMA_HOST=http://<your-ollama-host>:11434  python3 "$D" gemma "cheap bulk summarize"
```

From Python (fan-out, abstention-safe):
```python
import delegate
delegate.fanout([
    {"target": "codex", "task": "..."},
    {"target": "gemma", "task": "..."},   # runs concurrently; errored lens -> state:"pending", never dropped
])
```

## Security posture (enforced in code, asserted by tests)

- NEVER emits a sandbox-bypass flag (`--dangerously-*`, `-y`, `--yolo`, ...). Community CLI-bridges
  commonly bake those in; this layer exists partly to avoid that.
- Child env is a least-privilege WHITELIST: base keys + ONLY the target's own key; no
  sibling-provider keys, no GH/Slack/secret-manager/Anthropic tokens.
- Child CLI resolved by ABSOLUTE path (no planted-binary shadow).
- codex sandbox defaults read-only; `--write` escalates to `workspace-write` (never `danger-full-access`).
- codex stdin is `/dev/null` (guards the >=0.120 non-TTY exec deadlock).
- **Rule of Two:** a delegate acting on untrusted input must not also hold private access AND
  unsandboxed/consequential output at once. Keep the sandbox read-only unless you have vetted the input.

## Gotchas

- grok/gemma need their config at call time: an `XAI_API_KEY` for grok, an `OLLAMA_HOST` pointed
  at your endpoint for gemma. Without them the run fails honestly (no silent fallback). A shell
  HOOK cannot reliably wrap a secret-injection step (it fails open); call this from an interactive
  session or a timer/service that already has the secret in its environment.
- codex OAuth tokens are single-use/rotating; a concurrent Codex app-server (e.g. an IDE
  extension) can invalidate this one (`refresh_token_reused` 401). `codex login status` can LIE;
  trust a real run.
- gemma uses `keep_alive:-1` so a probe does not evict the hot local model.
- Parallel fan-out: codex app-server launches serialize via a broker; grok/gemma are independent.
  Reap an orphaned broker process by EXACT PID, never a broad `pkill -f`.
- The `grok -p/--single` flag is load-bearing: a positional prompt opens the interactive TUI and
  hangs a non-interactive caller.

## Boundary (defer to your own setup)

This skill is the DECISION + a uniform 3-target interface + fan-out; it is deliberately not a
credential manager or a deploy tool. Secret storage/injection, which host runs Ollama, and which
ChatGPT/xAI plan you hold are your environment's concern. Provide `XAI_API_KEY` and `OLLAMA_HOST`
from wherever you keep them; the skill only ever reads the one key its target needs and never
prints it. Adapt the three target CLIs to whichever vendor CLIs you have authenticated locally.

Verify a target is live before trusting it: `python3 scripts/delegate.py codex "Reply with exactly: PONG"`
should return `ok:true, off_anthropic:true` with an absolute `argv0` and a genuine model reply.
