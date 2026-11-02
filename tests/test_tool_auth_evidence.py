"""Offline evidence checks for the router's illustrative auth detectors."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'skills/tools-router/reference-recon.py'
spec = importlib.util.spec_from_file_location('tool_auth_recon', SOURCE)
recon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recon)


class ToolAuthEvidenceTest(unittest.TestCase):
    def test_dummy_environment_is_configuration_only(self):
        with mock.patch.dict(os.environ, {'MODEL_API_KEY': 'synthetic-value'}, clear=True):
            self.assertEqual(recon.authed_env('MODEL_API_KEY'), 'config_present')
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(recon.authed_env('MODEL_API_KEY'), 'indeterminate')

    def test_failed_probe_with_active_marker_cannot_authenticate(self):
        self.assertEqual(recon.authed_if_active_marker(1, '* stale-account'), 'unauthed')

    def test_marker_without_account_on_same_line_is_unverified(self):
        self.assertEqual(recon.authed_if_active_marker(0, '*\nnot-an-account-row'), 'indeterminate')

    def test_zero_exit_with_unknown_output_is_not_authenticated(self):
        for name in ('gh', 'cloudcli', 'vendorcli'):
            with self.subTest(name=name):
                state, output = recon.probe_cli(name, runner=lambda *_: (0, 'unexpected response'))
                self.assertEqual(state, 'indeterminate')
                self.assertEqual(output, '')

    def test_mocked_success_requires_each_tools_positive_signal(self):
        outputs = {'gh': '  ✓ Logged in to github.com account fixture-user (fixture)\n',
                   'cloudcli': '* fixture-account\n', 'vendorcli': '{"login":"fixture-user"}'}
        for name, output in outputs.items():
            with self.subTest(name=name):
                self.assertEqual(recon.probe_cli(name, runner=lambda *_: (0, output)), ('authed', ''))
                self.assertEqual(recon.probe_cli(name, runner=lambda *_: (1, output)), ('unauthed', ''))

    def test_missing_executables_are_not_probed(self):
        runner = mock.Mock(side_effect=AssertionError('a provider was invoked'))
        with mock.patch.object(recon.shutil, 'which', return_value=None), \
                mock.patch.dict(os.environ, {}, clear=True):
            clis, _, _ = recon.build_inventory('', runner=runner)
        runner.assert_not_called()
        for name in recon.PROBES:
            self.assertEqual(clis[name]['state'], 'not_installed')

    def test_unknown_identity_shapes_and_empty_environment_are_unverified(self):
        for output in ('', 'null', '[]', '{}', '{"login":false}', '{"login":" "}'):
            with self.subTest(output=output):
                self.assertEqual(recon.authed_if_identity(0, output), 'indeterminate')
        with mock.patch.dict(os.environ, {'MODEL_API_KEY': ''}, clear=True):
            self.assertEqual(recon.authed_env('MODEL_API_KEY'), 'indeterminate')

    def test_run_captures_stderr_without_returning_raw_probe_text(self):
        proc = mock.Mock(returncode=0, stdout='✓ Logged in to github.com account fixture-user')
        with mock.patch.object(recon.subprocess, 'run', return_value=proc) as run:
            self.assertEqual(recon.probe_cli('gh', runner=recon._run), ('authed', ''))
        self.assertEqual(run.call_args.kwargs['stderr'], recon.subprocess.STDOUT)

    def test_configured_key_cannot_justify_disabling_mcp(self):
        clis = {'paycli': {'state': 'config_present'}}
        recs = recon.dedup(clis, [{'id': 'payments', 'status': 'failed'}])
        self.assertEqual(recs[0]['action'], 'flag_surface')

    def test_probe_errors_never_authenticate_and_raw_secrets_do_not_render(self):
        for error in (FileNotFoundError(), recon.subprocess.TimeoutExpired('fixture', 12)):
            with self.subTest(error=type(error).__name__), \
                    mock.patch.object(recon.subprocess, 'run', side_effect=error):
                self.assertNotEqual(recon.probe_cli('gh', runner=recon._run)[0], 'authed')
        secret = 'MODEL_API_KEY=synthetic-private-value'
        state, raw = recon.probe_cli('vendorcli', runner=lambda *_: (0, secret))
        table = recon.render_table({'vendorcli': {'state': state}}, [], [])
        self.assertEqual(raw, '')
        self.assertNotIn(secret, table)
