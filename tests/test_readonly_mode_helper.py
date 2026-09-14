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
        # must NOT claim the mode is armed, and because the hook fail-closes on a
        # directory marker it must report that file edits are being denied rather
        # than claim the mode is off.
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            os.mkdir(marker)
            proc = run_helper(["on", "should fail"], marker)
            self.assertNotEqual(0, proc.returncode, "on must fail when it cannot write the marker")
            self.assertNotIn("readonly: ON (", proc.stdout)
            combined = proc.stdout + proc.stderr
            self.assertIn("DENYING file edits", combined)
            self.assertNotIn("NOT armed", combined)


    def test_on_refuses_a_reason_too_long_for_the_hook_to_read(self):
        # The hook denies markers over 64 KiB without reading them, so a marker
        # the helper wrote from a huge reason would block every edit while `on`
        # reported failure. Refuse before writing anything instead.
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            proc = run_helper(["on", "x" * 70000], marker)
            self.assertNotEqual(0, proc.returncode, "on must refuse an oversized reason")
            self.assertFalse(os.path.exists(marker), "no marker may be written for a refused reason")
            combined = proc.stdout + proc.stderr
            self.assertIn("reason is too long", combined)
            self.assertIn("NOT armed", combined)

    def test_on_accepts_a_long_reason_that_still_fits_the_hook_cap(self):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            proc = run_helper(["on", "y" * 60000], marker)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn("readonly: ON", proc.stdout)


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
            combined = proc.stdout + proc.stderr
            self.assertIn("FAILED to clear", combined)
            self.assertIn("STILL BLOCKS", combined)
            self.assertNotIn("readonly: OFF", combined)
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


class HelperAgreesWithHook(unittest.TestCase):
    """The helper must never report a state the hook contradicts.

    Three review findings lived in this gap: the helper re-derived the marker
    state instead of asking the hook, so for an inaccessible parent it said
    OFF/ALLOW while the hook denied, and `off` announced a clear that had not
    happened. Any second implementation of a gate's logic drifts from it. The
    helper now queries the hook, and this test pins that agreement so a future
    edit cannot quietly reintroduce a private copy of the rules.
    """

    def _hook_blocks(self, marker):
        import importlib.util
        spec = importlib.util.spec_from_file_location("readonly_selftest", SELFTEST)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verdict, _ = module.fire(marker)
        return verdict == "BLOCK"

    def _helper_says_blocked(self, marker):
        proc = run_helper(["status"], marker)
        combined = proc.stdout + proc.stderr
        return "readonly: ON" in combined

    def _check(self, make):
        with tempfile.TemporaryDirectory() as d:
            marker = make(d)
            try:
                self.assertEqual(
                    self._hook_blocks(marker),
                    self._helper_says_blocked(marker),
                    "helper status disagrees with hook enforcement for %s" % marker,
                )
            finally:
                for path in (os.path.dirname(marker), d):
                    try:
                        os.chmod(path, 0o700)
                    except OSError:
                        pass

    def test_agree_on_active(self):
        def make(d):
            p = os.path.join(d, "readonly.json")
            with open(p, "w") as fh:
                fh.write('{"active": true}')
            return p
        self._check(make)

    def test_agree_on_explicit_false(self):
        def make(d):
            p = os.path.join(d, "readonly.json")
            with open(p, "w") as fh:
                fh.write('{"active": false}')
            return p
        self._check(make)

    def test_agree_on_malformed(self):
        def make(d):
            p = os.path.join(d, "readonly.json")
            with open(p, "w") as fh:
                fh.write("{not json")
            return p
        self._check(make)

    def test_agree_on_absent(self):
        self._check(lambda d: os.path.join(d, "nope.json"))

    @unittest.skipIf(os.geteuid() == 0, "root ignores the search bit")
    def test_agree_when_parent_is_unsearchable(self):
        # The exact state the helper used to get wrong: invisible to a plain
        # existence probe, denied by the hook.
        def make(d):
            parent = os.path.join(d, "state")
            os.mkdir(parent)
            p = os.path.join(parent, "readonly.json")
            with open(p, "w") as fh:
                fh.write('{"active": true}')
            os.chmod(parent, 0)
            return p
        self._check(make)


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


class HookRunsIsolatedFromTheSessionCwd(unittest.TestCase):
    """The harness runs the hook from the session directory, and a hook the harness
    cannot run (not executable) or that crashes without a deny is fail-open."""

    HOOK = os.path.join(SKILL_DIR, "hooks", "pretooluse-readonly.sh")

    def test_status_is_not_fooled_by_a_json_module_in_the_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            with open(marker, "w") as fh:
                fh.write('{"active": true}')
            repo = os.path.join(d, "audited-repo")
            os.mkdir(repo)
            with open(os.path.join(repo, "json.py"), "w") as fh:
                fh.write("import sys\nsys.exit(0)\n")
            env = dict(os.environ, READONLY_MARKER=marker)
            proc = subprocess.run(["bash", HELPER, "status"], capture_output=True,
                                  text=True, env=env, cwd=repo, timeout=30)
            self.assertIn("readonly: ON", proc.stdout, proc.stdout + proc.stderr)

    def test_a_fail_closed_deny_says_which_marker_and_how_to_recover(self):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "readonly.json")
            with open(marker, "w") as fh:
                fh.write("{not json")
            proc = subprocess.run([self.HOOK], input='{"tool_name": "Write"}',
                                  capture_output=True, text=True,
                                  env=dict(os.environ, READONLY_MARKER=marker), timeout=30)
            self.assertEqual(2, proc.returncode)
            self.assertIn(marker, proc.stderr)
            self.assertIn("readonly-mode.sh", proc.stderr)

    def test_status_does_not_report_on_for_a_hook_the_harness_cannot_execute(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            tree = os.path.join(d, "readonly")
            shutil.copytree(SKILL_DIR, tree)
            hook = os.path.join(tree, "hooks", "pretooluse-readonly.sh")
            os.chmod(hook, 0o644)
            marker = os.path.join(d, "readonly.json")
            with open(marker, "w") as fh:
                fh.write('{"active": true}')
            proc = subprocess.run(["bash", os.path.join(tree, "scripts", "readonly-mode.sh"), "status"],
                                  capture_output=True, text=True,
                                  env=dict(os.environ, READONLY_MARKER=marker), timeout=30)
            self.assertNotEqual(0, proc.returncode, proc.stdout)
            self.assertNotIn("readonly: ON", proc.stdout)
