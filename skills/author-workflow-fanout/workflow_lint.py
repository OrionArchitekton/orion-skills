#!/usr/bin/env python3
"""Heuristic smell-detector for Claude Code Workflow (scriptPath) fan-out scripts.

Not a full JS parser -- a deterministic linter for the three highest-cost,
most-recurring Workflow authoring bugs, each mapped to a durable lesson:

  no-catch        every agent() call must carry error handling (.catch or a
                  wrapper that does) so one dead search / rate-limit does not
                  crash the whole fan-out; the failure must become a ledger
                  entry + abstention, not an unhandled reject.
  budget-unguarded a while-loop reading budget.remaining()/spent() without
                  budget.total in the SAME condition runs to the 1000-agent
                  cap when no token target is set (remaining() is Infinity).
                  (loop-until-budget guard)
  meta-missing    a script with no `export const meta = {` is rejected at load.

To keep depth-tracking honest, string/template-literal bodies and comments are
blanked before structural analysis, so parentheses inside a prompt string do
not fool the statement splitter.

Usage: workflow_lint.py <script.js | ->
Exit: 0 clean | 1 findings (prints JSON) | 2 error (unreadable / bad usage).
"""
import json
import re
import sys


def blank_literals_and_comments(text):
    """Replace string/template/comment BODIES with spaces, preserving newlines
    and length so line numbers and bracket structure outside literals survive."""
    out = []
    i, n = 0, len(text)
    mode = None  # None | "'" | '"' | '`' | '//' | '/*'
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if mode is None:
            if c == "/" and nxt == "/":
                mode = "//"; out.append("  "); i += 2; continue
            if c == "/" and nxt == "*":
                mode = "/*"; out.append("  "); i += 2; continue
            if c in "'\"`":
                mode = c; out.append(c); i += 1; continue
            out.append(c); i += 1; continue
        # inside a literal or comment
        if mode == "//":
            if c == "\n": mode = None; out.append("\n")
            else: out.append(" ")
            i += 1; continue
        if mode == "/*":
            if c == "*" and nxt == "/": mode = None; out.append("  "); i += 2; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        # string / template literal
        if c == "\\":  # escaped char: blank both, keep length
            out.append("  "); i += 2; continue
        if c == mode:
            mode = None; out.append(c); i += 1; continue
        out.append("\n" if c == "\n" else " "); i += 1; continue
    return "".join(out)


def logical_lines(blanked, raw):
    """Yield (start_lineno, raw_text) for each logical statement. A statement
    ends at a newline where bracket depth is 0 AND the next non-blank line does
    not begin with '.' (method-chain continuation)."""
    raw_lines = raw.splitlines()
    bl_lines = blanked.splitlines()
    depth = 0
    buf, start = [], None
    i = 0
    while i < len(bl_lines):
        bl, rw = bl_lines[i], raw_lines[i] if i < len(raw_lines) else ""
        if start is None:
            start = i + 1
        buf.append(rw)
        # Track PAREN depth only: a call/argument list is what continues a
        # statement across lines. Braces/brackets (control blocks, object and
        # array literals) must NOT glue an agent() call to its neighbours, or
        # one .catch in a block would launder every unguarded call in it.
        for ch in bl:
            if ch == "(": depth += 1
            elif ch == ")": depth = max(0, depth - 1)
        # peek: is the next non-blank line a chain continuation?
        j = i + 1
        while j < len(bl_lines) and not bl_lines[j].strip():
            j += 1
        cont = j < len(bl_lines) and bl_lines[j].lstrip().startswith(".")
        if depth == 0 and not cont:
            yield start, "\n".join(buf)
            buf, start = [], None
        i += 1
    if buf:
        yield start or 1, "\n".join(buf)


AGENT_RE = re.compile(r"(?<![\w.])agent\s*\(")
WHILE_RE = re.compile(r"\bwhile\s*\(")
BUDGET_RE = re.compile(r"budget\.(remaining|spent)\s*\(")


def lint(text):
    blanked = blank_literals_and_comments(text)
    findings = []
    if not re.search(r"export\s+const\s+meta\s*=\s*\{", blanked):
        findings.append({"rule": "meta-missing", "line": 1,
                         "snippet": "no `export const meta = {` in script"})
    for start, stmt in logical_lines(blanked, text):
        bstmt = blank_literals_and_comments(stmt)
        if AGENT_RE.search(bstmt) and ".catch" not in bstmt:
            findings.append({"rule": "no-catch", "line": start,
                             "snippet": stmt.strip()[:120]})
        if WHILE_RE.search(bstmt) and BUDGET_RE.search(bstmt) \
                and "budget.total" not in bstmt:
            findings.append({"rule": "budget-unguarded", "line": start,
                             "snippet": stmt.strip()[:120]})
    return findings


def main(argv):
    if len(argv) != 2:
        print("usage: workflow_lint.py <script.js | ->", file=sys.stderr)
        return 2
    try:
        text = sys.stdin.read() if argv[1] == "-" else open(argv[1]).read()
    except OSError as e:
        print(f"ERROR: cannot read {argv[1]}: {e}", file=sys.stderr)
        return 2
    findings = lint(text)
    if not findings:
        print(json.dumps({"clean": True, "findings": []}))
        return 0
    print(json.dumps({"clean": False, "findings": findings}, indent=2))
    for f in findings:
        print(f"  {f['rule']} @L{f['line']}: {f['snippet']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
