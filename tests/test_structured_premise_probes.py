"""Offline consumer tests; all inspected state is synthetic and isolated."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/reprobe-stale-premise'
HELPER = SKILL / 'premise_probes.py'


class PremiseProbesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='premise-probes-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'
        self.root.mkdir()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(self.home),
                    'XDG_CONFIG_HOME': str(self.home), 'TMPDIR': str(self.base),
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CEILING_DIRECTORIES': str(self.base),
                    'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'}
        self.input = self.base / 'input.json'

    def premise(self, kind='file_contains', path='config.txt', expect='enabled', id='p1'):
        probe = {'kind': kind, 'path': path}
        if kind != 'path_exists':
            probe['expect'] = expect
        return {'id': id, 'claim': 'Synthetic local premise', 'probe': probe}

    def run_document(self, document, helper=HELPER, root=None):
        self.input.write_text(json.dumps(document))
        proc = subprocess.run([sys.executable, '-B', str(helper), '--root', str(root or self.root),
                               '--input', str(self.input)], cwd=self.home, env=self.env,
                              capture_output=True, text=True, timeout=5)
        self.assertEqual(proc.stderr, '', proc.stderr)
        self.assertLessEqual(len(proc.stdout.encode()), 65536)
        return proc.returncode, json.loads(proc.stdout)

    def run_probes(self, *premises, **kwargs):
        return self.run_document({'schema_version': 1, 'premises': list(premises)}, **kwargs)

    def test_fresh_content_observation_identity_and_privacy(self):
        self.assertTrue(HELPER.is_file(), 'optional structured helper is absent on baseline')
        target = self.root / 'config.txt'
        target.write_text('private-canary enabled\n')
        code, report = self.run_probes(self.premise())
        self.assertEqual(code, 0)
        self.assertTrue(report['all_confirmed'])
        result = report['results'][0]
        self.assertEqual(result['status'], 'confirmed')
        self.assertEqual(result['premise_id'], 'p1')
        self.assertRegex(result['premise_sha256'], r'^[a-f0-9]{64}$')
        self.assertLessEqual(result['started_at'], result['finished_at'])
        self.assertEqual(result['source']['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertEqual(result['source']['inode'], target.stat().st_ino)
        rendered = json.dumps(report)
        for private in ('private-canary', 'enabled', 'config.txt', str(self.root), 'Synthetic'):
            self.assertNotIn(private, rendered)
        target.write_text('private-canary disabled\n')
        code, report = self.run_probes(self.premise())
        self.assertEqual(code, 1)
        self.assertEqual(report['results'][0]['status'], 'drifted')
        self.assertFalse(report['all_confirmed'])

    def test_supported_operations_mixed_results_and_unknown_aggregation(self):
        target = self.root / 'config.txt'
        target.write_bytes(b'enabled')
        expected = hashlib.sha256(b'enabled').hexdigest()
        cases = [self.premise('path_exists', id='exists'),
                 self.premise('file_sha256', expect=expected, id='digest'),
                 self.premise(expect='different', id='drift'),
                 self.premise(path='missing/child', id='missing'),
                 {'id': 'unknown', 'claim': 'Do not run', 'probe':
                  {'kind': 'shell', 'cmd': 'touch SHOULD_NOT_EXIST'}}]
        code, report = self.run_probes(*cases)
        self.assertEqual(code, 1)
        self.assertEqual([r['status'] for r in report['results']],
                         ['confirmed', 'confirmed', 'drifted', 'missing', 'unknown'])
        self.assertEqual(report['counts'], {'confirmed': 2, 'drifted': 1, 'missing': 1, 'unknown': 1})
        self.assertFalse(report['all_confirmed'])
        code, report = self.run_probes(cases[0], cases[-1])
        self.assertEqual(code, 1)
        self.assertFalse(report['all_confirmed'])
        self.assertEqual(report['results'][-1]['reason'], 'unsupported_operation')
        self.assertFalse((self.home / 'SHOULD_NOT_EXIST').exists())
        code, report = self.run_probes(self.premise('file_sha256', expect='0' * 64))
        self.assertEqual(report['results'][0]['status'], 'drifted')
        for kind in ('path_exists', 'file_contains', 'file_sha256'):
            code, report = self.run_probes(self.premise(kind, path='absent', expect=expected))
            self.assertEqual(report['results'][0]['status'], 'missing')

    def test_invalid_documents_and_definitions_fail_closed_without_echo(self):
        (self.root / 'config.txt').write_text('enabled')
        bad_documents = [None, [], {}, {'schema_version': True, 'premises': []},
                         {'schema_version': 1, 'premises': []},
                         {'schema_version': 2, 'premises': [self.premise()]},
                         {'schema_version': 1, 'premises': [self.premise()] * 33},
                         {'schema_version': 1, 'premises': [self.premise(), self.premise()]}]
        for doc in bad_documents:
            with self.subTest(doc=doc):
                code, report = self.run_document(doc)
                self.assertEqual(code, 1)
                self.assertFalse(report['all_confirmed'])
                self.assertEqual(report['counts']['unknown'], 1)
        invalid = [None, True, 'touch SECRET', {},
                   {**self.premise(), 'id': 'SECRET\n'},
                   {**self.premise(), 'claim': 42},
                   {**self.premise(), 'extra': 'SECRET'},
                   self.premise(expect=''), self.premise(expect=[]),
                   self.premise(expect='x' * 1025),
                   self.premise('file_sha256', expect='abc'),
                   {**self.premise(), 'probe': None},
                   {**self.premise(), 'probe': 'touch SECRET'},
                   {**self.premise(), 'probe': {'kind': 'file_contains'}},
                   {**self.premise(), 'probe': {**self.premise()['probe'], 'allow_shell': True}}]
        for premise in invalid:
            with self.subTest(premise=premise):
                code, report = self.run_probes(premise)
                self.assertEqual(code, 1)
                self.assertEqual(report['results'][0]['status'], 'unknown')
                self.assertNotIn('SECRET', json.dumps(report))

    def test_paths_special_files_and_limits_do_not_escape_or_modify(self):
        target = self.root / 'config.txt'
        target.write_text('enabled')
        before = target.stat()
        (self.root / 'directory').mkdir()
        (self.root / 'link').symlink_to(target)
        (self.root / 'parentlink').symlink_to(self.root, target_is_directory=True)
        os.mkfifo(self.root / 'fifo')
        (self.root / 'binary').write_bytes(b'\xff')
        (self.root / 'large').write_bytes(b'x' * (1048576 + 1))
        paths = ['../config.txt', str(target), './config.txt', 'a//b',
                 'link', 'parentlink/config.txt', 'directory', 'fifo', 'binary', 'large',
                 'x' * 241, '/dev/zero']
        for path in paths:
            with self.subTest(path=path):
                code, report = self.run_probes(self.premise(path=path))
                self.assertEqual(code, 1)
                self.assertEqual(report['results'][0]['status'], 'unknown')
        for root in (self.base / 'missing', self.root / 'config.txt'):
            code, report = self.run_probes(self.premise(), root=root)
            self.assertEqual(report['results'][0]['status'], 'unknown')
        rootlink = self.base / 'rootlink'
        rootlink.symlink_to(self.root, target_is_directory=True)
        code, report = self.run_probes(self.premise(), root=rootlink)
        self.assertEqual(report['results'][0]['status'], 'unknown')
        self.assertEqual(target.read_text(), 'enabled')
        self.assertEqual(target.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(target.stat().st_ctime_ns, before.st_ctime_ns)

    def load_module(self):
        spec = importlib.util.spec_from_file_location('premise_probes_test_subject', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_denied_and_changed_during_read_are_unknown_without_partial_evidence(self):
        from unittest.mock import patch
        module = self.load_module()
        target = self.root / 'config.txt'
        target.write_text('enabled')
        read = os.read
        def racing_read(fd, size):
            data = read(fd, size)
            target.write_text('changed')
            return data
        with patch.object(module.os, 'read', side_effect=racing_read):
            report = module.report({'schema_version': 1, 'premises': [self.premise()]}, str(self.root))
        self.assertEqual(report['results'][0]['reason'], 'changed_during_read')
        self.assertIsNone(report['results'][0]['source'])
        with patch.object(module.os, 'read', side_effect=PermissionError('SECRET private failure')):
            report = module.report({'schema_version': 1, 'premises': [self.premise()]}, str(self.root))
        self.assertEqual(report['results'][0]['status'], 'unknown')
        self.assertNotIn('SECRET', json.dumps(report))

    def test_manifest_errors_are_bounded_json_failures(self):
        for raw in ('{bad', '{"schema_version":1,"schema_version":1,"premises":[]}',
                    '{"schema_version":NaN,"premises":[]}', ' ' * 65537):
            self.input.write_text(raw)
            proc = subprocess.run([sys.executable, '-B', str(HELPER), '--root', str(self.root),
                                   '--input', str(self.input)], cwd=self.home, env=self.env,
                                  capture_output=True, text=True, timeout=5)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(proc.stderr, '')
            self.assertEqual(json.loads(proc.stdout)['counts']['unknown'], 1)

    def test_disappearance_and_replacement_during_read_are_unknown(self):
        from unittest.mock import patch
        module = self.load_module()
        target = self.root / 'config.txt'
        for action in ('unlink', 'replace'):
            target.write_text('enabled')
            read = os.read
            changed = False
            def racing_read(fd, size):
                nonlocal changed
                data = read(fd, size)
                if not changed:
                    changed = True
                    target.unlink()
                    if action == 'replace':
                        target.write_text('enabled')
                return data
            with patch.object(module.os, 'read', side_effect=racing_read):
                result = module.report({'schema_version': 1, 'premises': [self.premise()]},
                                       str(self.root))['results'][0]
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['reason'], 'changed_during_read')
            self.assertIsNone(result['source'])

    def test_boundary_sizes_and_no_content_read_for_exists(self):
        from unittest.mock import patch
        module = self.load_module()
        (self.root / 'config.txt').write_bytes(b'x' * 1048576)
        code, report = self.run_probes(self.premise(expect='xxx'))
        self.assertEqual(code, 0)
        with patch.object(module.os, 'read', side_effect=AssertionError('existence must not read')):
            result = module.report({'schema_version': 1, 'premises': [self.premise('path_exists')]},
                                   str(self.root))['results'][0]
        self.assertEqual(result['status'], 'confirmed')
        self.assertNotIn('sha256', result['source'])
        with patch.object(module.os, 'name', 'unsupported'):
            result = module.report({'schema_version': 1, 'premises': [self.premise()]},
                                   str(self.root))['results'][0]
        self.assertEqual(result['reason'], 'unsupported_platform')

    def test_unsupported_probes_never_inspect_sources_or_execute(self):
        from unittest.mock import patch
        module = self.load_module()
        operations = ['shell', 'bash', 'string', 'git_head', 'http', 'write', 'python']
        for operation in operations:
            premise = {'id': 'p', 'claim': 'Untrusted executable text',
                       'probe': {'kind': operation, 'path': '/dev/zero', 'cmd': 'touch CANARY'}}
            with patch.object(module, 'observe', side_effect=AssertionError('unsupported source read')):
                result = module.report({'schema_version': 1, 'premises': [premise]},
                                       str(self.root))['results'][0]
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['reason'], 'unsupported_operation')

    def test_standalone_copy_retains_helper_notice_and_usable_example(self):
        required = json.loads((ROOT / 'tests/fixtures/distribution/required-files.json').read_text())
        expected = {'SKILL.md', 'premise_probes.py', 'LICENSE.orion', 'PROVENANCE.md',
                    'docs/runbooks/structured-probes.md'}
        self.assertTrue(expected.issubset(required['reprobe-stale-premise']))
        standalone = self.base / 'standalone'
        shutil.copytree(SKILL, standalone)
        self.assertEqual((standalone / 'LICENSE.orion').read_bytes(), (ROOT / 'LICENSE').read_bytes())
        document = json.loads((ROOT / 'tests/fixtures/premise_probes/example.json').read_text())
        (self.root / 'config.txt').write_text('feature=enabled\n')
        code, report = self.run_document(document, helper=standalone / 'premise_probes.py')
        self.assertEqual(code, 0)
        self.assertEqual(report['counts']['confirmed'], 3)
        for path in standalone.rglob('*.md'):
            import re
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if ':' not in link and not link.startswith('#'):
                    resolved = (path.parent / link.split('#')[0]).resolve()
                    self.assertTrue(resolved.is_file())
                    self.assertTrue(resolved.is_relative_to(standalone))


if __name__ == '__main__':
    unittest.main()
