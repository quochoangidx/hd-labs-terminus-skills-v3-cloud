from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "batch-handover.py"
SPEC = importlib.util.spec_from_file_location("batch_handover", SCRIPT)
assert SPEC and SPEC.loader
handover = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handover)


class CandidateLedgerHandoverTests(unittest.TestCase):
    @patch.object(handover.subprocess, "run")
    def test_schema_v3_accepted_subset_matches_batch_index(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "{}", "")
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "batch-pattern-mix.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "accepted_task_slugs": ["tbrain-one"],
                    }
                ),
                encoding="utf-8",
            )
            errors: list[str] = []
            handover.validate_candidate_ledger(
                ledger, ["tbrain-one"], False, errors
            )
            self.assertEqual([], errors)

    @patch.object(handover.subprocess, "run")
    def test_schema_v3_rejects_mismatched_accepted_subset(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "{}", "")
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "batch-pattern-mix.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "accepted_task_slugs": ["tbrain-other"],
                    }
                ),
                encoding="utf-8",
            )
            errors: list[str] = []
            handover.validate_candidate_ledger(
                ledger, ["tbrain-one"], False, errors
            )
            self.assertTrue(any("must match" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
