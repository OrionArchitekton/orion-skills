"""Exercise executable selection with local fakes; never invoke a model CLI."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'skills/delegate/scripts/delegate.py'
spec = importlib.util.spec_from_file_location('delegate_resolution', SOURCE)
delegate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delegate)


class DelegateResolutionTest(unittest.TestCase):
    def test_planted_temporary_path_entry_never_launches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'launched'
            fake = root / 'codex'
            fake.write_text('#!/bin/sh\n: > "' + str(marker) + '"\n')
            fake.chmod(0o700)
            rejected = False
            with mock.patch.dict(os.environ, {'PATH': tmp, 'HOME': tmp}, clear=True), \
                    mock.patch.object(delegate.subprocess, 'run', wraps=delegate.subprocess.run) as run:
                try:
                    delegate.dispatch('codex', 'synthetic local fixture')
                except delegate.DelegateError:
                    rejected = True
            self.assertFalse(marker.exists(), 'the planted executable ran')
            run.assert_not_called()
            self.assertTrue(rejected, 'untrusted executable must be rejected')

    def test_symlink_parent_traversal_cannot_escape_installation_tree(self):
        fixtures = Path(__file__).resolve().parent / 'fixtures/tool_evidence'
        with tempfile.TemporaryDirectory(dir=fixtures) as tmp:
            root = Path(tmp)
            install = root / 'install'
            launchers = install / 'bin'
            launchers.mkdir(parents=True)
            outside = root / 'outside'
            outside.write_text('#!/bin/sh\nexit 0\n')
            outside.chmod(0o700)
            (launchers / 'codex').symlink_to('../../outside')
            with mock.patch.object(delegate, '_installation_paths', return_value=[
                    (launchers, install, {0, os.getuid()})]), \
                    mock.patch.object(delegate.shutil, 'which', return_value=str(launchers / 'codex')), \
                    mock.patch.object(delegate.subprocess, 'run') as run:
                with self.assertRaises(delegate.DelegateError):
                    delegate.dispatch('codex', 'synthetic fixture')
                run.assert_not_called()

    def setUp(self):
        fixtures = Path(__file__).resolve().parent / 'fixtures/tool_evidence'
        self.temp = tempfile.TemporaryDirectory(dir=fixtures)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # The fake installation has a declared secure ancestry, even if this checkout
        # lives under /tmp. Keep real permissions inside the fixture so unsafe-file,
        # ancestor and symlink-hop checks still exercise the production validator.
        real_lstat = Path.lstat
        ancestors = set(self.root.parents)

        def fixture_lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if path in ancestors:
                fields = list(info)
                fields[0] &= ~0o022
                return os.stat_result(fields)
            return info

        patch = mock.patch.object(delegate.Path, 'lstat', fixture_lstat)
        patch.start()
        self.addCleanup(patch.stop)
        self.install = self.root / 'install'
        self.bin = self.install / 'bin'
        self.bin.mkdir(parents=True)
        self.cli = self.bin / 'codex'
        self.cli.write_text('#!/bin/sh\nprintf fixture-ok\n')
        self.cli.chmod(0o700)
        self.policy = mock.patch.object(delegate, '_installation_paths', return_value=[
            (self.bin, self.install, {0, os.getuid()})])
        self.policy.start()
        self.addCleanup(self.policy.stop)

    def reject(self, selection):
        with mock.patch.object(delegate.shutil, 'which', return_value=selection), \
                mock.patch.object(delegate.subprocess, 'run') as run:
            with self.assertRaises(delegate.DelegateError):
                delegate.dispatch('codex', 'synthetic fixture')
            run.assert_not_called()

    def test_missing_relative_and_arbitrary_absolute_candidates_never_launch(self):
        for candidate in (None, 'codex', './codex', 'bin/codex',
                          str(self.root / 'codex'), str(self.bin / '../bin/codex')):
            with self.subTest(candidate=candidate):
                self.reject(candidate)

    def test_current_directory_candidate_never_launches(self):
        with mock.patch.object(delegate.Path, 'cwd', return_value=self.bin):
            self.reject(str(self.cli))

    def test_world_writable_file_or_ancestor_never_launches(self):
        for path in (self.cli, self.bin, self.install):
            with self.subTest(path=path):
                original = path.stat().st_mode
                path.chmod(original | 0o020)
                try:
                    self.reject(str(self.cli))
                finally:
                    path.chmod(original)

    def test_untrusted_owner_never_launches(self):
        with mock.patch.object(delegate, '_installation_paths', return_value=[
                (self.bin, self.install, {os.getuid() + 100000})]):
            self.reject(str(self.cli))

    def test_broken_and_cyclic_links_never_launch(self):
        self.cli.unlink()
        self.cli.symlink_to('missing')
        self.reject(str(self.cli))
        self.cli.unlink()
        self.cli.symlink_to('codex')
        self.reject(str(self.cli))

    def test_symlink_traversal_through_regular_file_is_rejected(self):
        target = self.install / 'lib' / 'codex'
        target.parent.mkdir()
        self.cli.rename(target)
        (target.parent / 'not-a-directory').write_text('fixture')
        self.cli.symlink_to('../lib/not-a-directory/../codex')
        self.reject(str(self.cli))

    def test_writable_intermediate_link_cannot_hide_a_safe_final_target(self):
        target = self.install / 'lib' / 'codex'
        target.parent.mkdir()
        self.cli.rename(target)
        intermediate = self.root / 'writable'
        intermediate.mkdir(mode=0o777)
        intermediate.chmod(0o777)
        (intermediate / 'link').symlink_to(target)
        self.cli.symlink_to(intermediate / 'link')
        self.reject(str(self.cli))

    def test_nonexecutable_file_and_directory_never_launch(self):
        self.cli.chmod(0o600)
        self.reject(str(self.cli))
        self.cli.unlink()
        self.cli.mkdir()
        self.reject(str(self.cli))

    def test_checked_local_installation_executes_only_fake_cli(self):
        with mock.patch.object(delegate.shutil, 'which', return_value=str(self.cli)), \
                mock.patch.dict(os.environ, {'PATH': '/usr/bin:/bin', 'HOME': str(self.root)}, clear=True):
            result = delegate.dispatch('codex', 'synthetic fixture')
        self.assertTrue(result['ok'])
        self.assertEqual(result['output'], 'fixture-ok')
        self.assertEqual(result['argv0'], str(self.cli))

    def test_checked_symlink_preserves_command_forms_and_sandbox(self):
        target = self.install / 'lib' / 'codex'
        target.parent.mkdir()
        self.cli.rename(target)
        self.cli.symlink_to('../lib/codex')
        with mock.patch.object(delegate.shutil, 'which', return_value=str(self.cli)):
            self.assertEqual(delegate.build_argv('codex', 'task'),
                             [str(target), 'exec', '-s', 'read-only', 'task'])
            self.assertEqual(delegate.build_argv('codex', 'task', write=True, model='fixture'),
                             [str(target), 'exec', '-s', 'workspace-write', '-m', 'fixture', 'task'])
            self.assertEqual(delegate.build_argv('grok', 'task'),
                             [str(target), '-p', 'task', '--output-format', 'json'])

    def test_os_account_home_not_environment_defines_user_installation(self):
        self.policy.stop()
        with mock.patch.dict(os.environ, {'HOME': str(self.root)}, clear=True):
            paths = delegate._installation_paths()
        self.assertFalse(any(str(launcher).startswith(str(self.root)) for launcher, _, _ in paths))

    def test_known_system_executable_works_with_default_policy(self):
        self.policy.stop()
        with mock.patch.object(delegate.shutil, 'which', return_value='/usr/bin/true'):
            self.assertEqual(delegate.resolve_cli('codex'), '/usr/bin/true')

    def test_existing_environment_and_bypass_guards_remain(self):
        env = delegate.scrub_env('grok', {'HOME': str(self.root), 'XAI_API_KEY': 'fixture',
                                         'GH_TOKEN': 'fixture', 'ANTHROPIC_API_KEY': 'fixture'})
        self.assertEqual(set(env), {'HOME', 'XAI_API_KEY'})
        for flag in delegate.BYPASS_FLAGS:
            with self.subTest(flag=flag), self.assertRaises(delegate.DelegateError):
                delegate._assert_no_bypass(['fixture', flag])
