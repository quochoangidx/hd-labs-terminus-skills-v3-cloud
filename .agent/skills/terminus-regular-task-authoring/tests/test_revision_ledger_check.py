from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "revision_ledger_check.py"
SPEC = importlib.util.spec_from_file_location("revision_ledger_check", SCRIPT)
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def receipt(path: Path, snapshot: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "task_snapshot_sha256": snapshot,
                "command": "pytest tests/test_outputs.py::test_authority",
                "exit_code": 1,
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def case(tmp_path: Path):
    task = tmp_path / "tbrain-return"
    task.mkdir()
    (task / "instruction.md").write_text("Reconcile the authority.\n", encoding="utf-8")
    repaired = CHECK.tree_hash(task)
    returned = hashlib.sha256(b"the snapshot the platform judged").hexdigest()

    report_dir = tmp_path / "reports"
    receipt(report_dir / "receipts" / "f1-repro.json", returned)
    receipt(report_dir / "receipts" / "f1-closed.json", repaired)

    ledger = {
        "schema_version": 1,
        "task_slug": task.name,
        "report_path": "panel-return-3.md",
        "returned_snapshot_sha256": returned,
        "repaired_snapshot_sha256": repaired,
        "findings": [
            {
                "id": "F1",
                "axis": "sound_verifier",
                "severity": "Major",
                "blocking": True,
                "decision": "backed",
                "rationale": "the ordering rule is core to what the task tests",
                "reproduction": "receipts/f1-repro.json",
                "closure": "receipts/f1-closed.json",
                "gate": {"rule": "unenforced_restriction", "script": "panel_precheck.py"},
            }
        ],
        "previous_findings": [],
    }
    return task, report_dir / "revision-ledger.json", ledger


def codes(task: Path, path: Path, ledger: dict, manifest: Path | None = None) -> set[str]:
    path.write_text(json.dumps(ledger), encoding="utf-8")
    return {b["code"] for b in CHECK.validate(task, path, manifest)["blockers"]}


def test_a_backed_finding_with_both_receipts_passes(case) -> None:
    task, path, ledger = case
    assert codes(task, path, ledger) == set()


def test_a_closure_receipt_alone_does_not_answer_a_finding(case) -> None:
    """Without the reproduction, nothing shows the test ever failed."""
    task, path, ledger = case
    del ledger["findings"][0]["reproduction"]

    assert "missing_receipt" in codes(task, path, ledger)


def test_a_reproduction_bound_to_the_wrong_snapshot_is_rejected(case) -> None:
    """The defect must be shown on the tree the platform judged, not on the repair."""
    task, path, ledger = case
    receipt(path.parent / "receipts" / "f1-repro.json", ledger["repaired_snapshot_sha256"])

    assert "stale_receipt" in codes(task, path, ledger)


def test_acknowledging_a_blocking_finding_is_not_an_answer(case) -> None:
    task, path, ledger = case
    ledger["findings"][0]["decision"] = "acknowledged"

    assert "unanswered_blocker" in codes(task, path, ledger)


def test_a_dropped_promise_must_appear_in_removed_obligations(case) -> None:
    task, path, ledger = case
    ledger["findings"][0].update({"decision": "dropped", "removed_obligation_id": "RETRY"})
    for key in ("reproduction", "closure"):
        ledger["findings"][0].pop(key)
    manifest = path.parent / "panel-precheck-manifest.json"
    manifest.write_text(json.dumps({"removed_obligations": []}), encoding="utf-8")

    assert "dropped_not_recorded" in codes(task, path, ledger, manifest)

    manifest.write_text(
        json.dumps({"removed_obligations": [{"id": "RETRY"}]}), encoding="utf-8"
    )
    assert "dropped_not_recorded" not in codes(task, path, ledger, manifest)


def test_a_dispute_needs_a_citation_and_a_counterexample(case) -> None:
    task, path, ledger = case
    ledger["findings"][0].update({"decision": "disputed"})
    for key in ("reproduction", "closure"):
        ledger["findings"][0].pop(key)

    found = codes(task, path, ledger)
    assert "dispute_without_citation" in found
    assert "missing_receipt" in found


def test_every_finding_must_buy_a_gate_or_record_why_it_cannot(case) -> None:
    task, path, ledger = case
    del ledger["findings"][0]["gate"]

    assert "no_gate" in codes(task, path, ledger)

    ledger["findings"][0]["gate"] = {
        "not_mechanizable": "needs a judgement about whether two readings of the contract differ"
    }
    assert "no_gate" not in codes(task, path, ledger)


def test_a_carried_forward_finding_needs_an_explicit_response(case) -> None:
    """The report omitting an old finding does not resolve it."""
    task, path, ledger = case
    ledger["previous_findings"] = [{"id": "P1", "status": "still_open"}]

    assert "previous_unanswered" in codes(task, path, ledger)


def test_the_returned_snapshot_must_be_recorded(case) -> None:
    """Findings are about what the platform judged, not a tree that has since drifted."""
    task, path, ledger = case
    del ledger["returned_snapshot_sha256"]

    assert "returned_snapshot" in codes(task, path, ledger)


def test_the_ledger_must_bind_to_the_current_tree(case) -> None:
    task, path, ledger = case
    (task / "instruction.md").write_text("Reconcile the authority differently.\n", encoding="utf-8")

    assert "stale_ledger" in codes(task, path, ledger)


def test_a_dispute_must_be_raised_where_the_panel_reads_it(case) -> None:
    """A rebuttal left in the platform revision note never reaches the panel."""
    task, path, ledger = case
    ledger["findings"][0].update(
        {
            "decision": "disputed",
            "contract_citation": {"file": "instruction.md", "anchor": "Reconcile the authority"},
            "counterexample": "receipts/f1-repro.json",
        }
    )
    for key in ("reproduction", "closure"):
        ledger["findings"][0].pop(key)

    assert "dispute_not_raised" in codes(task, path, ledger)

    ledger["findings"][0]["contested_in_channel"] = "#terminus-3-submissions 2026-09-23, thread 'tbrain-return F1'"
    assert "dispute_not_raised" not in codes(task, path, ledger)
