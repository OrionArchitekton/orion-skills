"""Positive and negative DLP tests for EDITORIAL-001 public technical allowlist."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load_redactor(surface: str):
    path = ROOT / "skills" / surface / "publish-core" / "redactor.py"
    spec = importlib.util.spec_from_file_location(f"redactor_{surface}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EditorialAllowlistDlpTest(unittest.TestCase):
    def test_allowlist_schema_and_versions_match_across_surfaces(self):
        gist_path = ROOT / "skills/gist/references/public-technical-identifiers.v1.json"
        x_path = ROOT / "skills/x/references/public-technical-identifiers.v1.json"
        self.assertTrue(gist_path.is_file())
        self.assertTrue(x_path.is_file())
        gist_data = json.loads(gist_path.read_text(encoding="utf-8"))
        x_data = json.loads(x_path.read_text(encoding="utf-8"))
        self.assertEqual(gist_data, x_data)
        self.assertEqual(gist_data["schema_version"], "public-technical-allowlist/v1")
        self.assertEqual(gist_data["version"], "1.0.0")
        cats = gist_data["categories"]
        self.assertIn("GIT_WORK_TREE", cats["git_env_and_config"])
        self.assertIn("core.worktree", cats["git_env_and_config"])
        self.assertIn("git", cats["cli_commands_and_flags"])
        self.assertIn("systemd", cats["cli_commands_and_flags"])
        self.assertIn("pytest", cats["cli_commands_and_flags"])
        self.assertIn("ffmpeg", cats["cli_commands_and_flags"])
        self.assertIn("RFC 8058", cats["rfcs_and_standards"])
        self.assertIn("ECONNREFUSED", cats["public_error_identifiers"])
        self.assertIn("pydantic", cats["oss_libraries_and_runtimes"])
        self.assertIn("containsSyntheticMedia", cats["documented_apis_and_headers"])

    def test_positive_dlp_public_technical_identifiers_survive_verbatim(self):
        prose = (
            "Git checks with git -C repo --work-tree dir failed when GIT_WORK_TREE and "
            "core.worktree drifted. Services under systemd ran pytest and ffmpeg checks "
            "before validating RFC 8058 List-Unsubscribe-Post headers, pydantic schemas, "
            "ECONNREFUSED handling, containsSyntheticMedia, "
            "--enable-experimental-web-platform-features, and "
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE."
        )
        for surface in ("gist", "x"):
            with self.subTest(surface=surface), tempfile.TemporaryDirectory() as td:
                rules = Path(td) / "rules.txt"
                rules.write_text("", encoding="utf-8")
                with patch.dict(os.environ, {"HOME": td, "X_DENYLIST_FILE": str(rules)}, clear=True):
                    mod = _load_redactor(surface)
                    verdict, hits = mod.decision(prose)
                    self.assertEqual(verdict, "PUBLISH", f"unexpected hits: {hits}")
                    self.assertEqual(hits, [])
                    self.assertEqual(mod.redact(prose), prose)
                    version, entries = mod.load_public_allowlist()
                    self.assertEqual(version, "1.0.0")
                    self.assertIn("GIT_WORK_TREE", entries)
                    self.assertIn("core.worktree", entries)

    def test_negative_dlp_credentials_tailnet_private_hosts_and_pii_hard_block(self):
        bad_samples = {
            "doppler-credential": "GIT_WORK_TREE check leaked dp.st.prod.secretToken123456",
            "openai-sk": "core.worktree config beside sk-proj-AbCdEf0123456789ghIj",
            "github-ghp": "systemd unit exposed ghp_AbCdEf0123456789ghIjKlMnOpQrStUv",
            "tailnet-ip-low": "pytest probed 100.64.0.1 over tailnet",
            "tailnet-ip-mid": "ffmpeg stream hit 100.80.12.34:8080",
            "tailnet-ip-high": "route pointed to 100.127.255.1",
            "private-host-internal": "postgres at db.internal refused ECONNREFUSED",
            "private-host-custom": "systemd deployed to prod-worker-01 overnight",
            "customer-email": "user alice.customer@gmail.com reported a billing error",
            "customer-ssn": "record held SSN 123-45-6789 in payload",
            "customer-phone": "caller reached 555-234-5678 on support line",
        }
        for surface in ("gist", "x"):
            with self.subTest(surface=surface), tempfile.TemporaryDirectory() as td:
                rules = Path(td) / "rules.txt"
                rules.write_text("prod-worker-01\n", encoding="utf-8")
                with patch.dict(os.environ, {"HOME": td, "X_DENYLIST_FILE": str(rules)}, clear=True):
                    mod = _load_redactor(surface)
                    for label, sample in bad_samples.items():
                        with self.subTest(label=label):
                            verdict, hits = mod.decision(sample)
                            self.assertEqual(verdict, "ABSTAIN", f"sample leaked through: {label}")
                            self.assertTrue(hits)
                            self.assertNotEqual(mod.redact(sample), sample)

    def test_hybrid_secret_next_to_allowlisted_term_and_malformed_allowlist_fail_closed(self):
        for surface in ("gist", "x"):
            with self.subTest(surface=surface), tempfile.TemporaryDirectory() as td:
                rules = Path(td) / "rules.txt"
                rules.write_text("", encoding="utf-8")
                with patch.dict(os.environ, {"HOME": td, "X_DENYLIST_FILE": str(rules)}, clear=True):
                    mod = _load_redactor(surface)
                    hybrid = "GIT_WORK_TREE=sk-proj-AbCdEf0123456789ghIj core.worktree=/home/alice/repo"
                    verdict, hits = mod.decision(hybrid)
                    self.assertEqual(verdict, "ABSTAIN")
                    classes = {cls for cls, _ in hits}
                    self.assertIn("secret", classes)
                    self.assertIn("internal-path", classes)
                    bad_allowlist = Path(td) / "bad.json"
                    bad_allowlist.write_text("{not-json", encoding="utf-8")
                    orig = mod.ALLOWLIST_PATH
                    mod.ALLOWLIST_PATH = bad_allowlist
                    try:
                        bad_verdict, bad_hits = mod.decision("git status")
                        self.assertEqual(bad_verdict, "ABSTAIN")
                        self.assertEqual(bad_hits[0][0], "redactor-config")
                    finally:
                        mod.ALLOWLIST_PATH = orig


if __name__ == "__main__":
    unittest.main()
