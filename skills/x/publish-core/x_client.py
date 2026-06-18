#!/usr/bin/env python3
"""publish-core X (Twitter) client — direct OAuth1.0a, no SDK.

Signs `POST https://api.x.com/2/tweets` with an X app's OAuth1.0a user-context
creds (X_API_KEY/X_API_SECRET consumer + X_ACCESS_TOKEN/X_ACCESS_TOKEN_SECRET
user). The OAuth2 bearer is read-only and cannot post as the user, so it is not
used here.

Creds are read from the ENVIRONMENT. Populate it however you manage secrets — a
`.env`, `doppler run -- ...`, `op run -- ...`, CI secrets, etc. Nothing is
hard-coded and no secret is read from disk by this module.

SAFETY:
  * Dry-run (default) BUILDS the fully-signed request and prints its SHAPE only
    (method / URL / which OAuth params are present / signature length / body).
    It never prints a token, a secret, or the Authorization header value, and
    never sends.
  * A live send requires BOTH --send AND the arm flag
    (~/.claude/state/publishers-armed). Disarmed -> refuse, exit 0, no send.

Stdlib-only (hmac/hashlib/base64/urllib).

CLI:
  x_client.py post --text "<tweet>" [--send]
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request

import common

TWEET_URL = "https://api.x.com/2/tweets"
CRED_NAMES = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")


def _enc(s: str) -> str:
    """RFC-3986 percent-encoding (OAuth1.0a leaves '~' unescaped)."""
    return urllib.parse.quote(str(s), safe="~")


def _creds_from_env():
    return {n: os.environ.get(n, "") for n in CRED_NAMES}


def build_signed_request(text: str, creds: dict) -> dict:
    """Return {method, url, headers, body, oauth_params} for POST /2/tweets.

    For the v2 JSON endpoint only the oauth_* params enter the signature base
    string (the JSON body is not form-encoded, so it is excluded) — the correct
    OAuth1.0a construction for api.x.com/2/tweets.
    """
    oauth = {
        "oauth_consumer_key": creds["X_API_KEY"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    param_string = "&".join(f"{_enc(k)}={_enc(v)}" for k, v in sorted(oauth.items()))
    base_string = "&".join(["POST", _enc(TWEET_URL), _enc(param_string)])
    signing_key = f"{_enc(creds['X_API_SECRET'])}&{_enc(creds['X_ACCESS_TOKEN_SECRET'])}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    oauth["oauth_signature"] = signature
    auth_header = "OAuth " + ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth.items()))
    body = json.dumps({"text": text})
    return {
        "method": "POST",
        "url": TWEET_URL,
        "headers": {"Authorization": auth_header, "Content-Type": "application/json"},
        "body": body,
        "oauth_params": oauth,
    }


def print_shape(req: dict, text: str) -> None:
    """Print request SHAPE only — never a token/secret/auth value."""
    oauth = req["oauth_params"]
    print(f"  method      : {req['method']}")
    print(f"  url         : {req['url']}")
    print(f"  body        : {req['body']}   (chars={len(text)})")
    print(f"  Content-Type: {req['headers']['Content-Type']}")
    print("  Authorization: OAuth header PRESENT (value withheld)")
    print(f"    params present: {', '.join(sorted(oauth.keys()))}")
    print(f"    oauth_signature: PRESENT (len={len(oauth['oauth_signature'])}, HMAC-SHA1, value withheld)")


def send(req: dict) -> dict:
    """Actually POST. Caller must have verified armed + cap + redaction."""
    data = req["body"].encode()
    r = urllib.request.Request(req["url"], data=data, method="POST")
    for k, v in req["headers"].items():
        r.add_header(k, v)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return {"status": resp.status, "body": resp.read().decode()}


def main(argv) -> int:
    if not argv or argv[0] != "post":
        print('usage: x_client.py post --text "<tweet>" [--send]', file=sys.stderr)
        return 2
    text, do_send, i = None, False, 1
    while i < len(argv):
        if argv[i] == "--text" and i + 1 < len(argv):
            text = argv[i + 1]; i += 2
        elif argv[i] == "--send":
            do_send = True; i += 1
        else:
            i += 1
    if not text:
        print("error: --text required", file=sys.stderr)
        return 2

    creds = _creds_from_env()
    missing = [n for n in CRED_NAMES if not creds[n]]
    using_synthetic = bool(missing)
    if using_synthetic:
        # Dry-run with synthetic creds so the signer can be exercised with NO
        # real secret present. Live send is impossible without real env creds.
        creds = {n: f"DUMMY_{n}" for n in CRED_NAMES}

    req = build_signed_request(text, creds)

    if not do_send:
        print("DRY-RUN: signed POST /2/tweets constructed, NOT sent."
              + (" [synthetic creds]" if using_synthetic else " [real creds in env]"))
        print_shape(req, text)
        return 0

    if not common.is_armed():
        print(f"REFUSED: --send requested but system is DISARMED (arm flag absent: {common.ARM_FLAG_PATH}). No tweet sent.")
        common.log_line("x send REFUSED reason=disarmed")
        return 0
    if using_synthetic:
        print("REFUSED: --send requested but real X_* creds are not in env "
              "(populate them via your secrets manager / env). No tweet sent.")
        common.log_line("x send REFUSED reason=no-real-creds")
        return 0
    try:
        result = send(req)
        common.log_line(f"x send OK status={result['status']}")
        common.ensure_state_dir()
        with common.X_RECEIPTS_PATH.open("a") as fh:
            fh.write(json.dumps({"at": common.iso_z(), "status": result["status"], "chars": len(text)}) + "\n")
        print(f"SENT: status={result['status']}")
        return 0
    except Exception as exc:  # noqa: live network error
        common.log_line(f"x send ERROR {type(exc).__name__}")
        print(f"SEND ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
