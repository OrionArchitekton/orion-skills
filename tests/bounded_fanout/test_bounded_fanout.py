"""Run the public result-boundary Node suite in a fixture-owned offline environment."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class BoundedResultsTest(unittest.TestCase):
    def test_node_result_boundary(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(prefix='bounded-results-offline-') as temp:
            env = {
                'PATH': os.environ['PATH'], 'HOME': temp, 'TMPDIR': temp,
                'XDG_CONFIG_HOME': temp, 'LC_ALL': 'C.UTF-8',
                'GIT_CEILING_DIRECTORIES': temp,
            }
            result = subprocess.run(
                ['node', '--test', str(root / 'tests/bounded_fanout/results.test.mjs')],
                cwd=temp, env=env, text=True, capture_output=True, timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
