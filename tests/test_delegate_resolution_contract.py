"""Executable fixtures only: no installed model CLI or provider is invoked."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'skills/delegate/scripts/delegate.py'
spec = importlib.util.spec_from_file_location('delegate_resolution', SOURCE)
delegate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delegate)


@unittest.skipUnless(os.name == 'posix', 'process fixtures require a POSIX host')
class DelegateResolutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='delegate-fixtures-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        (self.workspace / '.git').mkdir()
        self.install = self.root / 'external'
        self.install.mkdir()
        self.marker = self.root / 'marker'
        old_cwd = Path.cwd()
        os.chdir(self.workspace)
        self.addCleanup(os.chdir, old_cwd)
        env = mock.patch.dict(os.environ, {
            'PATH': str(self.install), 'HOME': str(self.root / 'home'),
            'LANG': 'C.UTF-8',
        }, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def fixture(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # Absolute interpreter; records only harmless fixture argv/stdin/env.
        path.write_text('#!/usr/bin/python3\nimport json,os,sys\n'
                        'from pathlib import Path\n'
                        f'Path({str(self.marker)!r}).write_text(json.dumps(dict('
                        'argv=sys.argv, env=dict(os.environ), stdin=sys.stdin.read())))\n'
                        'print("fixture-ok")\n')
        path.chmod(0o755)
        return path

    def deny(self):
        with mock.patch.object(delegate.subprocess, 'run', wraps=subprocess.run) as run:
            with self.assertRaises(delegate.DelegateError):
                delegate.dispatch('codex', 'harmless fixture')
            run.assert_not_called()
        self.assertFalse(self.marker.exists())

    def test_workspace_first_hit_denied_with_disabled_check_canary(self):
        planted = self.fixture(self.workspace / 'codex')
        self.fixture(self.install / 'codex')
        os.environ['PATH'] = str(self.workspace) + os.pathsep + str(self.install)
        # Control-disabled baseline: precisely the released selection executes
        # the harmless workspace fixture. No model CLI can be selected here.
        with mock.patch.object(delegate, 'resolve_cli', return_value=str(planted)):
            argv = delegate.build_argv('codex', 'harmless fixture')
        subprocess.run(argv, env=delegate.scrub_env('codex'),
                       stdin=subprocess.DEVNULL, capture_output=True, check=True)
        self.assertTrue(self.marker.exists())
        self.marker.unlink()
        self.deny()

    def test_external_link_via_workspace_then_back_out_is_denied(self):
        target = self.fixture(self.install / 'target')
        (self.workspace / 'bounce').symlink_to(target)
        (self.install / 'codex').symlink_to(self.workspace / 'bounce')
        self.deny()

    def test_symlink_ancestor_with_parent_traversal_keeps_kernel_meaning(self):
        # external/alias/../codex walks through workspace/deep before `..`.
        # abspath/normpath would incorrectly collapse it to external/codex.
        deep = self.workspace / 'deep'
        deep.mkdir()
        (self.install / 'alias').symlink_to(deep, target_is_directory=True)
        self.fixture(self.workspace / 'codex')
        selection = str(self.install / 'alias' / '..' / 'codex')
        with mock.patch.object(delegate.shutil, 'which', return_value=selection):
            self.deny()

    def test_replacement_after_argv_construction_is_denied(self):
        launcher = self.fixture(self.install / 'codex')
        planted = self.fixture(self.workspace / 'payload')
        original_scrub = delegate.scrub_env

        def replace_before_spawn(target):
            launcher.unlink()
            launcher.symlink_to(planted)
            return original_scrub(target)

        with mock.patch.object(delegate, 'scrub_env', side_effect=replace_before_spawn):
            self.deny()

    def test_relative_empty_and_workspace_subdirectory_selections_deny(self):
        for entry in ('', '.', 'bin', str(self.workspace / 'bin')):
            with self.subTest(entry=entry):
                self.fixture(self.workspace / 'codex')
                self.fixture(self.workspace / 'bin/codex')
                os.environ['PATH'] = entry + os.pathsep + str(self.install)
                self.deny()

    def test_relative_selection_pointing_outside_is_explicitly_denied(self):
        self.fixture(self.install / 'codex')
        os.environ['PATH'] = '../external'
        self.deny()

    def test_symlink_into_workspace_is_denied(self):
        planted = self.fixture(self.workspace / 'codex')
        (self.install / 'codex').symlink_to(planted)
        self.deny()

    def test_parent_directory_symlink_into_workspace_is_denied(self):
        self.fixture(self.workspace / 'bin/codex')
        (self.install / 'alias').symlink_to(self.workspace / 'bin')
        os.environ['PATH'] = str(self.install / 'alias')
        self.deny()

    def test_nested_cwd_uses_enclosing_git_worktree_marker(self):
        (self.workspace / '.git').rmdir()
        (self.workspace / '.git').write_text('gitdir: fixture-metadata')
        nested = self.workspace / 'src/deep'
        nested.mkdir(parents=True)
        os.chdir(nested)
        self.fixture(self.workspace / 'bin/codex')
        os.environ['PATH'] = str(self.workspace / 'bin')
        self.deny()

    def test_non_git_workspace_uses_current_directory(self):
        # Model no enclosing marker without discovering a shared /tmp/.git.
        nongit = self.root / 'nongit'
        nongit.mkdir()
        os.chdir(nongit)
        self.fixture(nongit / 'codex')
        os.environ['PATH'] = str(nongit)
        with mock.patch.object(Path, 'exists', return_value=False):
            self.deny()

    def test_missing_broken_cyclic_nonexecutable_and_directory_deny(self):
        for kind in ('missing', 'broken', 'cycle', 'mode', 'directory'):
            with self.subTest(kind=kind):
                launcher = self.install / 'codex'
                if launcher.is_symlink() or launcher.is_file():
                    launcher.unlink()
                if launcher.is_dir():
                    launcher.rmdir()
                if kind == 'broken':
                    launcher.symlink_to('missing')
                elif kind == 'cycle':
                    launcher.symlink_to('codex')
                elif kind == 'mode':
                    self.fixture(launcher).chmod(0o644)
                elif kind == 'directory':
                    launcher.mkdir()
                # Exercise validation even where shutil.which would omit it.
                with mock.patch.object(delegate.shutil, 'which', return_value=str(launcher)):
                    self.deny()
        with mock.patch.object(delegate.shutil, 'which', return_value=None):
            self.deny()

    def test_outside_install_matrix_executes_selected_launcher(self):
        layouts = ('usr/bin', 'usr/local/bin', 'home/.local/bin', 'custom prefix/bin',
                   'home/.nvm/versions/node/v24/bin', 'home/.volta/bin',
                   'home/.asdf/shims', 'home/.local/share/mise/shims')
        for layout in layouts:
            for style in ('file', 'link', 'shim'):
                with self.subTest(layout=layout, style=style):
                    directory = self.install / layout / style
                    launcher = directory / 'codex'
                    target = self.fixture(directory / 'implementation')
                    if style == 'link':
                        launcher.symlink_to(target.name)
                    elif style == 'shim':
                        launcher.write_text('#!/bin/sh\nexec "' + str(target) + '" "$@"\n')
                        launcher.chmod(0o755)
                    else:
                        self.fixture(launcher)
                    os.environ['PATH'] = str(directory)
                    result = delegate.dispatch('codex', 'harmless fixture')
                    self.assertTrue(result['ok'])
                    self.assertEqual(result['argv0'], str(launcher))
                    recorded = json.loads(self.marker.read_text())
                    if style != 'shim':
                        self.assertEqual(recorded['argv'][0], str(launcher))
                    self.assertEqual(recorded['argv'][1:], ['exec', '-s', 'read-only', 'harmless fixture'])
                    self.assertEqual(recorded['stdin'], '')
                    self.marker.unlink()

    def test_group_writable_custom_install_is_not_silently_removed(self):
        self.fixture(self.install / 'codex').chmod(0o775)
        self.install.chmod(0o775)
        self.assertTrue(delegate.dispatch('codex', 'harmless fixture')['ok'])

    def test_multicall_symlink_preserves_name_and_link_traversal(self):
        target = self.install / 'lib/multicall'
        target.parent.mkdir()
        target.write_text('#!/bin/sh\ncase "$0" in */codex) printf codex-fixture;; *) exit 9;; esac\n')
        target.chmod(0o755)
        (self.install / 'codex').symlink_to(target)
        result = delegate.dispatch('codex', 'harmless fixture')
        self.assertTrue(result['ok'])
        self.assertEqual(result['output'], 'codex-fixture')
        self.assertEqual(result['argv0'], str(self.install / 'codex'))

    def test_outside_link_parent_traversal_preserves_kernel_meaning(self):
        actual = self.install / 'tree/deep'
        actual.mkdir(parents=True)
        (self.install / 'alias').symlink_to(actual)
        launcher = self.fixture(actual.parent / 'codex')
        selected = str(self.install / 'alias' / '..' / 'codex')
        os.environ['PATH'] = str(self.install / 'alias' / '..')
        result = delegate.dispatch('codex', 'harmless fixture')
        self.assertTrue(result['ok'])
        self.assertEqual(result['argv0'], selected)
        self.assertEqual(json.loads(self.marker.read_text())['argv'][0], selected)

    def test_environment_and_provider_controls_are_preserved(self):
        self.fixture(self.install / 'codex')
        self.fixture(self.install / 'grok')
        os.environ.update(XAI_API_KEY='fixture-xai', OPENAI_API_KEY='fixture-openai',
                          ANTHROPIC_API_KEY='fixture-anthropic', GH_TOKEN='fixture-gh',
                          OLLAMA_HOST='http://fixture.invalid')
        codex = delegate.dispatch('codex', 'two words', write=True, model='fixture-model')
        self.assertTrue(codex['ok'])
        data = json.loads(self.marker.read_text())
        self.assertEqual(data['argv'][1:], ['exec', '-s', 'workspace-write', '-m', 'fixture-model', 'two words'])
        self.assertEqual(set(data['env']), {'PATH', 'HOME', 'LANG'})
        grok = delegate.dispatch('grok', 'two words')
        self.assertTrue(grok['ok'])
        data = json.loads(self.marker.read_text())
        self.assertEqual(data['argv'][1:], ['-p', 'two words', '--output-format', 'json'])
        self.assertEqual(data['env']['XAI_API_KEY'], 'fixture-xai')
        for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GH_TOKEN', 'OLLAMA_HOST'):
            self.assertNotIn(key, data['env'])
        for flag in (*delegate.BYPASS_FLAGS, '--dangerous-fixture'):
            with self.subTest(flag=flag), self.assertRaises(delegate.DelegateError):
                delegate.build_argv('codex', flag)
        with self.assertRaises(delegate.DelegateError):
            delegate.build_argv('unknown', 'fixture')
        with self.assertRaises(delegate.DelegateError):
            delegate.build_argv('codex', ' ')

    def test_pending_and_timeout_contracts_are_preserved(self):
        self.fixture(self.install / 'codex')
        with mock.patch.object(delegate.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', 1)):
            result = delegate.dispatch('codex', 'harmless fixture', timeout=1)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'timeout after 1s')
        os.environ['PATH'] = str(self.workspace)
        self.fixture(self.workspace / 'codex')
        result = delegate.fanout([dict(target='codex', task='harmless fixture')])
        self.assertEqual(result[0]['state'], 'pending')
        self.assertFalse(self.marker.exists())

    def test_gemma_lane_never_resolves_cli(self):
        with mock.patch.object(delegate, 'resolve_cli', side_effect=AssertionError('no CLI')), \
                mock.patch.object(delegate, '_dispatch_gemma', return_value={'ok': True}) as http:
            self.assertEqual(delegate.dispatch('gemma', 'fixture'), {'ok': True})
            http.assert_called_once_with('fixture', model=None, timeout=180)

    def test_filesystem_identity_alias_of_workspace_is_denied(self):
        # Simulate a case/volume alias on a filesystem where the spellings
        # compare differently but refer to the same workspace directory.
        alias = self.install / 'case-alias'
        self.fixture(alias / 'codex')
        os.environ['PATH'] = str(alias)
        real_samefile = Path.samefile

        def identity(path, other):
            return path == alias or real_samefile(path, other)

        with mock.patch.object(Path, 'samefile', identity):
            self.deny()

    def test_junction_branch_checks_intermediate_workspace_target(self):
        # Structural simulation only: this Linux symlink stands in for a
        # Windows junction/reparse link; it does not qualify native Windows.
        target = self.fixture(self.install / 'target')
        (self.workspace / 'bounce').symlink_to(target)
        selected = self.install / 'codex'
        selected.symlink_to(self.workspace / 'bounce')
        real_is_symlink = Path.is_symlink
        with mock.patch.object(delegate.stat, 'S_ISLNK', return_value=False), \
                mock.patch.object(Path, 'is_junction', real_is_symlink, create=True):
            self.deny()


if __name__ == '__main__':
    unittest.main()
