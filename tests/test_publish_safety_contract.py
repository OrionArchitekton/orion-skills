"""Offline consumer contracts for both standalone publishing packages."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def publisher(surface):
    """Load one standalone copy, with no inherited credentials or live state."""
    names = ("common", "redactor", "cap_ledger", "x_client", "gist_client")
    saved = {n: sys.modules.get(n) for n in names}
    with tempfile.TemporaryDirectory(prefix="publish-safety-") as td:
        root = Path(td)
        rules = root / "rules.txt"
        rules.write_text("")
        env = {"HOME": td, "X_DENYLIST_FILE": str(rules),
               "X_DAILY_CAP": "5", "GIST_DAILY_CAP": "2"}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            try:
                modules = {}
                for name in names[:3] + (surface + "_client",):
                    path = ROOT / "skills" / surface / "publish-core" / (name + ".py")
                    spec = importlib.util.spec_from_file_location(name, path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[name] = module
                    spec.loader.exec_module(module)
                    modules[name] = module
                yield modules, root, rules
            finally:
                for name, previous in saved.items():
                    if previous is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = previous


class PublishSafetyContract(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO fixture requires POSIX')
    def test_special_files_refuse_before_reading(self):
        for surface in ('x', 'gist'):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                rules.unlink()
                os.mkfifo(rules)
                with patch.object(Path, 'read_text', side_effect=AssertionError('must not open FIFO')):
                    self.assertEqual(m['redactor'].decision('Public note')[0], 'ABSTAIN')

    def test_regex_lines_keep_json_looking_text_and_comments_compatible(self):
        cases = [('[123]', '2', 'unrelated'),
                 ('[true]', 't', 'xyz'),
                 ('{"x":1}', '{"x":1}', 'unrelated'),
                 ('# comment\n[123]\n\n[true]\n{"x":1}\n', '3', 'xyz')]
        for surface in ('x', 'gist'):
            for content, matching, clean in cases:
                with self.subTest(surface=surface, rules=content), publisher(surface) as (m, root, rules):
                    rules.write_text(content, encoding='utf-8')
                    self.assertEqual(m['redactor'].decision(matching)[0], 'ABSTAIN')
                    self.assertEqual([kind for kind, _ in m['redactor'].decision(matching)[1]], ['custom'])
                    self.assertEqual(m['redactor'].decision(clean), ('PUBLISH', []))
                    for text, expected in ((matching, 3), (clean, 0)):
                        candidate = root / 'candidate.txt'
                        candidate.write_text(text, encoding='utf-8')
                        with contextlib.redirect_stdout(io.StringIO()):
                            self.assertEqual(m['redactor'].main(['--check', str(candidate)]), expected)

    def test_compiler_exhaustion_is_a_nonoverridable_config_failure(self):
        for surface in ('x', 'gist'):
            for failure in (RecursionError('private rule'), MemoryError('private rule')):
                with self.subTest(surface=surface, failure=type(failure).__name__), publisher(surface) as (m, root, rules):
                    rules.write_text('SYNTHETIC_RULE')
                    client, common, caps = m[surface + '_client'], m['common'], m['cap_ledger']
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(patch.object(m['redactor'].re, 'compile', side_effect=failure))
                        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                        reserve = stack.enter_context(patch.object(caps, 'reserve'))
                        if surface == 'x':
                            stack.enter_context(patch.object(client, '_creds_from_env', return_value={n: 'fake' for n in client.CRED_NAMES}))
                            stack.enter_context(patch.object(common, 'is_armed', return_value=True))
                            send = stack.enter_context(patch.object(client, 'send'))
                            args = ['post', '--text', 'Public note', '--send']
                        else:
                            stack.enter_context(patch.object(client, 'fetch_public', return_value='Public note'))
                            stack.enter_context(patch.object(common, 'is_gist_armed', return_value=True))
                            send = stack.enter_context(patch.object(client, 'create_gist'))
                            args = ['create', '--repo', 'o/r', '--path', 'f.md', '--ack-public-hits', '--send']
                        self.assertEqual(m['redactor'].decision('Public note')[0], 'ABSTAIN')
                        self.assertEqual(client.main(args), 3)
                    reserve.assert_not_called()
                    send.assert_not_called()
                    self.assertFalse(common.CAPS_PATH.exists())

    def test_invalid_regex_abstains_without_disclosing_rule(self):
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                rules.write_text("[PRIVATE_SYNTHETIC_RULE\n")
                candidate = root / "candidate.txt"
                candidate.write_text("Harmless public note")
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    rc = m["redactor"].main(["--check", str(candidate)])
                self.assertEqual(rc, 3)
                self.assertEqual(m["redactor"].decision(candidate.read_text())[0], "ABSTAIN")
                self.assertNotIn("PRIVATE_SYNTHETIC_RULE", output.getvalue())
                self.assertIn("line 1", output.getvalue())

    def test_config_read_failures_block_check_and_preview(self):
        for surface in ("x", "gist"):
            for failure in (PermissionError("private path"), UnicodeError("private bytes"),
                            IsADirectoryError("wrong input shape")):
                with self.subTest(surface=surface, failure=type(failure).__name__), publisher(surface) as (m, root, rules):
                    with patch.object(Path, "read_text", side_effect=failure):
                        self.assertEqual(m["redactor"].decision("Public note")[0], "ABSTAIN")
                        self.assertTrue(m["redactor"].custom_load_errors())
                    output = io.StringIO()
                    with patch.object(Path, "read_text", side_effect=failure), \
                         patch.object(m["redactor"], "_read_source", return_value="Public note"), \
                         contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        self.assertEqual(m["redactor"].main(["--redact", "-"]), 3)
                    self.assertNotIn("Public note", output.getvalue())
                    self.assertNotIn("private", output.getvalue())

    def test_only_missing_default_config_is_optional(self):
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                rules.unlink()
                self.assertEqual(m["redactor"].decision("Public note")[0], "ABSTAIN")
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(m["redactor"].decision("Public note"), ("PUBLISH", []))
                rules.mkdir()
                self.assertEqual(m["redactor"].decision("Public note")[0], "ABSTAIN")

    def test_gist_ack_cannot_override_broken_protection(self):
        with publisher("gist") as (m, root, rules):
            rules.write_text("[broken\n")
            client, common = m["gist_client"], m["common"]
            with patch.object(client, "fetch_public", return_value="Already public note") as fetch, \
                 patch.object(client, "create_gist") as create, \
                 patch.object(common, "is_gist_armed", return_value=True), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = client.main(["create", "--repo", "o/r", "--path", "f.md",
                                  "--ack-public-hits", "--send"])
            self.assertEqual(rc, 3)
            fetch.assert_not_called()
            create.assert_not_called()
            self.assertFalse(common.CAPS_PATH.exists())

    def test_damaged_ledger_is_preserved_and_blocks_reservation(self):
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                common, caps = m["common"], m["cap_ledger"]
                common.ensure_state_dir()
                damaged = b"{broken"
                common.CAPS_PATH.write_bytes(damaged)
                with self.assertRaises(ValueError):
                    caps.reserve(surface)
                self.assertEqual(common.CAPS_PATH.read_bytes(), damaged)

    def test_invalid_ledger_shapes_block_every_cap_operation(self):
        invalid = ["[]", "null", "true", '{"bad-date": {"x": 1}}',
                   '{"2026-02-30": {"x": 1}}', '{"2026-W54": {"gist": 1}}',
                   '{"2026-11-02": []}', '{"2026-11-02": {"x": -1}}',
                   '{"2026-11-02": {"x": "1"}}', '{"2026-11-02": {"x": true}}',
                   '{"2026-11-02": {"x": 1.5}}', '{"2026-11-02": {"x": null}}',
                   '{"2026-11-02": {"x": 3, "x": 0}}',
                   '{"2026-11-02": {"gist": -1}}']
        for surface in ("x", "gist"):
            for damaged in invalid:
                with self.subTest(surface=surface, damaged=damaged), publisher(surface) as (m, root, rules):
                    common, caps = m["common"], m["cap_ledger"]
                    common.ensure_state_dir()
                    common.CAPS_PATH.write_text(damaged)
                    for operation in (caps.current, caps.reserve, caps.increment):
                        with self.assertRaises(ValueError):
                            operation(surface)
                        self.assertEqual(common.CAPS_PATH.read_text(), damaged)

    def test_unreadable_ledger_blocks_and_missing_state_initializes(self):
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                common, caps = m["common"], m["cap_ledger"]
                self.assertEqual(caps.current(surface), 0)
                self.assertEqual(caps.reserve(surface), 1)
                saved = common.CAPS_PATH.read_bytes()
                with patch.object(Path, "read_text", side_effect=PermissionError("private data")):
                    with self.assertRaises(ValueError):
                        caps.reserve(surface)
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(caps.main(["reserve", surface]), 5)
                self.assertEqual(common.CAPS_PATH.read_bytes(), saved)
                for _ in range(common.CAPS[surface] - 1):
                    self.assertIsNotNone(caps.reserve(surface))
                self.assertIsNone(caps.reserve(surface))
                self.assertEqual(caps.current(surface), common.CAPS[surface])

    def test_x_direct_send_checks_exact_candidate_before_reservation(self):
        with publisher("x") as (m, root, rules):
            client, common, caps = m["x_client"], m["common"], m["cap_ledger"]
            with patch.object(client, "_creds_from_env", return_value={n: "fake" for n in client.CRED_NAMES}), \
                 patch.object(common, "is_armed", return_value=True), \
                 patch.object(client, "send", return_value={"status": 201}) as send, \
                 patch.object(caps, "reserve", wraps=caps.reserve) as reserve, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                candidate = "Synthetic private endpoint 10.23.45.67"
                self.assertEqual(client.main(["post", "--text", candidate, "--send"]), 3)
                send.assert_not_called()
                reserve.assert_not_called()
                self.assertFalse(common.CAPS_PATH.exists())

    def test_x_success_reserves_once_and_preserves_exact_bytes(self):
        import json
        with publisher("x") as (m, root, rules):
            client, common, caps = m["x_client"], m["common"], m["cap_ledger"]
            candidate = "Public café note\nwith a quoted \"word\" and emoji 🙂"
            with patch.object(client, "_creds_from_env", return_value={n: "fake" for n in client.CRED_NAMES}), \
                 patch.object(common, "is_armed", return_value=True), \
                 patch.object(client, "send", return_value={"status": 201}) as send, \
                 patch.object(caps, "reserve", wraps=caps.reserve) as reserve, \
                 patch.object(m["redactor"], "decision", wraps=m["redactor"].decision) as decision, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(client.main(["post", "--text", candidate, "--send"]), 0)
            decision.assert_called_once_with(candidate)
            reserve.assert_called_once_with("x")
            self.assertEqual(json.loads(send.call_args.args[0]["body"])["text"], candidate)
            self.assertEqual(caps.current("x"), 1)

    def test_both_clients_refuse_damaged_state_and_keep_uncertain_slots(self):
        for surface in ("x", "gist"):
            for damaged in (True, False):
                with self.subTest(surface=surface, damaged=damaged), publisher(surface) as (m, root, rules):
                    client, common, caps = m[surface + "_client"], m["common"], m["cap_ledger"]
                    common.ensure_state_dir()
                    if damaged:
                        common.CAPS_PATH.write_text("{broken")
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                        if surface == "x":
                            stack.enter_context(patch.object(client, "_creds_from_env", return_value={n: "fake" for n in client.CRED_NAMES}))
                            stack.enter_context(patch.object(common, "is_armed", return_value=True))
                            send = stack.enter_context(patch.object(client, "send", side_effect=TimeoutError("uncertain")))
                            args = ["post", "--text", "Public note", "--send"]
                        else:
                            stack.enter_context(patch.object(client, "fetch_public", return_value="Public note"))
                            stack.enter_context(patch.object(common, "is_gist_armed", return_value=True))
                            send = stack.enter_context(patch.object(client, "create_gist", side_effect=TimeoutError("uncertain")))
                            args = ["create", "--repo", "o/r", "--path", "f.md", "--send"]
                        self.assertEqual(client.main(args), 5 if damaged else 1)
                    if damaged:
                        send.assert_not_called()
                        self.assertEqual(common.CAPS_PATH.read_text(), "{broken")
                    else:
                        send.assert_called_once()
                        self.assertEqual(caps.current(surface), 1)

    def test_arm_credentials_and_dry_run_still_prevent_x_sends(self):
        for armed, creds, do_send in ((False, True, True), (True, False, True), (True, True, False)):
            with self.subTest(armed=armed, creds=creds, send=do_send), publisher("x") as (m, root, rules):
                client, caps = m["x_client"], m["cap_ledger"]
                with patch.object(client, "_creds_from_env", return_value={n: "fake" if creds else "" for n in client.CRED_NAMES}), \
                     patch.object(m["common"], "is_armed", return_value=armed), \
                     patch.object(client, "send") as send, patch.object(caps, "reserve") as reserve, \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(client.main(["post", "--text", "Public note"] + (["--send"] if do_send else [])), 0)
                send.assert_not_called()
                reserve.assert_not_called()

    def test_shared_ledger_preserves_other_surfaces_and_week_buckets(self):
        import json
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                common, caps = m["common"], m["cap_ledger"]
                saved = {"2025-W01": {"custom-surface": 7}, "2025-01-01": {"gist": 2, "x": 5}}
                common.ensure_state_dir()
                common.CAPS_PATH.write_text(json.dumps(saved))
                self.assertEqual(caps.reserve(surface), 1)
                now = json.loads(common.CAPS_PATH.read_text())
                for key, value in saved.items():
                    self.assertEqual(now[key], value)

    def test_corrupt_state_cli_returns_nonzero_without_leaking_bytes(self):
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                common, caps = m["common"], m["cap_ledger"]
                common.ensure_state_dir()
                common.CAPS_PATH.write_text('{"PRIVATE_SYNTHETIC_STATE"')
                for args in (["show"], ["check", surface], ["reserve", surface]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        self.assertEqual(caps.main(args), 5)
                    self.assertNotIn("PRIVATE_SYNTHETIC_STATE", output.getvalue())

    @unittest.skipUnless(os.name == "posix", "cross-process cap contract requires POSIX flock")
    def test_concurrent_reservations_never_exceed_cap(self):
        import json
        import subprocess
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                folder = ROOT / "skills" / surface / "publish-core"
                code = ("import cap_ledger; "
                        f"print(cap_ledger.reserve({surface!r}))")
                env = {"HOME": str(root), "PATH": os.defpath,
                       "X_DAILY_CAP": "2", "GIST_DAILY_CAP": "2"}
                processes = [subprocess.Popen([sys.executable, "-c", code], cwd=folder,
                                              env=env, text=True, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE) for _ in range(8)]
                counts = []
                for process in processes:
                    out, err = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, err)
                    counts.append(out.strip())
                self.assertEqual(sorted(n for n in counts if n != "None"), ["1", "2"])
                self.assertEqual(counts.count("None"), 6)
                self.assertEqual(json.loads(m["common"].CAPS_PATH.read_text())[
                    m["common"].bucket_key(surface)][surface], 2)

    def test_valid_rules_still_match_and_clean_text_still_passes(self):
        for surface in ("x", "gist"):
            with self.subTest(surface=surface), publisher(surface) as (m, root, rules):
                rules.write_text("# comment\n\\bACME\\b\n\n")
                verdict, hits = m["redactor"].decision("Acme announcement")
                self.assertEqual(verdict, "ABSTAIN")
                self.assertEqual([kind for kind, _ in hits], ["custom"])
                self.assertEqual(m["redactor"].decision("Public note"), ("PUBLISH", []))
                self.assertEqual(m["redactor"].redact("Acme announcement"), "[REDACTED:custom] announcement")
