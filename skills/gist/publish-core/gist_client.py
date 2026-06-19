#!/usr/bin/env python3
"""publish-core gist client — publish an embeddable PUBLIC gist of content that is
ALREADY public.

WHY derive-from-public: a gist is a CODE surface, and a prose redactor is an
insufficient guard for real source (it enumerates private nouns; it cannot prove
the absence of an embedded secret or a structural leak). So this client NEVER
publishes arbitrary local code. It fetches content from a PUBLIC repo over the
UNAUTHENTICATED raw URL — if that 200s, the content is provably world-readable
already, which makes "already public" a structural fact, not a promise. The
redactor still runs as a belt-and-suspenders backstop. See
references/DERIVE-FROM-PUBLIC.md.

SAFETY (same shape as the /x client):
  * Dry-run (default) fetches + redaction-checks + prints the gist SHAPE only
    (files / bytes / lines / verdict / description). It NEVER creates a gist.
  * A live create requires --send AND both arm flags (the shared
    ~/.claude/state/publishers-armed AND the gist-specific
    ~/.claude/state/gist-publishers-armed, both absent by default) AND room
    under the daily cap. Disarmed or at-cap -> refuse.
  * Auth for the create is your existing `gh` token (needs the `gist` scope); no
    secret is read or printed here — `gh` handles it.

Source repo: pass --repo OWNER/REPO (or set $GIST_SOURCE_REPO); ref defaults to
`main` (or $GIST_SOURCE_REF).

Stdlib-only for the fetch (urllib); the create shells out to `gh gist create`.

CLI:
  gist_client.py create --path <repo-path> [--path ...] \
      [--repo OWNER/REPO] [--ref main] [--filename <name>] \
      [--desc "<description>"] [--ack-public-hits] [--send]

The redactor is a BACKSTOP on this path, not the guard: the unauthenticated raw
fetch already proved the content is world-readable, so an ABSTAIN is a false
positive (e.g. a public doc that legitimately shows `docker login` or a token
PREFIX in an example). It still blocks BY DEFAULT (fail-closed); a human who has
reviewed the printed hits and confirmed each is a benign already-public token
passes --ack-public-hits to proceed (explicit + logged).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import common

RAW_HOST = "https://raw.githubusercontent.com"
RAW_NETLOC = "raw.githubusercontent.com"


def raw_url(repo: str, ref: str, path: str) -> str:
    return f"{RAW_HOST}/{repo}/{ref}/{path.lstrip('/')}"


def fetch_public(repo: str, ref: str, path: str, timeout: int = 15) -> str:
    """GET the path over the UNAUTHENTICATED raw URL.

    Success is the proof the content is already world-readable. A 404 means the
    path/ref is wrong OR the repo is not public — either way, do NOT publish.
    """
    url = raw_url(repo, ref, path)
    req = urllib.request.Request(url, headers={"User-Agent": "publish-core-gist"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Enforce the "200 = world-readable on GitHub" invariant BY CONSTRUCTION,
            # not by trusting GitHub's redirect policy: urlopen follows 30x silently
            # (incl. cross-host), so pin the FINAL response host + status before
            # trusting the body as the already-public proof.
            final_netloc = urllib.parse.urlsplit(resp.geturl()).netloc
            if resp.status != 200 or final_netloc != RAW_NETLOC:
                raise RuntimeError(
                    f"raw fetch {url} resolved to {final_netloc} (status {resp.status}); "
                    f"refusing — the already-public proof requires a 200 from {RAW_NETLOC}"
                )
            try:
                return resp.read().decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RuntimeError(
                    f"raw fetch {url} returned binary or non-UTF-8 content; refusing "
                    "(a gist publishes text — fetch the textual source path)"
                ) from exc
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"raw fetch {url} -> HTTP {exc.code}: path/ref wrong or repo not public; "
            "refusing (derive-from-public requires a world-readable source)"
        ) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(
            f"raw fetch {url} failed: {exc}; "
            "refusing (derive-from-public requires a world-readable source)"
        ) from exc


def gist_filename(path: str, override: str | None) -> str:
    """Resolve the gist's display filename to a SINGLE base name.

    The result is later joined onto a temp dir (`Path(td) / name`), so it must
    never contain path components: an absolute path or a `../` segment would
    escape the temp dir and overwrite a real local file with fetched content.
    Reject anything that is not already a bare filename rather than silently
    rewriting it.
    """
    fn = override if override else path.rstrip("/").split("/")[-1]
    name = Path(fn).name
    if not name or name in (".", "..") or name != fn:
        raise ValueError(
            f"invalid gist filename: {fn!r} "
            "(must be a single filename with no path components)"
        )
    return name


def redaction_ok(content: str):
    """Backstop verdict over already-public content. ('PUBLISH', []) | ('ABSTAIN', hits)."""
    import redactor  # local sibling
    return redactor.decision(content)


def build_plan(files: dict, repo: str, ref: str, description: str) -> dict:
    """Pure: assemble the gist SHAPE + per-file redaction verdict (no network/create)."""
    entries = []
    abstained = False
    for name, content in files.items():
        verdict, hits = redaction_ok(content)
        if verdict != "PUBLISH":
            abstained = True
        entries.append({
            "filename": name,
            "bytes": len(content.encode("utf-8")),
            "lines": content.count("\n") + (1 if content and not content.endswith("\n") else 0),
            "verdict": verdict,
            "hit_classes": sorted({c for c, _ in hits}),
            # Keep the MASKED snippets (never raw secrets — redactor.scan masks
            # them) so a human can eyeball each matched value before --ack-public-hits.
            "hits": [{"class": c, "masked": m} for c, m in hits],
        })
    return {
        "repo": repo, "ref": ref, "description": description,
        "public": True, "files": entries, "clean": not abstained,
    }


def print_plan(plan: dict) -> None:
    print(f"  source repo : {plan['repo']}@{plan['ref']}  (fetched over public raw URL)")
    print(f"  public      : {plan['public']}")
    print(f"  description : {plan['description']!r}")
    print(f"  files       : {len(plan['files'])}")
    for f in plan["files"]:
        print(f"    - {f['filename']}  ({f['bytes']}B, {f['lines']} lines)  "
              f"redactor={f['verdict']}")
        # Print each MASKED hit so a human can eyeball the actual matched value
        # (not just its class) before deciding to --ack-public-hits.
        for h in f.get("hits", []):
            print(f"        HIT [{h['class']}] {h['masked']}")


def create_gist(files: dict, description: str) -> str:
    """Write files to a temp dir (preserving names) and `gh gist create --public`.

    Returns the gist URL printed by gh. Auth is gh's own token (never printed).
    """
    with tempfile.TemporaryDirectory() as td:
        td_resolved = Path(td).resolve()
        paths = []
        for name, content in files.items():
            p = (Path(td) / name).resolve()
            # Defense-in-depth: gist_filename already rejects path components, but
            # never let a key escape the temp dir and clobber a real local file.
            if td_resolved not in p.parents:
                raise ValueError(f"refusing unsafe gist filename: {name!r}")
            p.write_text(content, encoding="utf-8")
            paths.append(str(p))
        cmd = ["gh", "gist", "create", "--public", "--desc", description, *paths]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            raise RuntimeError(f"gh gist create failed (rc={out.returncode}): {out.stderr.strip()}")
        return out.stdout.strip()


def main(argv) -> int:
    if not argv or argv[0] != "create":
        print('usage: gist_client.py create --path <repo-path> [--path ...] '
              '[--repo OWNER/REPO] [--ref REF] [--filename N] [--desc "..."] '
              '[--ack-public-hits] [--send]', file=sys.stderr)
        return 2

    repo = os.environ.get("GIST_SOURCE_REPO", "")
    ref = os.environ.get("GIST_SOURCE_REF", "main")
    paths, filename, description, do_send, ack_hits = [], None, None, False, False
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--path" and i + 1 < len(argv):
            paths.append(argv[i + 1]); i += 2
        elif a == "--repo" and i + 1 < len(argv):
            repo = argv[i + 1]; i += 2
        elif a == "--ref" and i + 1 < len(argv):
            ref = argv[i + 1]; i += 2
        elif a == "--filename" and i + 1 < len(argv):
            filename = argv[i + 1]; i += 2
        elif a == "--desc" and i + 1 < len(argv):
            description = argv[i + 1]; i += 2
        elif a == "--ack-public-hits":
            ack_hits = True; i += 1
        elif a == "--send":
            do_send = True; i += 1
        else:
            i += 1

    if not repo:
        print("error: source repo required — pass --repo OWNER/REPO or set "
              "$GIST_SOURCE_REPO (must be a PUBLIC repo)", file=sys.stderr)
        return 2
    if not paths:
        print("error: at least one --path (repo-relative) is required", file=sys.stderr)
        return 2
    if filename and len(paths) > 1:
        print("error: --filename only valid with a single --path", file=sys.stderr)
        return 2
    description = description or f"From {repo}: {', '.join(paths)}"

    # 1. Fetch each path over the PUBLIC raw URL (the already-public proof).
    files = {}
    for p in paths:
        try:
            name = gist_filename(p, filename)
        except ValueError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            common.log_line(f"gist REFUSED reason=bad-filename path={p}")
            return 2
        # Refuse a basename collision rather than silently dropping a file: two
        # paths with the same basename (docs/README.md + examples/README.md) would
        # otherwise overwrite each other in this dict, shipping fewer files than
        # the user asked for. (--filename is already barred with multiple paths.)
        if name in files:
            print(f"error: duplicate gist filename {name!r} from path {p!r}; "
                  "two sources share a basename — rename one or fetch them in "
                  "separate gists", file=sys.stderr)
            common.log_line(f"gist REFUSED reason=filename-collision name={name}")
            return 2
        try:
            content = fetch_public(repo, ref, p)
        except RuntimeError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            common.log_line(f"gist REFUSED reason=fetch path={p}")
            return 3
        files[name] = content

    # 2. Redaction backstop. The raw-fetch already proved world-readability, so a
    #    hit is a false positive; it still BLOCKS by default (fail-closed) unless a
    #    human has reviewed the printed hits and passes --ack-public-hits.
    plan = build_plan(files, repo, ref, description)
    if not plan["clean"]:
        hit_classes = sorted({c for f in plan["files"] for c in f["hit_classes"]})
        if not ack_hits:
            print("VERDICT: ABSTAIN — redactor backstop flagged already-public content.")
            print_plan(plan)
            print(f"\n  hit classes: {hit_classes}")
            print("  This is a backstop on already-public content (the raw fetch proved it is")
            print("  world-readable). If you have reviewed each hit and it is a benign public")
            print("  token (e.g. a token PREFIX in an example), re-run with --ack-public-hits")
            print("  to proceed. Never ack a hit you have not eyeballed.")
            common.log_line(f"gist REFUSED reason=redactor-abstain classes={hit_classes}")
            return 3
        print(f"WARN: proceeding past {len(hit_classes)} backstop hit class(es) "
              f"{hit_classes} by explicit --ack-public-hits (content fetched from public "
              f"raw URL = already world-readable).")
        print_plan(plan)

    # 3. Dry-run (default).
    if not do_send:
        print("DRY-RUN: gist plan constructed, NOT created.")
        print_plan(plan)
        return 0

    # 4. Live create path (dual-arm-gated). A gist is a CODE surface: it needs
    #    BOTH the shared flag and its own gist-specific flag, so it never inherits
    #    "armed" from a lower-risk prose publisher.
    if not common.is_gist_armed():
        print(f"REFUSED: --send requested but the gist surface is DISARMED. A live "
              f"gist requires BOTH {common.ARM_FLAG_PATH} AND "
              f"{common.GIST_ARM_FLAG_PATH}. No gist created.")
        common.log_line("gist send REFUSED reason=disarmed")
        return 0

    # 5. Cap gate (fail-closed, in the LIVE path — not a separate manual step).
    #    Read the prior count and refuse at cap BEFORE creating anything.
    import cap_ledger  # local sibling
    if cap_ledger.at_cap("gist"):
        cap = common.CAPS["gist"]
        print(f"REFUSED: gist daily cap reached ({cap_ledger.current('gist')}/{cap} "
              f"for {common.day_key()}). No gist created.", file=sys.stderr)
        common.log_line(f"gist send REFUSED reason=at-cap count={cap_ledger.current('gist')}/{cap}")
        return 4

    try:
        url = create_gist(files, description)
        # Record the publish in the SAME live path (so repeated --send is capped).
        new_count = cap_ledger.increment("gist")
        common.log_line(f"gist send OK url={url} count={new_count}/{common.CAPS['gist']}")
        common.ensure_state_dir()
        with common.GIST_RECEIPTS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": common.iso_z(), "url": url,
                                 "repo": repo, "ref": ref,
                                 "files": list(files.keys())}) + "\n")
        print(f"CREATED: {url}")
        return 0
    except Exception as exc:  # noqa: live subprocess/network error
        common.log_line(f"gist send ERROR {type(exc).__name__}")
        print(f"CREATE ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(main(sys.argv[1:]))
