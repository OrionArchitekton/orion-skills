"""Offline package contracts; native CLI qualification is recorded separately."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_codex_verification_skills_contract import frontmatter_fields

ROOT = Path(__file__).resolve().parents[1]


class ClaudePluginContractTest(unittest.TestCase):
    def test_manifest_uses_the_single_default_skill_tree_without_activation(self):
        manifest = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        self.assertEqual(manifest['name'], 'orion-skills')
        self.assertEqual(manifest['version'], '0.7.1')
        self.assertEqual(set(manifest), {
            'name', 'version', 'description', 'author', 'homepage',
            'repository', 'license',
        })
        self.assertEqual(manifest['license'], 'MIT')
        for name in ('readonly', 'gist', 'ship'):
            self.assertIs(frontmatter_fields(ROOT / 'skills' / name / 'SKILL.md')
                          ['disable-model-invocation'], True)
        self.assertFalse((ROOT / '.claude-plugin/marketplace.json').exists())
        for automatic in ('hooks/hooks.json', '.mcp.json', '.lsp.json', 'settings.json'):
            self.assertFalse((ROOT / automatic).exists(), automatic)
        paths = list((ROOT / 'skills').glob('*/SKILL.md'))
        self.assertEqual(len(paths), 29)
        self.assertFalse(any(p.is_symlink() for p in (ROOT / 'skills').rglob('*')))

    def test_documented_plugin_paths_survive_relocation_and_spaces(self):
        # Execute only synthetic local operations, never publishing or delegation.
        with tempfile.TemporaryDirectory(prefix='orion-plugin-') as tmp:
            root = Path(tmp)
            plugin = root / 'cache/orion-skills/0.7.1 with spaces'
            shutil.copytree(ROOT / 'skills', plugin / 'skills',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            home = root / 'home'
            home.mkdir()
            env = {'PATH': os.environ['PATH'], 'HOME': str(home),
                   'TMPDIR': tmp, 'XDG_CONFIG_HOME': str(home / 'config'),
                   'XDG_CACHE_HOME': str(home / 'cache'),
                   'GIT_CEILING_DIRECTORIES': tmp, 'LC_ALL': 'C.UTF-8'}
            for skill, variable, relative in (
                ('readonly', 'RO', 'scripts/readonly-mode.sh'),
                ('x', 'CORE', 'publish-core/redactor.py'),
                ('gist', 'CORE', 'publish-core/redactor.py'),
                ('grokbot', 'S', 'scripts/grokbot-read'),
            ):
                with self.subTest(skill=skill):
                    text = (plugin / 'skills' / skill / 'SKILL.md').read_text()
                    assignment = re.search(r'^# Plugin: (' + variable + r'=.+)$',
                                           text, re.M)
                    self.assertIsNotNone(assignment, skill)
                    # This is a shell/path test of the documented substitution,
                    # not a claim that Python simulates native skill loading.
                    assignment = assignment[1].replace('${CLAUDE_PLUGIN_ROOT}', str(plugin))
                    suffix = relative if skill == 'readonly' else Path(relative).name
                    located = subprocess.run(
                        ['bash', '-eu', '-c', assignment + '\n' +
                         'test -f "$' + variable + '/' + suffix + '"'],
                        env=env, cwd=root, capture_output=True, text=True, timeout=15)
                    self.assertEqual(located.returncode, 0, located.stderr)
                    if skill == 'readonly':
                        for action in ('on "fixture only"', 'status', 'off', 'status'):
                            result = subprocess.run(
                                ['bash', '-eu', '-c', assignment + '\n' +
                                 '"$RO/scripts/readonly-mode.sh" ' + action],
                                env=env, cwd=root, capture_output=True, text=True, timeout=15)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertIn('OFF', result.stdout)
                    elif skill in ('x', 'gist'):
                        (home / '.claude/config').mkdir(parents=True, exist_ok=True)
                        (home / '.claude/config/x-denylist.txt').write_text('SYNTHETIC_PRIVATE_VALUE\n')
                        for value, exit_code in (('ordinary fixture', 0), ('SYNTHETIC_PRIVATE_VALUE', 3)):
                            result = subprocess.run(
                                ['bash', '-eu', '-c', assignment + '\n' +
                                 'python3 "$CORE/redactor.py" --check -'],
                                input=value, env=env, cwd=root,
                                capture_output=True, text=True, timeout=15)
                            self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
            self.assertFalse((home / '.claude/state/publishers-armed').exists())
            self.assertFalse((home / '.claude/state/gist-publishers-armed').exists())


if __name__ == '__main__':
    unittest.main()
