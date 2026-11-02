"""Executable evidence for illustrative procedures, not a semantic safety oracle."""
import os
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RewriteGuardExampleTest(unittest.TestCase):
    def test_guard_binding_at_the_effect_through_both_entry_points(self):
        example = ROOT / "skills/reassert-guards-on-rewrite/examples/guarded_write.py"
        scope = runpy.run_path(str(example))
        for name in ("original", "dropped", "unsafe_move", "safe_move"):
            entry = scope[name]
            for channel in ("api", "batch"):
                with self.subTest(candidate=name, channel=channel):
                    effects = []
                    entry(channel, "tenant-a", "tenant-a", effects)
                    self.assertEqual(effects, [(channel, "tenant-a")])
                    effects = []
                    denied = False
                    try:
                        entry(channel, "tenant-a", "tenant-b", effects)
                    except PermissionError:
                        denied = True
                    # Detect the unsafe examples with the same acceptance probe.
                    binding = denied and effects == []
                    self.assertEqual(binding, name in ("original", "safe_move"))
                    if name in ("dropped", "unsafe_move"):
                        self.assertEqual(effects, [(channel, "tenant-b")])

    def test_equal_textual_counts_do_not_imply_equal_binding(self):
        example = ROOT / "skills/reassert-guards-on-rewrite/examples/guarded_write.py"
        scope = runpy.run_path(str(example))
        import inspect
        old = inspect.getsource(scope["original"])
        new = inspect.getsource(scope["unsafe_move"])
        for pattern in (r"\braise\b", r"\bif\b", r"PermissionError"):
            self.assertEqual(len(re.findall(pattern, old)), len(re.findall(pattern, new)))
        effects = []
        with self.assertRaises(PermissionError):
            scope["unsafe_move"]("api", "tenant-a", "tenant-b", effects)
        self.assertTrue(effects, "exception alone hides an unauthorized effect")


class ReviewFindingExampleTest(unittest.TestCase):
    def test_worked_findings_against_real_reviewed_current_and_final_revisions(self):
        # Read the shipped worked scenario before executing its evidence.
        worked = ROOT / "skills/apply-review-findings/references/finding-ledger-example.md"
        self.assertTrue(worked.is_file(), "standalone review scenario is missing")
        fixture = ROOT / "tests/fixtures/rewrite_review"
        with tempfile.TemporaryDirectory(prefix="orion-review-", dir="/tmp") as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            # Whitelist instead of inheriting GIT_DIR, GIT_WORK_TREE,
            # GIT_COMMON_DIR, GIT_INDEX_FILE, injected config, or credentials.
            env = {"PATH": os.environ["PATH"], "HOME": str(root),
                   "TMPDIR": str(root), "XDG_CONFIG_HOME": str(root / "config"),
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_CEILING_DIRECTORIES": str(root),
                   "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C.UTF-8"}

            def git(*args, cwd=repo, check=True):
                return subprocess.run(["git", *args], cwd=cwd, env=env,
                                      text=True, capture_output=True, check=check)

            self.assertNotEqual(git("rev-parse", "--show-toplevel", cwd=root,
                                    check=False).returncode, 0)
            git("init", "-b", "main")
            git("config", "user.name", "Synthetic Reviewer")
            git("config", "user.email", "reviewer@example.invalid")
            revisions = {}
            for name in ("reviewed", "current", "repaired"):
                shutil.copyfile(fixture / f"{name}.py", repo / "service.py")
                git("add", "--", "service.py")
                git("-c", "core.hooksPath=/dev/null", "commit", "-m", name)
                revisions[name] = git("rev-parse", "HEAD").stdout.strip()
            self.assertEqual(len(set(revisions.values())), 3)

            def load_at(name):
                scope = {}
                exec(compile(git("show", f"{revisions[name]}:service.py").stdout,
                             f"{name}:service.py", "exec"), scope)
                return scope

            old, current, final = (load_at(name) for name in revisions)
            ledger = json.loads((fixture / "findings.json").read_text())
            for finding in ledger:
                finding.update(reviewer="fixture-reviewer", reviewed_sha=revisions["reviewed"],
                               current_sha=revisions["current"], final_sha=revisions["repaired"])
            by_id = {f["id"]: f for f in ledger}
            self.assertEqual(set(by_id), {"F1", "F2", "F3", "F4", "F5", "F6", "V1"})
            self.assertEqual({f["disposition"] for f in ledger},
                             {"fix", "already-satisfied", "decline-non-defect",
                              "needs-new-vehicle", "operator/design-gated"})
            probe = re.findall(r"```python\n(.*?)\n```", worked.read_text(), re.S)[0]
            with self.assertRaisesRegex(AssertionError, "overflow accepted"):
                exec(probe, dict(current))
            exec(probe, dict(final))
            effects = []
            current["charge"](101, effects)  # F1 is still a defect at current.
            self.assertEqual(effects, [101])
            effects = []
            with self.assertRaises(ValueError):
                final["charge"](101, effects)
            self.assertEqual(effects, [])
            final["charge"](100, effects)
            self.assertEqual(effects, [100])
            self.assertIn("fetch_item", old)
            self.assertNotIn("fetch_item", current)  # F2 citation moved, not discarded.
            self.assertEqual(current["read_item"]("a", "a"), "item")
            with self.assertRaises(PermissionError):
                current["read_item"]("a", "b")
            effects = []
            old["charge"](-1, effects)  # F3 was real at the reviewed SHA.
            self.assertEqual(effects, [-1])
            for scope in (current, final):
                self.assertEqual(scope["read_item"]("a", "a"), "item")
                with self.assertRaises(PermissionError):
                    scope["read_item"]("a", "b")
                effects = []
                with self.assertRaises(ValueError):
                    scope["charge"](-1, effects)
                self.assertEqual(effects, [])
                self.assertTrue(scope["policy"]("allow"))
                with self.assertRaises(ValueError):
                    scope["policy"]("unknown")  # F4 requested fallback violates contract.
                self.assertNotIn("optional_adapter", scope)  # F5 absent target.
                self.assertEqual(scope["LIMIT"], 100)  # F6 policy unchanged.
            # There is no remote, provider or review-thread mutation to exercise.
            self.assertEqual(git("remote").stdout, "")


class StandaloneProcedureTest(unittest.TestCase):
    def errors(self, directory):
        errors = []
        for mandatory in ("SKILL.md", "PROVENANCE.md", "LICENSE.orion"):
            if not (directory / mandatory).is_file():
                errors.append(mandatory)
        for markdown in directory.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", markdown.read_text()):
                if ":" in target or target.startswith("#"):
                    continue
                path = (markdown.parent / target.split("#", 1)[0]).resolve()
                if not path.is_relative_to(directory.resolve()) or not path.is_file():
                    errors.append(target)
        return errors

    def test_one_skill_copy_closes_references_and_preserves_notice(self):
        for name in ("reassert-guards-on-rewrite", "apply-review-findings"):
            with self.subTest(skill=name), tempfile.TemporaryDirectory(
                    prefix="orion-one-skill-", dir="/tmp") as tmp:
                directory = Path(tmp) / name
                shutil.copytree(ROOT / "skills" / name, directory,
                                ignore=shutil.ignore_patterns("__pycache__"))
                self.assertEqual(self.errors(directory), [])
                self.assertEqual((directory / "LICENSE.orion").read_bytes(),
                                 (ROOT / "LICENSE").read_bytes())
                for path in directory.rglob("*"):
                    if path.is_file():
                        text = path.read_text()
                        self.assertNotRegex(text, r"/home/orion|/Users/|127\.0\.0\.1|https?://")
                if name == "reassert-guards-on-rewrite":
                    env = {"PATH": os.environ["PATH"], "HOME": tmp,
                           "TMPDIR": tmp, "XDG_CONFIG_HOME": str(Path(tmp) / "config")}
                    result = subprocess.run(["python3", "examples/guarded_write.py"],
                                            cwd=directory, env=env, text=True,
                                            capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(len(result.stdout.splitlines()), 8)
                # Negative package canaries: absent and escaping mandatory refs.
                notice = directory / "LICENSE.orion"
                notice.unlink()
                self.assertTrue(self.errors(directory))
                outside = Path(tmp) / "outside-notice"
                outside.write_text("Not bundled")
                notice.symlink_to(outside)
                self.assertTrue(self.errors(directory))


if __name__ == "__main__":
    unittest.main()
