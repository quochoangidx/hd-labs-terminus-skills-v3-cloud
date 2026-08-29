from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts/check_rubric.py"
SPEC = importlib.util.spec_from_file_location("check_rubric", SCRIPT)
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class RubricCheckTests(unittest.TestCase):
    def _packet(self, rubric: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        packet = directory / "SUBMISSION-example.md"
        packet.write_text(f"# Metadata\n\nExample\n\n# Rubrics\n\n{rubric}\n", encoding="utf-8")
        return packet

    def test_valid_task_specific_rubric(self):
        packet = self._packet(
            "\n".join(
                [
                    "Agent preserves the accepted transaction through delayed acknowledgement, +5",
                    "Agent reports the resolved resume address after redirect, +5",
                    "Agent replays an accepted transaction, -3",
                    "Agent exposes a killed-path store, -5",
                ]
            )
        )
        result = CHECK.inspect(packet)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["positive_total"], 10)
        self.assertEqual(result["negative_count"], 2)

    def test_rejects_leakage_and_bad_score_total(self):
        packet = self._packet(
            "\n".join(
                [
                    "Agent passes the hidden tests for retirement, +5",
                    "Agent loses a commit, -3",
                ]
            )
        )
        result = CHECK.inspect(packet)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("leakage" in item for item in result["errors"]))
        self.assertTrue(any("10-40" in item for item in result["errors"]))

    def test_warns_on_repeated_portfolio_topology(self):
        rubric = "\n".join(
            [
                "Agent preserves behavior alpha, +5",
                "Agent preserves behavior beta, +5",
                "Agent breaks behavior alpha or beta, -5",
            ]
        )
        results = [CHECK.inspect(self._packet(rubric)) for _ in range(3)]
        warnings = CHECK.portfolio_warnings(results)
        self.assertEqual(len(warnings), 2)

    def test_does_not_treat_value_variants_as_three_failure_clauses(self):
        packet = self._packet(
            "\n".join(
                [
                    "Agent preserves retirement timing, +5",
                    "Agent reports the precise resume PC, +5",
                    "Agent duplicates retirement or replays an accepted load or divide, -3",
                ]
            )
        )
        result = CHECK.inspect(packet)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["warnings"], [])

    def test_receipt_hash_binds_packet_and_complete_matrix(self):
        packet = self._packet(
            "\n".join(
                [
                    "Agent preserves retirement timing, +5",
                    "Agent reports the precise resume PC, +5",
                    "Agent replays an accepted load, -3",
                ]
            )
        )
        matrix = packet.with_name("rubric-coverage.md")
        matrix.write_text(
            "| contract_id | source | observable_requirement | witness_ids | "
            "discrimination | coverage | criterion_id |\n"
            "|---|---|---|---|---|---|---|\n"
            "| precise_pc | instruction.md | exact resume PC | irq_redirect | "
            "rejects stale PC | covered | R2 |\n",
            encoding="utf-8",
        )
        receipt = packet.with_name("rubric-check.json")

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(packet),
                "--coverage-matrix",
                str(matrix),
                "--output",
                str(receipt),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "pass")
        self.assertEqual(data["results"][0]["sha256"], CHECK.sha256(packet))
        self.assertEqual(data["coverage_matrix"]["sha256"], CHECK.sha256(matrix))

    def test_partial_matrix_fails(self):
        matrix = self._packet("Agent preserves behavior alpha, +5\nAgent avoids corruption, -3")
        matrix.write_text("| alpha | partial | R1 |\n", encoding="utf-8")
        result = CHECK.inspect_coverage_matrix(matrix)
        self.assertEqual(result["status"], "fail")


if __name__ == "__main__":
    unittest.main()
