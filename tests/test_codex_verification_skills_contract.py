import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CODEX_STARTER_SKILLS = (
    "reprobe-stale-premise",
    "prove-control-binds",
    "prove-deploy-is-live",
)
OPENAI_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
}
FORBIDDEN_README_CLAIMS = (
    r"\b(?:all|every|complete|full|entire|whole|wider)\b.{0,30}"
    r"\b(?:catalog|library|skills?|workflows?)\b.{0,30}"
    r"\b(?:supports?|works?|compatible|supported)\b.{0,30}\bCodex\b",
    r"\bCodex\b.{0,30}"
    r"\b(?:supports?|works?\s+with|is\s+compatible\s+with)\b.{0,30}"
    r"\b(?:all|every|complete|full|entire|whole|wider)\b.{0,30}"
    r"\b(?:catalog|library|skills?|workflows?)\b",
    r"\b(?:starter set|skills?)\b.{0,60}"
    r"\b(?:available|listed|installable)\b.{0,40}"
    r"\b(?:plugin directory|marketplace)\b",
    r"\b(?:plugin directory|marketplace)\b.{0,40}"
    r"\b(?:lists?|offers?|contains?|installs?)\b",
    r"\b(?:install|add|use)\b.{0,40}\b(?:starter set|skills?)\b"
    r".{0,40}\b(?:as|via|from)\b.{0,15}\b(?:Codex\s+)?plugin\b",
    r"\b(?:starter set|skills?)\b.{0,20}\b(?:is|are)\b"
    r".{0,15}\b(?:a\s+)?(?:Codex\s+)?plugin\b",
    r"\b(?:Codex\s+)?plugin\b.{0,40}"
    r"\b(?:contains?|includes?|installs?|provides?)\b.{0,30}"
    r"\b(?:starter set|skills?)\b",
)


def frontmatter_fields(skill_path: Path) -> dict[str, object]:
    content = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise AssertionError(f"{skill_path} has invalid frontmatter markers")

    try:
        fields = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise AssertionError(f"{skill_path} has invalid YAML frontmatter") from exc
    if not isinstance(fields, dict):
        raise AssertionError(f"{skill_path} frontmatter must be a mapping")
    return fields


def section_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index == -1:
        raise AssertionError(f"missing section marker: {start}")
    end_index = text.find(end, start_index + len(start))
    if end_index == -1:
        raise AssertionError(f"missing section marker: {end}")
    return text[start_index:end_index]


class CodexVerificationSkillsContractTest(unittest.TestCase):
    def test_starter_set_frontmatter_matches_openai_contract(self):
        for skill in CODEX_STARTER_SKILLS:
            with self.subTest(skill=skill):
                skill_path = ROOT / "skills" / skill / "SKILL.md"
                self.assertTrue(skill_path.is_file(), f"missing {skill_path}")

                fields = frontmatter_fields(skill_path)
                self.assertFalse(set(fields) - OPENAI_FRONTMATTER_FIELDS)

                name = fields.get("name")
                self.assertIsInstance(name, str)
                self.assertEqual(name, skill)
                self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertLessEqual(len(name), 64)

                description = fields.get("description")
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip())
                self.assertNotIn("<", description)
                self.assertNotIn(">", description)
                self.assertLessEqual(len(description.strip()), 1024)

    def test_starter_set_stays_portable_and_marketplace_free(self):
        forbidden_fragments = (
            "/home/orion",
            "~/.claude",
            ".claude/",
            "disable-model-invocation:",
            "allowed-tools:",
        )

        for skill in CODEX_STARTER_SKILLS:
            with self.subTest(skill=skill):
                text = (ROOT / "skills" / skill / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, text)

        plugin_manifests = sorted(
            path.relative_to(ROOT)
            for path in ROOT.rglob("plugin.json")
            if path.parent.name in {".codex-plugin", ".claude-plugin"}
        )
        marketplace_manifests = sorted(
            path.relative_to(ROOT) for path in ROOT.rglob("marketplace.json")
        )
        self.assertEqual(plugin_manifests, [])
        self.assertEqual(marketplace_manifests, [])

    def test_readme_binds_exact_codex_install_and_support_claims(self):
        text = README.read_text(encoding="utf-8")
        codex_section = section_between(text, "### Codex CLI", "\n## Skills")

        documented = set(
            re.findall(r"(?<![a-z0-9-])skills/([a-z0-9-]+)", codex_section)
        )
        self.assertEqual(documented, set(CODEX_STARTER_SKILLS))

        installer_prompts = tuple(
            block.strip()
            for block in re.findall(
                r"```text\n(.*?)\n```", codex_section, flags=re.DOTALL
            )
        )
        expected_prompts = tuple(
            "$skill-installer Install "
            "https://github.com/OrionArchitekton/orion-skills/tree/main/"
            f"skills/{skill}"
            for skill in CODEX_STARTER_SKILLS
        )
        self.assertEqual(installer_prompts, expected_prompts)

        manual_blocks = re.findall(
            r"```bash\n(.*?)\n```", codex_section, flags=re.DOTALL
        )
        self.assertEqual(len(manual_blocks), 1)
        manual_block = manual_blocks[0]
        manual_loop = re.search(r"for skill in ([a-z0-9 -]+); do", manual_block)
        self.assertIsNotNone(manual_loop)
        self.assertEqual(
            set(manual_loop.group(1).split()), set(CODEX_STARTER_SKILLS)
        )
        self.assertIn('[ -L "$destination" ]', manual_block)
        self.assertIn('cp -r "skills/$skill" "$destination"', manual_block)
        self.assertIn("continue", manual_block)
        self.assertIn(
            '[ ! -f "$HOME/.agents/skills/$skill/SKILL.md" ]', manual_block
        )
        self.assertIn("exit 1", manual_block)

        normalized_readme = " ".join(text.split())
        normalized_section = " ".join(codex_section.split())
        self.assertIn(
            "a narrowly validated starter set also supports [Codex CLI]",
            normalized_readme,
        )
        self.assertIn("not a plugin-directory listing", normalized_section)
        self.assertIn(
            "The wider library has not yet been validated as a Codex set.",
            normalized_readme,
        )
        for pattern in FORBIDDEN_README_CLAIMS:
            self.assertIsNone(
                re.search(pattern, normalized_readme, flags=re.IGNORECASE)
            )

        for skill in CODEX_STARTER_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(f"${skill}", codex_section)

    def test_claim_guard_rejects_common_codex_and_plugin_overclaims(self):
        overclaims = (
            "Every workflow in this library works in Codex.",
            "The starter set is available from the Codex marketplace.",
            "Codex supports the complete catalog.",
            "Install the starter set as a Codex plugin.",
        )
        for claim in overclaims:
            with self.subTest(claim=claim):
                self.assertTrue(
                    any(
                        re.search(pattern, claim, flags=re.IGNORECASE)
                        for pattern in FORBIDDEN_README_CLAIMS
                    )
                )

    def test_manual_fallback_preserves_existing_and_fails_on_dangling_link(self):
        text = README.read_text(encoding="utf-8")
        codex_section = section_between(text, "### Codex CLI", "\n## Skills")
        manual_blocks = re.findall(
            r"```bash\n(.*?)\n```", codex_section, flags=re.DOTALL
        )
        self.assertEqual(len(manual_blocks), 1)
        manual_block = manual_blocks[0]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)
            env = os.environ.copy()
            env["HOME"] = str(temp_home)

            first = subprocess.run(
                ["bash", "-c", manual_block],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)

            installed_root = temp_home / ".agents" / "skills"
            for skill in CODEX_STARTER_SKILLS:
                self.assertTrue((installed_root / skill / "SKILL.md").is_file())

            sentinel = installed_root / CODEX_STARTER_SKILLS[0] / "sentinel"
            sentinel.write_text("preserve me", encoding="utf-8")
            retry = subprocess.run(
                ["bash", "-c", manual_block],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(retry.returncode, 0, retry.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me")

            broken_skill = installed_root / CODEX_STARTER_SKILLS[-1]
            shutil.rmtree(broken_skill)
            broken_skill.symlink_to(
                temp_home / "missing-skill", target_is_directory=True
            )
            broken = subprocess.run(
                ["bash", "-c", manual_block],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn("incomplete skill installation", broken.stderr)
