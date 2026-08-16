from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


SCRIPT = (
    Path(__file__).parents[2]
    / ".agent"
    / "skills"
    / "task-batch"
    / "scripts"
    / "evidence.py"
)
SPEC = importlib.util.spec_from_file_location("task_batch_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_style_receipts_split_task_and_submission_surfaces(tmp_path: Path) -> None:
    task = tmp_path / "workspace" / "tasks" / "tbrain-example"
    report = tmp_path / "workspace" / "reports" / task.name
    submission = tmp_path / "workspace" / "submissions" / "SUBMISSION-tbrain-example.md"
    task.mkdir(parents=True)
    report.mkdir(parents=True)
    submission.parent.mkdir(parents=True)
    (task / "instruction.md").write_text("Repair the output.\n", encoding="utf-8")
    task_transcript = report / "task-style-preflight-transcript.md"
    task_transcript.write_text("Task-tree prose verified.\n", encoding="utf-8")
    task_receipt = report / "task-style-preflight.json"

    result = MODULE.task_style_receipt(
        SimpleNamespace(
            task_dir=task,
            transcript=task_transcript,
            runtime="codex",
            model="gpt-test",
            session_id="task-style-session",
            output=task_receipt,
        )
    )

    assert result == 0
    task_data = json.loads(task_receipt.read_text(encoding="utf-8"))
    assert task_data["schema_version"] == 1
    assert [row["path"] for row in task_data["surfaces"]] == ["instruction.md"]

    submission.write_text("# Difficulty Explanation\n\nObserved behavior.\n", encoding="utf-8")
    submission_transcript = report / "style-audit-transcript.md"
    submission_transcript.write_text("Submission prose verified.\n", encoding="utf-8")
    final_receipt = report / "style-audit.json"

    result = MODULE.style_receipt(
        SimpleNamespace(
            task_dir=task,
            submission=submission,
            transcript=submission_transcript,
            runtime="codex",
            model="gpt-test",
            session_id="submission-style-session",
            output=final_receipt,
        )
    )

    assert result == 0
    final_data = json.loads(final_receipt.read_text(encoding="utf-8"))
    assert final_data["schema_version"] == 2
    assert final_data["task_style_preflight_sha256"] == MODULE.load_handover().sha256(
        task_receipt
    )
    assert final_data["submission_surface"]["path"] == str(submission.resolve())
    assert "surfaces" not in final_data
