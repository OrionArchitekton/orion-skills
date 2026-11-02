"""Exercise the published handoff write recipe, not a parallel implementation.

Reader decisions about stale evidence and authority are worked scenarios in
fixtures/workflow_portability/handoff-scenarios.md, not an automatic selector.
"""
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/pre-compact/SKILL.md"


class HandoffTaskIdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="handoff recipe ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".claude/handoffs/packs").mkdir(parents=True)
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.root),
                    "HANDOFF_ROOT": str(self.root / "durable handoffs"), "REPO_ID": "example/project"}

    def write(self, task, body_task=None):
        body = self.root / "body.md"
        body.write_text(f"Task: {body_task or task}\nRepository: example/project\nOwner: fixture\n"
                        "Accepted baseline: unknown\nLast verified outcome: synthetic fixture only\n"
                        "Unfinished step: review\nNext action: inspect fixture\nRemaining authority: no publication\n")
        section = SKILL.read_text().split("**4. Write the pack.**", 1)[1]
        recipe = re.search(r"```bash\n(.*?)\n```", section, re.S).group(1)
        # Support running the historical recipe for a RED regression observation.
        recipe = recipe.replace("/tmp/pack-body.md", shlex.quote(str(body))).replace("<slug>", task)
        result = subprocess.run(["bash", "--noprofile", "--norc", "-c", recipe],
                                env={**self.env, "TASK_ID": task, "PACK_BODY": str(body)},
                                text=True, capture_output=True)
        return result, body.read_bytes()

    def test_two_tasks_and_repeated_checkpoints_preserve_every_pack(self):
        packs = []
        for task in ("project-task-a", "project-task-b", "project-task-a"):
            result, body = self.write(task)
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = list((Path(self.env["HANDOFF_ROOT"]) / "tasks" / task / "packs").glob("*.md"))
            new = [p for p in paths if p not in [p for p, _ in packs]]
            self.assertEqual(len(new), 1, result.stdout)
            self.assertIn(str(new[0]), result.stdout)
            packs.append((new[0], body))
            for path, original in packs:
                self.assertEqual(path.read_bytes(), original)
        self.assertFalse((Path(self.env["HANDOFF_ROOT"]) / "LATEST.md").exists())

    def test_invalid_task_id_creates_no_pack(self):
        result, _ = self.write("../other-task")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list(self.root.rglob("packs/*.md")))

    def test_mismatched_body_creates_no_pack(self):
        result, _ = self.write("project-task-a", body_task="project-task-b")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list(self.root.rglob("packs/*.md")))


if __name__ == "__main__":
    unittest.main()
