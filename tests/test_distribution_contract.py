"""Offline catalog and mandatory-file checks, also usable on extracted archives."""
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def distribution_errors(root, required):
    errors = []
    skills = root / 'skills'
    actual = {p.name for p in skills.iterdir() if p.is_dir()}
    if not actual or actual != set(required):
        errors.append('source catalog differs from the retained package contract')
    text = (root / 'README.md').read_text(encoding='utf-8')
    rows = re.findall(r'\|\s*\[`([a-z0-9-]+)`\]\(skills/([a-z0-9-]+)/SKILL\.md\)', text)
    names = [name for name, _ in rows]
    examples = re.findall(r'(?m)^-\s*\*\*`([a-z0-9-]+)`\*\*', text)
    if (set(names) != actual or len(names) != len(actual)
            or any(name != target for name, target in rows)):
        errors.append('README table differs from source IDs')
    if set(examples) != actual or len(examples) != len(actual):
        errors.append('README worked examples differ from source IDs')
    for name, files in required.items():
        directory = skills / name
        for relative in files:
            path = directory / relative
            if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
                errors.append(f'missing or escaping mandatory file: {name}/{relative}')
        for markdown in directory.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', markdown.read_text(encoding='utf-8')):
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                path = markdown.parent / target.split('#', 1)[0]
                if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
                    errors.append(f'missing or escaping standalone reference: {name}/{target}')
    return errors


class DistributionContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / 'skills/example'
        self.skill.mkdir(parents=True)
        (self.skill / 'SKILL.md').write_text('---\nname: example\n---\n[Guide](guide.md)\n')
        (self.skill / 'guide.md').write_text('Public guide\n')
        self.readme = '| [`example`](skills/example/SKILL.md) | Example |\n- **`example`**: Example.\n'
        (self.root / 'README.md').write_text(self.readme)
        self.required = {'example': ['SKILL.md', 'guide.md']}

    def test_catalog_guard_accepts_complete_input_and_rejects_drift(self):
        self.assertEqual(distribution_errors(self.root, self.required), [])
        for text in ('', self.readme + self.readme,
                     self.readme.replace('skills/example/', 'skills/wrong/')):
            with self.subTest(readme=text):
                (self.root / 'README.md').write_text(text)
                self.assertTrue(distribution_errors(self.root, self.required))

    def test_missing_and_escaping_mandatory_references_block(self):
        guide = self.skill / 'guide.md'
        guide.unlink()
        self.assertTrue(distribution_errors(self.root, self.required))
        outside = self.root / 'outside.md'
        outside.write_text('Not part of this standalone skill\n')
        guide.symlink_to(outside)
        self.assertTrue(distribution_errors(self.root, self.required))
        guide.unlink()
        guide.write_text('Public guide\n')
        (self.skill / 'SKILL.md').write_text('[Unbundled](missing.md)\n')
        self.assertTrue(distribution_errors(self.root, self.required))

    def test_retained_collection_is_complete(self):
        required = json.loads((ROOT / 'tests/fixtures/distribution/required-files.json').read_text())
        self.assertEqual(distribution_errors(ROOT, required), [])
