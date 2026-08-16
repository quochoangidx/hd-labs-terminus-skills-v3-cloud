from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "canonical_source_smoke.py"
SPEC = importlib.util.spec_from_file_location("canonical_source_smoke", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CanonicalSourceSmokeTests(unittest.TestCase):
    def test_plan_requires_digest_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "schema_version": 1,
                "candidate_slug": "tbrain-one",
                "source_dir": str(root),
                "source_revision": "abc123",
                "image": "rust:latest",
                "command": ["cargo", "check"],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sha256"):
                module.load_plan(plan)

    @patch.object(module.subprocess, "run")
    def test_execute_disables_network_and_uses_disposable_copy(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "ok", "")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            plan = {
                "source_dir": str(source),
                "image": "rust@sha256:" + "a" * 64,
                "command": ["cargo", "check"],
                "timeout_seconds": 10,
            }
            result, timed_out, command = module.execute(plan)
            self.assertEqual(0, result.returncode)
            self.assertFalse(timed_out)
            self.assertIn("none", command)
            self.assertTrue(any("dst=/src" in item for item in command))


if __name__ == "__main__":
    unittest.main()
