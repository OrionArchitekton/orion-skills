"""Contract tests for the 9-stage web design triad and public hygiene."""

from __future__ import annotations

import importlib.util
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BAD_DASH_RE = re.compile(r"[\u2013\u2014\u2015]")
TRIAD_SKILLS = ("orion-web-director", "orion-frontend-builder", "web-render-reviewer")


def _load_redactor():
    path = ROOT / "skills/gist/publish-core/redactor.py"
    spec = importlib.util.spec_from_file_location("orion_skills_redactor", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WebDesignTriadContractTest(unittest.TestCase):
    def test_director_stage2_has_precode_genericness_check_and_pointer(self):
        director_md = (ROOT / "skills/orion-web-director/SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(director_md, r"(?is)stage|2\.\s*\*\*creative direction\*\*")
        self.assertRegex(director_md, r"(?i)genericness|unrelated")
        self.assertIn("references/archetypes-and-tokens.md", director_md)
        self.assertRegex(director_md, r"(?i)ai[- ]slop")
        self.assertRegex(director_md, r"(?i)microcopy")

    def test_director_reference_depth_covers_calibration_rules_within_budget(self):
        ref_path = ROOT / "skills/orion-web-director/references/archetypes-and-tokens.md"
        lines = ref_path.read_text(encoding="utf-8").splitlines()
        text = "\n".join(lines)
        self.assertLessEqual(len(lines), 95, f"Expected <=95 lines, got {len(lines)}")
        self.assertFalse(BAD_DASH_RE.search(text), "Found banned long dash in archetypes-and-tokens.md")

        # 1. Explicit AI-slop default clusters
        self.assertIn("#F4F1EA", text)
        self.assertIn("#D97757", text)
        self.assertRegex(text, r"(?i)middle-dot")
        self.assertRegex(text, r"(?i)uppercase.*eyebrow|eyebrow")
        self.assertRegex(text, r"(?i)trailing arrow|->")

        # 2. True-sequence numbering rule
        self.assertRegex(text, r"01\s*/\s*02\s*/\s*03")
        self.assertRegex(text, r"(?i)chronological|ordered pipeline|real sequence")

        # 3. Unified h1 voice
        self.assertRegex(text, r"<h1>")
        self.assertRegex(text, r"(?i)italicizing|recoloring|emphasis word")

        # 4. Verb-consistent UX microcopy
        self.assertRegex(text, r"Publish.*Published")
        self.assertRegex(text, r"Save changes")
        self.assertRegex(text, r"(?i)non-apologetic")

    def test_frontend_builder_covers_react19_compiler_and_tsc_check(self):
        skill_text = (ROOT / "skills/orion-frontend-builder/SKILL.md").read_text(encoding="utf-8")
        ref_lines = (ROOT / "skills/orion-frontend-builder/references/primitives-and-assets.md").read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(ref_lines), 95, f"Expected <=95 lines, got {len(ref_lines)}")
        combined = skill_text + "\n" + "\n".join(ref_lines)
        self.assertFalse(BAD_DASH_RE.search(combined), "Found banned long dash in orion-frontend-builder")
        self.assertIn("React 19 Compiler", combined)
        self.assertIn("useMemo", combined)
        self.assertIn("useCallback", combined)
        self.assertIn("tsc --noEmit", combined)

    def test_triad_skills_pass_public_redactor_and_have_no_long_dashes(self):
        with tempfile.TemporaryDirectory() as td:
            rules = Path(td) / "rules.txt"
            rules.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": td, "X_DENYLIST_FILE": str(rules)}, clear=True):
                redactor = _load_redactor()
                for skill in TRIAD_SKILLS:
                    for md_file in sorted((ROOT / "skills" / skill).rglob("*.md")):
                        with self.subTest(file=str(md_file.relative_to(ROOT))):
                            txt = md_file.read_text(encoding="utf-8")
                            self.assertFalse(BAD_DASH_RE.search(txt), f"Long dash in {md_file}")
                            verdict, hits = redactor.decision(txt)
                            self.assertEqual(verdict, "PUBLISH", f"Redactor hits in {md_file}: {hits}")
                            self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
