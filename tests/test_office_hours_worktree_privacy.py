"""Execute the published privacy recipes in disposable, isolated Git repositories.

Use unittest so the repository's CI entrypoint exercises these consumer recipes
as well as the pytest entrypoint declared in AGENTS.md.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/office-hours/SKILL.md"


def run(argv, cwd, env, check=True):
    return subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True,
                          check=check, timeout=10)


def recipe():
    section = SKILL.read_text().split("### Builder Profile Append", 1)[1]
    block = re.search(r"```bash\n(.*?)\n```", section, re.S).group(1)
    return block.replace("<SKILL_DIR>", str(SKILL.parent))


def append_profile(repo, env):
    # A consumer write immediately after the recipe must never happen on failure.
    return run(["bash", "--noprofile", "--norc", "-c", recipe() +
                "\nprintf '%s\\n' '{\"synthetic\":true}' >> \"$STATE_ROOT/builder-profile.jsonl\""],
               repo, env, check=False)


class OfficeHoursWorktreePrivacyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="office hours privacy ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        home = self.root / "home"
        home.mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(home),
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_COUNT": "0"}

    def repository(self, name="ordinary repo with spaces"):
        repo = self.root / name
        repo.mkdir()
        run(["git", "init", "--template=", str(repo)], self.root, self.env)
        # Plumbing creates the fixture baseline without installed commit hooks.
        tree = run(["git", "mktree"], repo, self.env).stdout.strip()
        identity = {**self.env, "GIT_AUTHOR_NAME": "Fixture", "GIT_COMMITTER_NAME": "Fixture",
                    "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
        commit = subprocess.run(["git", "commit-tree", tree], input="fixture\n", cwd=repo,
                                env=identity, text=True, capture_output=True, check=True,
                                timeout=10).stdout.strip()
        run(["git", "update-ref", "HEAD", commit], repo, self.env)
        (repo / ".git/info").mkdir(exist_ok=True)
        return repo

    def test_profile_is_ignored_before_first_write_in_both_worktree_types(self):
        for linked in (False, True):
            with self.subTest(linked=linked):
                ordinary = self.repository(f"ordinary repo {linked}")
                exclude = ordinary / ".git/info/exclude"
                exclude.write_text("# unrelated rule\nkeep-me\n")
                repo = ordinary
                if linked:
                    repo = self.root / "linked repo with spaces"
                    run(["git", "worktree", "add", "--detach", str(repo)], ordinary, self.env)
                result = append_profile(repo, self.env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((repo / ".office-hours/builder-profile.jsonl").is_file())
                self.assertEqual(run(["git", "check-ignore", "-q", ".office-hours/builder-profile.jsonl"], repo, self.env, False).returncode, 0)
                self.assertEqual(run(["git", "status", "--porcelain", "--untracked-files=all"], repo, self.env).stdout, "")
                self.assertTrue(exclude.read_text().startswith("# unrelated rule\nkeep-me\n"))

    def test_failed_protection_leaves_no_new_profile(self):
        for failure in ("exclusion-directory", "override", "tracked", "state-symlink", "profile-symlink", "analytics-symlink"):
            with self.subTest(failure=failure):
                repo = self.repository(failure)
                exclude = repo / ".git/info/exclude"
                profile = repo / ".office-hours/builder-profile.jsonl"
                outside = self.root / (failure + " outside")
                outside.mkdir()
                if failure == "exclusion-directory":
                    exclude.mkdir()
                elif failure == "override":
                    (repo / ".gitignore").write_text("!.office-hours/\n!.office-hours/builder-profile.jsonl\n")
                elif failure == "tracked":
                    profile.parent.mkdir()
                    profile.write_text("existing synthetic state\n")
                    run(["git", "add", ".office-hours/builder-profile.jsonl"], repo, self.env)
                elif failure == "state-symlink":
                    profile.parent.symlink_to(outside, target_is_directory=True)
                else:
                    profile.parent.mkdir()
                    if failure == "profile-symlink":
                        profile.symlink_to(outside / "leaked-profile")
                    else:
                        (profile.parent / "analytics").symlink_to(outside, target_is_directory=True)
                before = profile.read_bytes() if profile.is_file() else None
                result = append_profile(repo, self.env)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(profile.read_bytes() if profile.is_file() else None, before)
                self.assertEqual(list(outside.iterdir()), [])

    def test_repeated_recipe_preserves_unterminated_rule_and_works_from_subdirectory(self):
        repo = self.repository()
        exclude = repo / ".git/info/exclude"
        exclude.write_text("keep-me")
        subdir = repo / "a nested directory"
        subdir.mkdir()
        for _ in range(2):
            result = append_profile(subdir, self.env)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(exclude.read_text().splitlines().count("/.office-hours/"), 1)
        self.assertEqual(run(["git", "check-ignore", "-q", "keep-me"], repo, self.env, False).returncode, 0)
        self.assertEqual(len((repo / ".office-hours/builder-profile.jsonl").read_text().splitlines()), 2)

    def test_outside_git_leaves_no_profile(self):
        home = Path(self.env["HOME"])
        result = append_profile(home, self.env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((home / ".office-hours").exists())

    def test_analytics_recipe_also_stops_when_exclusion_fails(self):
        repo = self.repository()
        (repo / ".git/info/exclude").mkdir()
        text = (SKILL.parent / "references/details.md").read_text()
        block = next(b for b in re.findall(r"```bash\n(.*?)\n```", text, re.S) if "ANALYTICS_DIR=" in b)
        result = run(["bash", "--noprofile", "--norc", "-c", block.replace("<SKILL_DIR>", str(SKILL.parent))], repo, self.env, False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((repo / ".office-hours/analytics/skill-usage.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
