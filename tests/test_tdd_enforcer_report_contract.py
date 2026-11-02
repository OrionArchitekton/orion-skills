"""Execute the published Bash gate against disposable offline scanner fixtures."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/tool_evidence'
ENFORCER = ROOT / 'skills/tdd-loop/references/ENFORCER.md'


def secret_gate():
    section = ENFORCER.read_text().split('## Secret gate', 1)[1]
    return re.search(r'```bash\n(.*?)\n```', section, re.S).group(1)


class EnforcerReportTest(unittest.TestCase):
    def run_gate(self, mode, rc=0, pipeline=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / 'gitleaks'
            fake.write_text('''#!/bin/sh
printf '%s\\n' "$@" > "$ARGS_FILE"
while [ "$#" -gt 0 ]; do
    if [ "$1" = --report-path ]; then shift; report="$1"; fi
    shift
done
case "$SCANNER_MODE" in
  missing) rm -f "$report" ;;
  empty) : ;;
  *) cp "$FIXTURE_DIR/$SCANNER_MODE" "$report" ;;
esac
exit "$SCANNER_RC"
''')
            fake.chmod(0o700)
            env = {'PATH': str(root) + os.pathsep + os.defpath + os.pathsep + str(Path(sys.executable).parent),
                   'HOME': tmp, 'TMPDIR': tmp, 'LC_ALL': 'C', 'SCANNER_MODE': mode,
                   'SCANNER_RC': str(rc), 'FIXTURE_DIR': str(FIXTURES), 'ARGS_FILE': str(root / 'args')}
            gate = secret_gate()
            if pipeline:
                # A logging wrapper must not turn the scanner's failure into cat's success.
                gate = gate.replace('if gitleaks ', 'if scanner_log_wrapper ')
                gate = 'scanner_log_wrapper() { gitleaks "$@" 2>&1 | cat; }\n' + gate
            proc = subprocess.run(['/bin/bash', '-e', '-c', gate + '\nprintf gate-passed'],
                                  env=env, cwd=tmp, text=True, capture_output=True, timeout=10)
            args = (root / 'args').read_text().splitlines()
            return proc, args

    def test_precreated_empty_report_is_not_clean_evidence(self):
        proc, _ = self.run_gate('empty')
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn('gate-passed', proc.stdout)

    def test_missing_malformed_wrong_shape_and_positive_reports_block(self):
        for mode in ('missing', 'malformed.json', 'null.json', 'object.json',
                     'wrapped.json', 'positive.json', 'scalar.json'):
            with self.subTest(mode=mode):
                proc, _ = self.run_gate(mode)
                self.assertNotEqual(proc.returncode, 0, proc.stdout)
                self.assertNotIn('gate-passed', proc.stdout)
                self.assertNotIn('synthetic-test', proc.stdout + proc.stderr)

    def test_successful_scanner_with_empty_findings_passes(self):
        proc, args = self.run_gate('gitleaks-clean.json')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('gate-passed', proc.stdout)
        self.assertEqual(args[:2], ['git', '--staged'])
        self.assertIn('--redact', args)
        self.assertEqual(args[args.index('--report-format') + 1], 'json')

    def test_clean_report_does_not_mask_failed_scanner_or_logging_pipeline(self):
        for rc in (1, 2, 124):
            for pipeline in (False, True):
                with self.subTest(rc=rc, pipeline=pipeline):
                    proc, _ = self.run_gate('gitleaks-clean.json', rc=rc, pipeline=pipeline)
                    self.assertNotEqual(proc.returncode, 0, proc.stdout)
                    self.assertNotIn('gate-passed', proc.stdout)
