import re
import unittest

from test_codex_verification_skills_contract import (
    README,
    ROOT,
    frontmatter_fields,
    section_between,
)


SKILLS_DIR = ROOT / "skills"
SKILLS_CLI_COMMANDS = (
    "npx skills add OrionArchitekton/orion-skills --list",
    "npx skills add OrionArchitekton/orion-skills --skill ship -g -a claude-code",
)


class SkillFrontmatterContractTest(unittest.TestCase):
    """Every skill must parse under a strict YAML loader.

    Skill installers such as the `skills` CLI parse frontmatter strictly and
    silently skip a skill whose YAML is invalid, so a lenient local loader is
    not evidence the skill is discoverable.
    """

    def test_every_skill_directory_has_a_skill_file(self):
        skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
        self.assertTrue(skill_dirs, "no skill directories found")
        for skill_dir in skill_dirs:
            with self.subTest(skill=skill_dir.name):
                self.assertTrue((skill_dir / "SKILL.md").is_file())

    def test_every_skill_frontmatter_is_strict_yaml_with_name_and_description(self):
        skill_paths = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        self.assertTrue(skill_paths, "no SKILL.md files found")
        for skill_path in skill_paths:
            skill = skill_path.parent.name
            with self.subTest(skill=skill):
                fields = frontmatter_fields(skill_path)
                self.assertEqual(fields.get("name"), skill)
                description = fields.get("description")
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip())

    def test_readme_skills_cli_section_binds_verified_commands_only(self):
        text = README.read_text(encoding="utf-8")
        section = section_between(text, "### skills CLI", "### Codex CLI")

        commands = tuple(
            line.strip()
            for block in re.findall(r"```bash\n(.*?)\n```", section, flags=re.DOTALL)
            for line in block.splitlines()
            if line.strip().startswith("npx ")
        )
        self.assertEqual(commands, SKILLS_CLI_COMMANDS)

        normalized = " ".join(section.split())
        self.assertIn("DISABLE_TELEMETRY=1", normalized)
        self.assertIn("have not been validated against this library", normalized)


if __name__ == "__main__":
    unittest.main()
