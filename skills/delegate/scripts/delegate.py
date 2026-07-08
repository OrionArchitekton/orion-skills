#!/usr/bin/env python3
"""delegate.py - off-Anthropic subagent-delegation layer for the Claude Code orchestrator.

Your Claude model stays the orchestrator; this hands a scoped subagent/background task to a
NON-Anthropic model CLI so the work runs off the Anthropic budget. Three targets:

  codex  -> `codex exec` on the operator's ChatGPT SUBSCRIPTION (ToS-sanctioned, off-budget)
  grok   -> `grok` (xAI Grok Build TUI) on a METERED XAI_API_KEY (sanctioned api-key path)
  gemma  -> a free local model via a self-hosted Ollama HTTP endpoint (zero marginal cost)

Mechanism is headless-CLI-subprocess, NOT an ANTHROPIC_BASE_URL router-proxy (which corrupts
tool calls). Security rails are enforced in code and asserted by tests:
  - NEVER emits a sandbox-bypass flag (see BYPASS_FLAGS);
  - scrubs the child env to a least-privilege WHITELIST (no sibling-provider keys, no
    GH/Slack/secret-manager tokens, no ANTHROPIC key);
  - resolves child CLIs by ABSOLUTE path (no bare-PATH planted-binary shadow);
  - defaults the codex sandbox to read-only (workspace-write only on explicit opt-in);
  - codex stdin is /dev/null (guards the >=0.120 non-TTY exec deadlock).

Design rationale: a router-proxy behind a custom ANTHROPIC_BASE_URL corrupts tool calls
(empty-string params, fake tool_use, mistranslated server tools -> infinite Read loops).
Shelling out to each vendor's own CLI keeps tool-calling native and the work off-budget.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TARGETS = frozenset({"codex", "grok", "gemma"})

# Flags that drop the sandbox / approval guardrail. This layer must NEVER emit any of these
# (the whole selling point over the community bridges that bake them in).
BYPASS_FLAGS = frozenset({
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-skip-permissions",
    "--skip-permissions",
    "--yolo",
    "--full-auto",
    "-y",
})

# Env keys the child NEVER needs and that would leak if inherited (denylist backstop; the
# real guard is the per-target WHITELIST in scrub_env).
_NEVER_LEAK = frozenset({
    "ANTHROPIC_API_KEY", "GH_TOKEN", "GITHUB_TOKEN", "DOPPLER_TOKEN",
    "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_CLOUD_API_KEY", "AI_AZURE_API_KEY",
})

# Base env every child gets (least-privilege): enough to run, nothing sensitive.
_BASE_ENV_KEYS = ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM")

# Per-target additional env keys the child legitimately needs.
_TARGET_ENV_KEYS = {
    "codex": (),                 # auth via ~/.codex/auth.json (HOME), no key in env
    "grok": ("XAI_API_KEY",),    # metered xAI api key
    "gemma": ("OLLAMA_HOST",),   # points at your Ollama endpoint
}

_GEMMA_MODEL_DEFAULT = "gemma4:26b"
_GEMMA_HOST_DEFAULT = "http://localhost:11434"


class DelegateError(Exception):
    """Raised on an unknown target, a missing CLI, or an invalid delegation request."""


def resolve_cli(name: str) -> str:
    """Absolute path to a child CLI, or raise. Never return a bare name (planted-binary shadow)."""
    path = shutil.which(name)
    if not path:
        raise DelegateError(f"CLI not found on PATH: {name!r}")
    return os.path.abspath(path)


def _assert_no_bypass(argv: list) -> list:
    for tok in argv:
        if tok in BYPASS_FLAGS or tok.startswith("--dangerous"):
            raise DelegateError(f"refusing to emit sandbox-bypass flag: {tok!r}")
    return argv


def build_argv(target: str, task: str, *, write: bool = False, model=None) -> list:
    """Build the child CLI argv for a spawned target. gemma is HTTP, not argv."""
    if target not in TARGETS:
        raise DelegateError(f"unknown delegation target: {target!r} (allowed: {sorted(TARGETS)})")
    if target == "gemma":
        raise DelegateError("gemma is the local Ollama HTTP lane; use dispatch(), not build_argv()")
    if not task or not task.strip():
        raise DelegateError("empty delegation task")

    cli = resolve_cli(target)
    if target == "codex":
        sandbox = "workspace-write" if write else "read-only"
        argv = [cli, "exec", "-s", sandbox]
        if model:
            argv += ["-m", model]
        argv.append(task)
    else:  # grok
        # grok headless: -p/--single prints the reply and EXITS. A POSITIONAL prompt opens the
        # interactive TUI and hangs a non-TTY caller, so the -p flag is load-bearing.
        argv = [cli, "-p", task, "--output-format", "json"]
    return _assert_no_bypass(argv)


def scrub_env(target: str, base_env=None) -> dict:
    """Least-privilege child env built by WHITELIST (not denylist): base keys + only the
    target's own needed key. Sibling-provider keys and GH/Slack/secret-manager/Anthropic
    tokens never survive."""
    if target not in TARGETS:
        raise DelegateError(f"unknown delegation target: {target!r}")
    src = os.environ if base_env is None else base_env
    env = {}
    for k in _BASE_ENV_KEYS:
        if k in src:
            env[k] = src[k]
    for k in _TARGET_ENV_KEYS[target]:
        if k in src:
            env[k] = src[k]
    # defensive backstop: strip any never-leak key that is not explicitly needed by this target
    needed = set(_TARGET_ENV_KEYS[target])
    for k in list(env):
        if k in _NEVER_LEAK and k not in needed:
            del env[k]
    return env


def should_delegate(task: dict) -> dict:
    """Decision helper (c): recommend where a task should run. Pure function.

    task keys (all optional): off_budget(bool), bulk(bool), cheap_ok(bool),
    needs_frontier(bool), needs_grok(bool), needs_x_search(bool).
    """
    if not task.get("off_budget"):
        return {"recommend": "stay-claude",
                "reason": "not flagged off-budget; keep on the Claude orchestrator"}
    if task.get("bulk") and task.get("cheap_ok"):
        return {"recommend": "gemma",
                "reason": "bulk + cheap-ok + off-budget -> free local model via Ollama, zero marginal cost"}
    if task.get("needs_grok") or task.get("needs_x_search"):
        return {"recommend": "grok",
                "reason": "needs xAI/Grok (X-search or grok-specific) -> grok via metered XAI key"}
    return {"recommend": "codex",
            "reason": "frontier/coding off-budget -> Codex on the sanctioned ChatGPT subscription"}


def _dispatch_gemma(task: str, *, model=None, timeout: int) -> dict:
    env = scrub_env("gemma")
    host = env.get("OLLAMA_HOST", _GEMMA_HOST_DEFAULT).rstrip("/")
    payload = json.dumps({
        "model": model or _GEMMA_MODEL_DEFAULT,
        "prompt": task,
        "stream": False,
        # keep_alive:-1 so a probe does NOT evict the hot local model.
        "keep_alive": -1,
    }).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode())
        return {"target": "gemma", "ok": True, "exit": 0,
                "output": (body.get("response") or "").strip()[:4000],
                "off_anthropic": True, "endpoint": f"{host}/api/generate"}
    except Exception as e:  # network/host errors are an honest failure, not a crash
        return {"target": "gemma", "ok": False, "exit": None, "error": str(e),
                "off_anthropic": True, "endpoint": f"{host}/api/generate"}


def dispatch(target: str, task: str, *, write: bool = False, model=None, timeout: int = 180) -> dict:
    """Run one delegated task on a non-Anthropic target; return a structured result.
    All three targets run OFF the Anthropic budget."""
    if target not in TARGETS:
        raise DelegateError(f"unknown delegation target: {target!r}")
    if target == "gemma":
        return _dispatch_gemma(task, model=model, timeout=timeout)

    argv = build_argv(target, task, write=write, model=model)
    env = scrub_env(target)
    try:
        proc = subprocess.run(
            argv, env=env,
            stdin=subprocess.DEVNULL,   # codex >=0.120 deadlocks on a non-TTY pipe otherwise
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, text=True,
        )
        return {"target": target, "ok": proc.returncode == 0, "exit": proc.returncode,
                "output": (proc.stdout or "").strip()[-4000:], "off_anthropic": True,
                "argv0": argv[0]}
    except subprocess.TimeoutExpired:
        return {"target": target, "ok": False, "exit": None, "error": f"timeout after {timeout}s",
                "off_anthropic": True, "argv0": argv[0]}


def fanout(specs: list, *, max_workers: int = 4) -> list:
    """Dispatch several delegations concurrently and join. Each spec: {target, task, write?, model?}.
    An errored/timed-out lens is tagged PENDING (abstention), never silently dropped.
    NOTE: codex app-server launches serialize via the broker; grok/gemma are independent
    processes and parallelize freely."""
    def _one(spec):
        try:
            r = dispatch(spec["target"], spec["task"], write=spec.get("write", False),
                         model=spec.get("model"), timeout=spec.get("timeout", 180))
            r["state"] = "ok" if r.get("ok") else "pending"
            return r
        except Exception as e:
            return {"target": spec.get("target"), "state": "pending", "ok": False, "error": str(e)}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(_one, specs))


def _main(argv: list) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Delegate a task to a non-Anthropic model (off-budget).")
    p.add_argument("target", choices=sorted(TARGETS))
    p.add_argument("task")
    p.add_argument("--write", action="store_true", help="codex: escalate sandbox to workspace-write")
    p.add_argument("--model", default=None)
    p.add_argument("--dry-run", action="store_true", help="print the argv/plan, do not run")
    p.add_argument("--timeout", type=int, default=180)
    a = p.parse_args(argv)
    if a.dry_run:
        if a.target == "gemma":
            print(json.dumps({"target": "gemma", "http": True,
                              "model": a.model or _GEMMA_MODEL_DEFAULT}, indent=2))
        else:
            print(json.dumps({"target": a.target,
                              "argv": build_argv(a.target, a.task, write=a.write, model=a.model),
                              "env_keys": sorted(scrub_env(a.target).keys())}, indent=2))
        return 0
    res = dispatch(a.target, a.task, write=a.write, model=a.model, timeout=a.timeout)
    print(json.dumps(res, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
