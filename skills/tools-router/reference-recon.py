#!/usr/bin/env python3
"""reference-recon.py — the tools-router generator PATTERN (illustrative skeleton).

Probes the CLIs + MCP servers a harness can reach, captures auth/health state WITHOUT
persisting raw secret-bearing output, computes AUTH-AWARE dedup recommendations, and
renders a compact index. Adapt the probe table, the MCP-list source, and the render to
your environment — this is a teaching skeleton, not drop-in code.

Run it OUT of band (a timer/cron/CI job), never on the session hot path.
"""
from __future__ import annotations
import os, re, shutil, subprocess

# --- secret redaction: belt-and-suspenders. The PRIMARY defense is never capturing raw
#     probe stdout (see probe_cli); this scrubs any field before it is rendered. ----------
_SECRET = [
    re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{3,}"),   # provider key shapes
    re.compile(r"(?i)\b\w*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD)\b\s*[:=]\s*\S+"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),                            # long hex
]
def redact(s: str) -> str:
    for pat in _SECRET:
        s = pat.sub("[REDACTED]", s)
    return s

# --- per-tool auth detection: NON-uniform. Each predicate is AFFIRMATIVE (find a
#     logged-in marker) over exit code AND a content signal — never "no error seen". ------
def authed_if_rc0(rc, out):           return "authed" if rc == 0 else "unauthed"
def authed_if_active_marker(rc, out): return "authed" if any(l.lstrip().startswith("*") for l in out.splitlines()) else "unauthed"
def authed_if_config(rc, out):        return "config_present" if (rc == 0 and "[default]" in out) else "no_config"  # local read != live auth
def authed_env(var):                  return "authed" if os.environ.get(var) else "indeterminate"  # env-var auth: indeterminate without the runtime env

# probe = (argv, detector, secret_bearing). secret_bearing probes never return their stdout.
# Tool names below are obviously-fake placeholders (except `gh`, a ubiquitous public example) —
# substitute your real CLIs.
PROBES = {
    "gh":        (["gh", "auth", "status"],          authed_if_rc0,           False),
    "cloudcli":  (["cloudcli", "auth", "list"],      authed_if_active_marker, False),  # rc0 even w/ 0 accounts -> parse the marker
    "paycli":    (["paycli", "config", "--list"],    authed_if_config,        True),   # PRINTS keys -> secret_bearing
    "vendorcli": (["vendorcli", "whoami"],           authed_if_rc0,           False),
    # env-var-auth tools are handled out of band (see build_inventory).
}

def _run(argv, timeout=12):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except Exception:
        return 124, ""  # timeout/crash -> never reads as authed

def probe_cli(name, runner=_run):
    argv, detect, secret = PROBES[name]
    rc, out = runner(argv, 12)
    state = detect(rc, out)
    # CRITICAL: never return raw stdout. A non-secret identity (account/email/org) is valuable
    # in the index but is omitted from this skeleton for safety — to add it, extract ONLY the
    # principal with a per-tool regex and pass it through redact(), never the raw output.
    return state, ""

# --- fail-soft parse of a NON-machine-readable tool list. Pin to STATUS WORDS, not glyphs
#     or column layout; unparseable rows -> 'unknown', never dropped. ----------------------
_STATUS = [("Needs authentication", "needs_auth"), ("Failed", "failed"), ("Connected", "connected")]
def parse_mcp_list(text):
    out = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or ": " not in line or " - " not in line:
            continue
        sid, rest = line.split(": ", 1)
        status = next((enum for word, enum in _STATUS if rest.endswith(word)), "unknown")
        out.append({"id": sid.strip(), "status": status})
    return out

# --- AUTH-AWARE dedup. Redundancy is relative to which side WORKS; the working side can be
#     either. Never auto-disable. -----------------------------------------------------------
SURFACES = [  # (surface, mcp-id predicate, cli name)
    ("github",   lambda i: i == "github",          "gh"),
    ("cloud",    lambda i: i.startswith("cloud-"), "cloudcli"),
    ("payments", lambda i: i == "payments",        "paycli"),
]
def dedup(clis, mcps):
    recs = []
    for surface, match, cli in SURFACES:
        matched = [m for m in mcps if match(m["id"])]
        if not matched:
            continue
        state = clis.get(cli, {}).get("state", "not_installed")
        mcp_works = any(m["status"] == "connected" for m in matched)
        cli_verified = state == "authed"
        cli_present  = state in ("authed", "config_present")
        if cli_verified and not mcp_works:
            action = "disable_mcp"                # working CLI fully covers a dead MCP
        elif cli_present and not mcp_works:
            action = "disable_mcp_weak"           # CLI present but unverified -> verify the key is live first
        elif mcp_works and not cli_verified:
            action = "flag_cli_unauthed"          # THE INVERSION: keep the working MCP, auth the CLI
        elif cli_verified and mcp_works:
            action = "note_overlap"               # both work -> human judgment, not an auto-kill
        else:
            action = "flag_surface"
        recs.append({"surface": surface, "action": action, "cli": cli})
    return recs

def build_inventory(mcp_text, runner=_run):
    clis = {}
    for name in PROBES:
        if not shutil.which(name):
            clis[name] = {"state": "not_installed"}; continue
        state, _ = probe_cli(name, runner)
        clis[name] = {"state": state}
    clis["model-api"] = {"state": authed_env("MODEL_API_KEY")}   # env-var-auth example
    mcps = parse_mcp_list(mcp_text)
    return clis, mcps, dedup(clis, mcps)

def render_table(clis, mcps, recs):
    lines = ["<!-- generated; rerun the recon, do not hand-edit -->", "# Tools (generated)", "",
             "| tool | kind | state |", "|---|---|---|"]
    for n, c in sorted(clis.items()):
        lines.append(f"| {n} | CLI | {c['state']} |")
    for m in sorted(mcps, key=lambda x: x["id"]):
        lines.append(f"| {m['id']} | MCP | {m['status']} |")
    if recs:
        lines += ["", "## Dedup (human-gated; never auto-applied)"]
        lines += [f"- [{r['action']}] {r['surface']} ({r['cli']})" for r in recs]
    return redact("\n".join(lines) + "\n")

if __name__ == "__main__":
    mcp_text = _run(["your-harness", "mcp", "list"])[1]   # adapt to your harness's list command
    clis, mcps, recs = build_inventory(mcp_text)
    print(render_table(clis, mcps, recs))                 # write atomically to your injected table path
