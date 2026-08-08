"""Contract tests for the readonly PreToolUse enforcement hook.

These do not re-implement the matrix; they run the shipped selftest, which fires
the real hook script with real payloads. Keeping one matrix means CI and a
stranger running `python3 skills/readonly/selftest.py` are checking the same
thing, so the published proof cannot drift from what CI enforces.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO_ROOT, "skills", "readonly")
HOOK = os.path.join(SKILL_DIR, "hooks", "pretooluse-readonly.sh")
HELPER = os.path.join(SKILL_DIR, "scripts", "readonly-mode.sh")
SELFTEST = os.path.join(SKILL_DIR, "selftest.py")


def _load_selftest():
    spec = importlib.util.spec_from_file_location("readonly_selftest", SELFTEST)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadonlyHookShipsExecutable(unittest.TestCase):
    def test_hook_and_helper_exist(self):
        self.assertTrue(os.path.exists(HOOK), "enforcement hook must ship in the repo")
        self.assertTrue(os.path.exists(HELPER), "marker helper must ship in the repo")
        self.assertTrue(os.path.exists(SELFTEST), "selftest must ship so the claim is reproducible")

    def test_hook_and_helper_are_executable(self):
        # The README claims a hook that enforces. A non-executable file is a
        # document, not a control, so the exec bit is part of the contract.
        for path in (HOOK, HELPER, SELFTEST):
            mode = os.stat(path).st_mode
            self.assertTrue(mode & stat.S_IXUSR, "%s must be executable" % os.path.basename(path))


class ReadonlyHookDenies(unittest.TestCase):
    def test_every_case_behaves(self):
        results = _load_selftest().run_all()
        self.assertTrue(results, "selftest produced no cases")
        failures = [
            "%s: expected %s, got %s (%s)" % (name, expected, actual, detail)
            for name, expected, actual, detail, ok in results
            if not ok
        ]
        self.assertEqual([], failures, "hook did not behave:\n  " + "\n  ".join(failures))

    def test_suite_has_both_block_and_allow_cases(self):
        # A block-only suite cannot tell an enforcing gate from one that blocks
        # everything, and an allow-only suite proves nothing at all.
        results = _load_selftest().run_all()
        expectations = {expected for _, expected, _, _, _ in results}
        self.assertIn("BLOCK", expectations)
        self.assertIn("ALLOW", expectations)

    def test_malformed_markers_are_denied_not_ignored(self):
        # The specific fail-open trap: an unparseable marker must block, because
        # "I could not evaluate the policy" is not "the policy permits this".
        results = _load_selftest().run_all()
        by_name = {name: (expected, actual) for name, expected, actual, _, _ in results}
        for name in by_name:
            if "denies" in name:
                expected, actual = by_name[name]
                self.assertEqual("BLOCK", actual, "%s should have blocked" % name)


if __name__ == "__main__":
    unittest.main()
