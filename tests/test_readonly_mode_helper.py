"""Contract tests for readonly-mode.sh, the activation half of the rail.

The hook had a selftest from the start; the helper did not, and review found four
defects living in exactly that gap. Every one of them was a case of the helper
reporting its INTENT rather than the true post-condition:

  * `on` printed "ON" when the marker write had failed, so the operator believed
    a control was armed while the hook stayed inert.
  * `off` printed "OFF" for a marker it could not remove (rm -f cannot unlink a
    directory), so the operator believed writes were released while the hook kept
    blocking.
  * `status` reported "ON, will block" for `{"active": false}`, the one state the
    hook explicitly ALLOWS.

So these tests assert the reported state matches what the hook actually does, not
merely that a command exited 0. A false "armed" is the failure mode that matters.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO_ROOT, "skills", "readonly")
HELPER = os.path.join(SKILL_DIR, "scripts", "readonly-mode.sh")
SELFTEST = os.path.join(SKILL_DIR, "selftest.py")


def run_helper(args, marker):
    env = dict(os.environ)
    env["READONLY_MARKER"] = marker
    return subprocess.run(
        ["bash", HELPER] + args,
        capture_output=True, text=True, env=env, timeout=30,
    )


class OnReportsTruth(unittest.TestCase):
    def test_on_arms_and_marker_reads_back_active(self):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "state", "readonly.json")
            proc = run_helper(["on", "audit: unit test"], marker)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn("readonly: ON", proc.stdout)
            with open(marker) as fh:
                self.assertIs(True, json.load(fh)["active"])

    def test_on_fails_loudly_when_the_marker_cannot_be_written(self):
        # The marker path is a directory, so the write cannot succeed. The helper
        # must NOT claim the mode is armed.
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            os.mkdir(marker)
            proc = run_helper(["on", "should fail"], marker)
            self.assertNotEqual(0, proc.returncode, "on must fail when it cannot write the marker")
            self.assertNotIn("readonly: ON (", proc.stdout)
            self.assertIn("NOT armed", proc.stdout + proc.stderr)


class OffReportsTruth(unittest.TestCase):
    def test_off_clears_a_normal_marker(self):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            run_helper(["on", "x"], marker)
            proc = run_helper(["off"], marker)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn("readonly: OFF", proc.stdout)
            self.assertFalse(os.path.exists(marker))

    def test_off_does_not_claim_success_when_the_marker_survives(self):
        # rm -f cannot remove a directory, and the hook treats a directory marker
        # as deny. Reporting OFF here would be a false release.
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            os.mkdir(marker)
            proc = run_helper(["off"], marker)
            self.assertNotEqual(0, proc.returncode, "off must fail when the marker survives")
            self.assertIn("KEEPS BLOCKING", proc.stdout + proc.stderr)
            self.assertTrue(os.path.exists(marker))


class StatusMatchesHookBehavior(unittest.TestCase):
    def _status(self, content):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            with open(marker, "w") as fh:
                fh.write(content)
            return run_helper(["status"], marker)

    def test_active_true_reports_deny(self):
        proc = self._status('{"active": true}')
        self.assertIn("readonly: ON", proc.stdout)
        self.assertIn("DENY", proc.stdout)

    def test_active_false_reports_allow(self):
        # The regression: this state ALLOWS writes, so status must not say ON.
        proc = self._status('{"active": false}')
        self.assertIn("readonly: OFF", proc.stdout)
        self.assertIn("ALLOW", proc.stdout)
        self.assertNotIn("readonly: ON", proc.stdout)

    def test_unevaluable_marker_reports_fail_closed_deny(self):
        proc = self._status("{not json")
        self.assertIn("readonly: ON", proc.stdout)
        self.assertIn("DENY", proc.stdout)

    def test_absent_marker_reports_allow(self):
        with tempfile.TemporaryDirectory() as d:
            proc = run_helper(["status"], os.path.join(d, "nope.json"))
            self.assertIn("readonly: OFF", proc.stdout)
            self.assertIn("ALLOW", proc.stdout)


class SelftestCliPath(unittest.TestCase):
    def test_documented_invocation_exits_zero(self):
        # The README and SKILL.md tell a stranger to run exactly this. If only
        # run_all() is covered, the published command could rot unnoticed.
        proc = subprocess.run(
            ["python3", SELFTEST], capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("must block", proc.stdout)


if __name__ == "__main__":
    unittest.main()
