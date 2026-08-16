from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "session_budget.py"
SPEC = importlib.util.spec_from_file_location("session_budget", SCRIPT)
assert SPEC and SPEC.loader
session_budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(session_budget)


class SessionBudgetTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, dict]:
        task_dir = root / "tbrain-example"
        report_dir = root / "reports" / task_dir.name
        task_dir.mkdir()
        report_dir.mkdir(parents=True)
        fairness = [
            {
                "reviewer_id": f"reviewer-{index}",
                "runtime": "codex-thread",
                "model": "gpt-5.6-luna",
                "session_id": f"thread-fairness-{index}",
                "fresh_context": True,
                "task_visible_only": True,
            }
            for index in (1, 2)
        ]
        auditor = {
            "runtime": "codex-thread",
            "model": "gpt-5.6-luna",
            "session_id": "thread-auditor",
            "transcript": "consolidated-audit.md",
            "transcript_sha256": "a" * 64,
        }
        payloads = {
            "instruction-sufficiency.json": {"fairness_review": {"reviewers": fairness}},
            "semantic-coverage.json": {"review": auditor},
            "pre-freeze-review.json": {"manual_review": auditor},
            "task-style-preflight.json": {"auditor": auditor},
        }
        for name, payload in payloads.items():
            (report_dir / name).write_text(json.dumps(payload), encoding="utf-8")
        builder = {
            "runtime": "codex-subagent",
            "model": "gpt-5.6-sol",
            "session_id": "builder-agent",
        }
        return task_dir, report_dir, builder

    def test_accepts_luna_codex_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir, report_dir, builder = self.fixture(Path(tmp))
            receipt, errors = session_budget.build_receipt(task_dir, report_dir, builder)
            self.assertEqual([], errors)
            self.assertEqual(2, receipt["schema_version"])
            self.assertEqual("codex-thread", receipt["consolidated_auditor"]["runtime"])

    def test_rejects_luna_role_claimed_as_subagent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir, report_dir, builder = self.fixture(Path(tmp))
            sufficiency = json.loads(
                (report_dir / "instruction-sufficiency.json").read_text(encoding="utf-8")
            )
            sufficiency["fairness_review"]["reviewers"][0]["runtime"] = "codex-subagent"
            (report_dir / "instruction-sufficiency.json").write_text(
                json.dumps(sufficiency), encoding="utf-8"
            )
            _, errors = session_budget.build_receipt(task_dir, report_dir, builder)
            self.assertTrue(any("runtime must be codex-thread" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
