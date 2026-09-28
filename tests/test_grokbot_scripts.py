"""Contract tests for skills/grokbot/scripts (grokbot-send, grokbot-read)."""
import base64
import http.server
import importlib.machinery
import importlib.util
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "grokbot" / "scripts"
# The sent-id ledger must never write to the real home directory during tests.
os.environ.setdefault("GROKBOT_STATE_DIR", tempfile.mkdtemp(prefix="grokbot-test-state-"))


def load(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(SCRIPTS / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


gs = load("grokbot-send")
rd = load("grokbot-read")


def quiet(fn, *args, **kwargs):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class ArgumentContractTest(unittest.TestCase):
    def test_generated_request_id_is_filename_safe(self):
        opt = gs.parse_args(["do", "a", "thing"])
        self.assertEqual(opt["task"], "do a thing")
        self.assertTrue(gs.valid_request_id(opt["request_id"]))

    def test_unsafe_request_ids_are_rejected(self):
        for bad in ("../evil", "a/b", "a\\b", "", "x" * 65, "with space", ".."):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as ctx:
                quiet(gs.parse_args, ["--request-id", bad, "task"])
            self.assertEqual(ctx.exception.code, 2)

    def test_collect_needs_no_task_but_needs_a_safe_id(self):
        self.assertEqual(gs.parse_args(["--collect", "gb-1"])["collect"], "gb-1")
        with self.assertRaises(SystemExit) as ctx:
            quiet(gs.parse_args, ["--collect", "../x"])
        self.assertEqual(ctx.exception.code, 2)

    def test_request_id_with_trailing_newline_is_rejected(self):
        self.assertFalse(gs.valid_request_id("abc\n"))

    def test_non_finite_or_non_positive_timeout_is_a_usage_error(self):
        for bad in ("nan", "inf", "-5", "0"):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as ctx:
                quiet(gs.parse_args, ["--wait", "--timeout", bad, "task"])
            self.assertEqual(ctx.exception.code, 2)

    def test_unknown_flag_is_rejected_instead_of_sent_as_task_text(self):
        for bad in (["--wiat", "do x"], ["--timeout=60", "do x"]):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as ctx:
                quiet(gs.parse_args, bad)
            self.assertEqual(ctx.exception.code, 2)

    def test_double_dash_ends_options(self):
        self.assertEqual(gs.parse_args(["--", "--not-a-flag", "x"])["task"], "--not-a-flag x")

    def test_missing_task_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            quiet(gs.parse_args, [])
        self.assertEqual(ctx.exception.code, 2)

    def test_send_without_webhook_config_exits_3_before_any_network(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GROKBOT_WEBHOOK")}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(gs, "post", side_effect=AssertionError("posted")), \
                mock.patch("sys.argv", ["grokbot-send", "task"]), \
                self.assertRaises(SystemExit) as ctx:
            quiet(gs.main)
        self.assertEqual(ctx.exception.code, 3)


class DeliveryProtocolTest(unittest.TestCase):
    def test_fire_and_forget_body_has_no_delivery_instruction(self):
        body = gs.build_body({"task": "t", "context": None, "request_id": "gb-1", "wait": False})
        self.assertEqual(body, {"task": "t", "request_id": "gb-1"})

    def test_wait_body_names_the_bot_side_path(self):
        env = {"GROKBOT_OUTBOX_DIR": "/mnt/c/Users/me/out", "GROKBOT_OUTBOX_BOT_DIR": "C:\\Users\\me\\out"}
        with mock.patch.dict(os.environ, env):
            body = gs.build_body({"task": "t", "context": "c", "request_id": "gb-1", "wait": True})
            bot_path, local_path = gs.outbox_paths("gb-1")
        self.assertEqual(bot_path, "C:\\Users\\me\\out\\gb-1.md")
        self.assertEqual(local_path, "/mnt/c/Users/me/out/gb-1.md")
        self.assertEqual(body["deliver_to"], bot_path)
        self.assertIn(bot_path, body["task"])
        self.assertTrue(body["task"].startswith("t"))
        self.assertEqual(body["context"], "c")

    def test_single_machine_uses_one_folder(self):
        with mock.patch.dict(os.environ, {"GROKBOT_OUTBOX_DIR": "/tmp/out"}):
            os.environ.pop("GROKBOT_OUTBOX_BOT_DIR", None)
            self.assertEqual(gs.outbox_paths("gb-2"), ("/tmp/out/gb-2.md", "/tmp/out/gb-2.md"))

    def test_wait_returns_content_once_the_file_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gb-1.md"

            def writer():
                time.sleep(0.3)
                target.write_text("part")
                time.sleep(0.2)
                target.write_text("partial then complete")

            threading.Thread(target=writer).start()
            got = gs.wait_for_result(str(target), timeout=5, poll=0.1, settle=0.5)
        self.assertEqual(got, "partial then complete")

    def test_wait_strips_windows_bom_and_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gb-2.md"
            target.write_bytes("\ufeff391\r\nsecond line\r\n".encode("utf-8"))
            got = gs.wait_for_result(str(target), timeout=2, poll=0.1, settle=0.2)
        self.assertEqual(got, "391\nsecond line\n")

    def test_wait_times_out_with_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(gs.wait_for_result(str(Path(tmp) / "never.md"),
                                                 timeout=0.4, poll=0.1, settle=0.1))

    def test_wait_ignores_a_symlink_planted_at_the_result_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / "elsewhere.txt"
            secret.write_text("not a result")
            link = Path(tmp) / "gb-3.md"
            link.symlink_to(secret)
            self.assertIsNone(gs.wait_for_result(str(link), timeout=0.5, poll=0.1, settle=0.1))

    def test_wait_caps_an_oversized_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gb-4.md"
            target.write_text("x" * (gs.MAX_RESULT_BYTES + 10))
            got = gs.wait_for_result(str(target), timeout=2, poll=0.1, settle=0.2)
        self.assertTrue(got.endswith("[truncated]\n"))
        self.assertLessEqual(len(got), gs.MAX_RESULT_BYTES + 20)

    def test_printed_text_has_terminal_control_characters_removed(self):
        self.assertEqual(gs.printable("a\x1b[31mb\x07c\r\n\td"), "a[31mbc\n\td")
        self.assertEqual(rd.printable("a\x1b]0;x\x07b"), "a]0;xb")
        self.assertEqual(gs.printable("safe‮txt.exe"), "safetxt.exe")
        self.assertEqual(gs.printable("café 中文 \U0001f680"), "café 中文 \U0001f680")

    def test_wait_decodes_a_utf16_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gb-8.md"
            target.write_bytes("﻿Hi 中\r\n".encode("utf-16-le"))
            got = gs.wait_for_result(str(target), timeout=2, poll=0.1, settle=0.2)
        self.assertEqual(got, "Hi 中\n")

    def test_an_empty_file_is_not_a_result_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gb-9.md"
            target.write_bytes(b"")
            self.assertIsNone(gs.wait_for_result(str(target), timeout=0.5, poll=0.1, settle=0.1))

    def test_wait_refuses_a_request_id_that_already_has_a_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "gb-5.md").write_text("old")
            env = {"GROKBOT_OUTBOX_DIR": tmp, "GROKBOT_WEBHOOK_URL": "https://example.invalid/h",
                   "GROKBOT_WEBHOOK_KEY": "k"}
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(gs, "post", side_effect=AssertionError("posted")), \
                    mock.patch("sys.argv", ["grokbot-send", "--wait", "--request-id", "gb-5", "t"]), \
                    self.assertRaises(SystemExit) as ctx:
                quiet(gs.main)
        self.assertEqual(ctx.exception.code, 2)


    def test_collect_of_a_result_still_being_written_exits_5(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "gb-6.md").write_text("partial")
            with mock.patch.dict(os.environ, {"GROKBOT_OUTBOX_DIR": tmp}), \
                    mock.patch.object(gs, "wait_for_result", return_value=None), \
                    mock.patch("sys.argv", ["grokbot-send", "--collect", "gb-6"]), \
                    self.assertRaises(SystemExit) as ctx:
                quiet(gs.main)
        self.assertEqual(ctx.exception.code, 5)


    def test_a_request_id_is_sent_at_most_once_even_before_any_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"GROKBOT_OUTBOX_DIR": tmp, "GROKBOT_STATE_DIR": tmp + "/state",
                   "GROKBOT_WEBHOOK_URL": "https://example.invalid/h", "GROKBOT_WEBHOOK_KEY": "k"}
            posts = []
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(gs, "post", side_effect=lambda *a: posts.append(a) or (1, "{}")), \
                    mock.patch.object(gs, "wait_for_result", return_value=None):
                with mock.patch("sys.argv", ["grokbot-send", "--request-id", "gb-once", "t"]):
                    quiet(gs.main)
                with mock.patch("sys.argv", ["grokbot-send", "--wait", "--request-id", "gb-once", "t"]), \
                        self.assertRaises(SystemExit) as ctx:
                    quiet(gs.main)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(len(posts), 1)


    def test_an_outcome_unknown_send_keeps_its_id_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"GROKBOT_STATE_DIR": tmp, "GROKBOT_WEBHOOK_URL": "https://example.invalid/h",
                   "GROKBOT_WEBHOOK_KEY": "k"}
            with mock.patch.dict(os.environ, env), mock.patch.object(gs, "post", side_effect=SystemExit(6)), \
                    mock.patch("sys.argv", ["grokbot-send", "--request-id", "gb-u", "t"]), \
                    self.assertRaises(SystemExit):
                quiet(gs.main)
            self.assertTrue(os.path.exists(os.path.join(tmp, "gb-u")), "an id that may have run stays recorded")

    def test_wait_keeps_polling_through_a_transient_read_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gb-w.md"
            target.write_text("done")
            calls = {"n": 0}
            real = gs._read_result

            def flaky(path):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise PermissionError("locked by the writer")
                return real(path)

            with mock.patch.object(gs, "_read_result", side_effect=flaky):
                got = gs.wait_for_result(str(target), timeout=3, poll=0.1, settle=0.1)
        self.assertEqual(got, "done")

    def test_json_output_redacts_a_reflected_key_and_refused_ids_can_be_resent(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"GROKBOT_STATE_DIR": tmp, "GROKBOT_WEBHOOK_URL": "https://example.invalid/h",
                   "GROKBOT_WEBHOOK_KEY": "k-SECRET-888"}
            out = io.StringIO()
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(gs, "post", return_value=(1, '{"echo": "Bearer k-SECRET-888"}')), \
                    mock.patch("sys.argv", ["grokbot-send", "--json", "--request-id", "gb-j", "t"]), \
                    redirect_stdout(out), redirect_stderr(io.StringIO()):
                gs.main()
            self.assertNotIn("SECRET-888", out.getvalue())
            refused = mock.patch.object(gs, "post", side_effect=SystemExit(4))
            with mock.patch.dict(os.environ, env), refused, \
                    mock.patch("sys.argv", ["grokbot-send", "--request-id", "gb-k", "t"]), \
                    self.assertRaises(SystemExit):
                quiet(gs.main)
            self.assertFalse(os.path.exists(os.path.join(tmp, "gb-k")), "a refused id is released")


class WebhookUrlValidationTest(unittest.TestCase):
    def run_main(self, url):
        env = {"GROKBOT_WEBHOOK_URL": url, "GROKBOT_WEBHOOK_KEY": "gbk_SECRETVALUE123"}
        err = io.StringIO()
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(gs, "post", side_effect=AssertionError("posted")), \
                mock.patch("sys.argv", ["grokbot-send", "task"]), \
                redirect_stdout(io.StringIO()), redirect_stderr(err), \
                self.assertRaises(SystemExit) as ctx:
            gs.main()
        return ctx.exception.code, err.getvalue()

    def test_a_key_with_whitespace_is_refused_without_echoing_it(self):
        for key in ("sk-SECRET123\n", " sk-SECRET123", "sk-SEC RET123", "sk-SECRET123\x07"):
            env = {"GROKBOT_WEBHOOK_URL": "https://example.invalid/h", "GROKBOT_WEBHOOK_KEY": key}
            err = io.StringIO()
            with self.subTest(key=repr(key)), mock.patch.dict(os.environ, env), \
                    mock.patch.object(gs, "post", side_effect=AssertionError("posted")), \
                    mock.patch("sys.argv", ["grokbot-send", "task"]), \
                    redirect_stdout(io.StringIO()), redirect_stderr(err), \
                    self.assertRaises(SystemExit) as ctx:
                gs.main()
            self.assertEqual(ctx.exception.code, 3)
            self.assertNotIn("SECRET", err.getvalue())

    def test_url_config_errors_exit_3_not_outcome_unknown(self):
        for url in ("https://h:abc/", "https://u:p@example.com/h", "https://example.com/pa th",
                    "https://example.com/h\n"):
            with self.subTest(url=repr(url)):
                code, err = self.run_main(url)
                self.assertEqual(code, 3)
                self.assertNotIn("SECRETVALUE", err)

    def test_plain_http_to_a_remote_host_is_refused(self):
        code, _ = self.run_main("http://example.com/hook")
        self.assertEqual(code, 3)

    def test_a_malformed_url_is_refused_without_echoing_either_value(self):
        for url in ("gbk_SECRETVALUE123", "https://", "https:///nohost", "ftp://example.com/x"):
            with self.subTest(url=url):
                code, err = self.run_main(url)
                self.assertEqual(code, 3)
                self.assertNotIn("SECRETVALUE", err)
                self.assertNotIn(url, err) if len(url) > 8 else None


class _Handler(http.server.BaseHTTPRequestHandler):
    status = 200
    seen = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _Handler.seen.append((self.headers.get("Authorization"), json.loads(self.rfile.read(length))))
        self.send_response(_Handler.status)
        self.end_headers()
        self.wfile.write(b'{"success":true,"runUuid":"r-1"}')

    def log_message(self, *args):
        pass


class WebhookPostTest(unittest.TestCase):
    def setUp(self):
        _Handler.seen = []
        self.server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/hook"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_post_sends_bearer_header_and_body(self):
        _Handler.status = 200
        attempts, text = gs.post(self.url, "k-123", {"task": "t", "request_id": "gb-1"})
        self.assertEqual(attempts, 1)
        self.assertIn("runUuid", text)
        auth, body = _Handler.seen[0]
        self.assertEqual(auth, "Bearer k-123")
        self.assertEqual(body["request_id"], "gb-1")

    def test_refused_post_exits_4_after_exactly_one_attempt(self):
        _Handler.status = 401
        with self.assertRaises(SystemExit) as ctx:
            quiet(gs.post, self.url, "bad", {"task": "t", "request_id": "gb-1"})
        self.assertEqual(ctx.exception.code, 4)
        self.assertEqual(len(_Handler.seen), 1)

    def test_status_classification(self):
        # Only 200 is documented as "run started". A 4xx is refused (no run, safe to fix and
        # resend). Anything else reached a server without a clean answer: outcome unknown.
        for status, expected in ((200, 0), (404, 4), (401, 4), (202, gs.EXIT_UNKNOWN),
                                 (204, gs.EXIT_UNKNOWN), (302, gs.EXIT_UNKNOWN), (307, gs.EXIT_UNKNOWN),
                                 (303, gs.EXIT_UNKNOWN), (502, gs.EXIT_UNKNOWN), (504, gs.EXIT_UNKNOWN)):
            _Handler.status = status
            _Handler.seen = []
            with self.subTest(status=status):
                if expected == 0:
                    attempts, _ = quiet(gs.post, self.url, "k", {"task": "t", "request_id": "gb-s"})
                    self.assertEqual(attempts, 1)
                else:
                    with self.assertRaises(SystemExit) as ctx:
                        quiet(gs.post, self.url, "k", {"task": "t", "request_id": "gb-s"})
                    self.assertEqual(ctx.exception.code, expected)
                self.assertEqual(len(_Handler.seen), 1)

    def test_an_error_body_that_reflects_the_key_is_redacted(self):
        class Reflect(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(401)
                self.end_headers()
                self.wfile.write(("bad auth: " + self.headers.get("Authorization", "")).encode())

            def log_message(self, *args):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Reflect)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        err = io.StringIO()
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(err), self.assertRaises(SystemExit):
                gs.post(f"http://127.0.0.1:{srv.server_address[1]}/hook", "k-SECRET-777",
                        {"task": "t", "request_id": "gb-r"})
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertNotIn("SECRET-777", err.getvalue())

    def test_the_error_body_is_never_printed(self):
        class Body(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'{"echo": "BODY-MARKER-555"}')

            def log_message(self, *args):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Body)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit):
                gs.post(f"http://127.0.0.1:{srv.server_address[1]}/hook", "k", {"task": "t", "request_id": "gb-b"})
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertNotIn("BODY-MARKER-555", out.getvalue() + err.getvalue())

    def test_only_a_certificate_failure_counts_as_not_sent_among_tls_errors(self):
        import ssl
        import urllib.error
        for reason, expected in ((ssl.SSLCertVerificationError("bad cert"), 4),
                                 (ssl.SSLEOFError("eof during write"), gs.EXIT_UNKNOWN),
                                 (ssl.SSLError("write failed"), gs.EXIT_UNKNOWN)):
            opener = mock.Mock()
            opener.open.side_effect = urllib.error.URLError(reason)
            with self.subTest(reason=type(reason).__name__), \
                    mock.patch.object(gs.urllib.request, "build_opener", return_value=opener), \
                    self.assertRaises(SystemExit) as ctx:
                quiet(gs.post, "https://example.invalid/h", "k", {"task": "t", "request_id": "gb-t"})
            self.assertEqual(ctx.exception.code, expected)

    def test_a_lost_response_is_outcome_unknown_and_names_the_request_id(self):
        class Slow(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                time.sleep(1.5)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Slow)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        err = io.StringIO()
        try:
            with mock.patch.object(gs, "TIMEOUT", 0.3), redirect_stdout(io.StringIO()), \
                    redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
                gs.post(f"http://127.0.0.1:{srv.server_address[1]}/hook", "k",
                        {"task": "t", "request_id": "gb-lost-1"})
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(ctx.exception.code, gs.EXIT_UNKNOWN)
        self.assertIn("gb-lost-1", err.getvalue())
        self.assertIn("do not resend", err.getvalue().lower())

    def test_a_malformed_status_line_is_outcome_unknown_not_a_traceback(self):
        class Garbage(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.wfile.write(b"NOT-HTTP\r\n\r\n")

            def log_message(self, *args):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Garbage)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(SystemExit) as ctx:
                quiet(gs.post, f"http://127.0.0.1:{srv.server_address[1]}/hook", "k",
                      {"task": "t", "request_id": "gb-lost-2"})
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(ctx.exception.code, gs.EXIT_UNKNOWN)

    def test_a_refused_connection_is_not_sent(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        with self.assertRaises(SystemExit) as ctx:
            quiet(gs.post, f"http://127.0.0.1:{port}/hook", "k", {"task": "t", "request_id": "gb-7"})
        self.assertEqual(ctx.exception.code, 4)

    def test_a_redirect_is_refused_and_the_key_never_reaches_the_second_host(self):
        reached = []

        class Recorder(http.server.BaseHTTPRequestHandler):
            # urllib turns a redirected POST into a GET, so record EVERY method.
            def _record(self):
                reached.append((self.command, self.headers.get("Authorization")))
                self.send_response(200)
                self.end_headers()

            do_GET = do_POST = do_HEAD = _record

            def log_message(self, *args):
                pass

        other = http.server.HTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=other.serve_forever, daemon=True).start()
        target = f"http://127.0.0.1:{other.server_address[1]}/stolen"

        class Redirect(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers()

            def log_message(self, *args):
                pass

        first = http.server.HTTPServer(("127.0.0.1", 0), Redirect)
        threading.Thread(target=first.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(SystemExit) as ctx:
                quiet(gs.post, f"http://127.0.0.1:{first.server_address[1]}/hook", "k-9",
                      {"task": "t", "request_id": "gb-1"})
            self.assertEqual(ctx.exception.code, gs.EXIT_UNKNOWN)
            self.assertEqual(reached, [])
        finally:
            for srv in (first, other):
                srv.shutdown()
                srv.server_close()


def blob_name(key):
    return base64.b32encode(key.encode()).decode().rstrip("=").lower() + ".blob"


class CacheReaderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        store = Path(self.tmp.name)
        acct = "sand.client.slice.account.example%7Cuser_X"
        roster = {"schemaVersion": 4, "value": {"rows": [
            {"id": "aaaa1111-0000", "name": "Helper", "updatedAt": 1790552000000, "lastEntry": {"text": "391"}},
            {"id": "bbbb2222-0000", "name": "Other", "updatedAt": 1790551000000, "lastEntry": {"text": "ok"}},
        ]}}
        # Shapes observed in the 0.58.0 Windows app.
        transcript = {"schemaVersion": 4, "value": {"entries": [
            {"kind": "message", "role": "user", "content": "hello", "timestampMs": 1790551900000},
            {"kind": "send-message", "message": {"type": "text", "content": "gb-1 ok"},
             "timestampMs": 1790551920000},
            {"kind": "event", "event": {"type": "automation", "action": "created",
                                        "automationId": "a-1", "automationName": "Example routine"},
             "timestampMs": 1790551930000},
        ]}}
        (store / blob_name(f"{acct}.roster.last-roster")).write_text(json.dumps(roster))
        (store / blob_name(f"{acct}.transcript.replicas.aaaa1111-0000")).write_text(json.dumps(transcript))
        (store / "not-a-blob.txt").write_text("x")
        self.store = str(store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_roster_lists_bots_newest_first(self):
        self.assertEqual([r["name"] for r in rd.roster(self.store)], ["Helper", "Other"])

    def test_transcript_by_name_or_id_prefix_renders_every_entry_kind(self):
        by_name = rd.transcript(self.store, "helper")
        self.assertEqual(by_name, rd.transcript(self.store, "aaaa1111"))
        self.assertEqual([e["text"] for e in by_name], ["hello", "gb-1 ok", "Example routine: automation created"])
        self.assertEqual([e["role"] for e in by_name], ["user", "bot", "event"])

    def test_unknown_bot_raises_lookup_error(self):
        with self.assertRaises(LookupError):
            rd.transcript(self.store, "nobody")

    def test_bot_without_cached_chat_returns_empty(self):
        self.assertEqual(rd.transcript(self.store, "Other"), [])

    def test_a_corrupt_or_partial_blob_is_skipped_not_fatal(self):
        acct = "sand.client.slice.account.example%7Cuser_Y"
        (Path(self.store) / blob_name(f"{acct}.transcript.replicas.zzzz")).write_text('{"value": {"ent')
        self.assertEqual([r["name"] for r in rd.roster(self.store)], ["Helper", "Other"])

    def run_cli(self, *argv):
        with mock.patch.dict(os.environ, {"GROKBOT_STORE": self.store}), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as ctx:
            rd.main(list(argv))
        return ctx.exception.code

    def test_json_output_escapes_control_and_bidi_characters(self):
        acct = "sand.client.slice.account.example%7Cuser_X"
        tr_path = Path(self.store) / blob_name(f"{acct}.transcript.replicas.aaaa1111-0000")
        tr = json.loads(tr_path.read_text())
        tr["value"]["entries"].append({"kind": "send-message", "message": {"content": "safe\u202etxt\x1b[2J"}})
        tr_path.write_text(json.dumps(tr))
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"GROKBOT_STORE": self.store}), redirect_stdout(out):
            rd.main(["show", "helper", "--json"])
        self.assertNotIn("\u202e", out.getvalue())
        self.assertNotIn("\x1b", out.getvalue())
        self.assertIn("safe", out.getvalue())

    def test_the_newest_account_slice_wins_when_several_exist(self):
        old_acct = "sand.client.slice.account.example%7Cuser_OLD"
        path = Path(self.store) / blob_name(f"{old_acct}.roster.last-roster")
        path.write_text(json.dumps({"value": {"rows": [{"id": "old-1", "name": "Stale", "updatedAt": 1}]}}))
        os.utime(path, (1, 1))
        self.assertEqual([r["name"] for r in rd.roster(self.store)], ["Helper", "Other"])

    def test_an_ambiguous_name_is_an_error_not_a_guess(self):
        acct = "sand.client.slice.account.example%7Cuser_X"
        path = Path(self.store) / blob_name(f"{acct}.roster.last-roster")
        data = json.loads(path.read_text())
        data["value"]["rows"].append({"id": "eeee5555-0000", "name": "HELPER", "updatedAt": 1})
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(LookupError, "ambiguous"):
            rd.resolve(self.store, "helper")
        self.assertEqual(rd.resolve(self.store, "eeee")["id"], "eeee5555-0000")

    def test_symlinked_or_fifo_blobs_are_ignored(self):
        acct = "sand.client.slice.account.example%7Cuser_Z"
        decoy = Path(self.tmp.name) / "decoy.json"
        decoy.write_text(json.dumps({"value": {"rows": [{"id": "zzzz", "name": "Decoy"}]}}))
        link = Path(self.store) / blob_name(f"{acct}.roster.last-roster")
        link.symlink_to(decoy)
        os.mkfifo(Path(self.store) / blob_name(f"{acct}.transcript.replicas.aaaa1111-0000"))
        self.assertEqual([r["name"] for r in rd.roster(self.store)], ["Helper", "Other"])
        self.assertEqual(len(rd.transcript(self.store, "helper")), 3)

    def test_bad_flags_are_usage_errors_not_tracebacks(self):
        for argv in (("show", "helper", "--grep"), ("show", "helper", "--last", "x"),
                     ("show", "helper", "--last", "0"), ("show", "helper", "--last", "-1")):
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cli(*argv), 2)

    def test_odd_value_types_in_the_cache_never_crash_the_reader(self):
        acct = "sand.client.slice.account.example%7Cuser_X"
        roster_path = Path(self.store) / blob_name(f"{acct}.roster.last-roster")
        data = json.loads(roster_path.read_text())
        data["value"]["rows"] += [{"id": "dddd", "name": 5, "lastEntry": "hi", "updatedAt": "nan"},
                                  {"id": 7, "name": ["x"], "updatedAt": 1e20}]
        roster_path.write_text(json.dumps(data))
        tr_path = Path(self.store) / blob_name(f"{acct}.transcript.replicas.aaaa1111-0000")
        tr = json.loads(tr_path.read_text())
        tr["value"]["entries"] += [
            {"kind": "send-message", "message": "hi", "timestampMs": "1790551920000"},
            {"kind": "event", "event": "x", "timestampMs": 1e20},
            {"kind": "message", "role": 7, "content": None},
            "not-a-dict",
        ]
        tr_path.write_text(json.dumps(tr))
        self.assertEqual(len(rd.transcript(self.store, "helper")), 6)
        for argv in (("list",), ("show", "helper"), ("show", "helper", "--json")):
            with self.subTest(argv=argv), mock.patch.dict(os.environ, {"GROKBOT_STORE": self.store}), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rd.main(list(argv))
        null_rows = {"schemaVersion": 4, "value": {"rows": None}}
        roster_path.write_text(json.dumps(null_rows))
        self.assertEqual(rd.roster(self.store), [])
        tr["value"]["entries"] = None
        tr_path.write_text(json.dumps(tr))

    def test_roster_rows_without_an_id_are_excluded(self):
        acct = "sand.client.slice.account.example%7Cuser_X"
        path = Path(self.store) / blob_name(f"{acct}.roster.last-roster")
        data = json.loads(path.read_text())
        data["value"]["rows"] += [{"name": "Ghost", "updatedAt": 5}, {"id": "", "name": "Blank"}]
        path.write_text(json.dumps(data))
        self.assertNotIn("Ghost", [r.get("name") for r in rd.roster(self.store)])
        with self.assertRaises(LookupError):
            rd.transcript(self.store, "ghost")

    def test_roster_tolerates_missing_names_and_mixed_timestamps(self):
        acct = "sand.client.slice.account.example%7Cuser_X"
        path = Path(self.store) / blob_name(f"{acct}.roster.last-roster")
        data = json.loads(path.read_text())
        data["value"]["rows"].append({"id": "cccc", "name": None, "updatedAt": "1790550000000"})
        path.write_text(json.dumps(data))
        names = [r.get("name") for r in rd.roster(self.store)]
        self.assertEqual(len(names), 3)
        with self.assertRaises(LookupError):
            rd.resolve(self.store, "nobody")


if __name__ == "__main__":
    unittest.main()
