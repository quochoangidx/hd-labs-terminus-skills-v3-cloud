from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("panel_gate", SCRIPTS / "panel_gate.py")
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

from prepare_packets import AXIS_SURFACES, build_packets  # noqa: E402


def make_task(root: Path) -> Path:
    task = root / "tbrain-gate-fixture"
    task.mkdir()
    (task / "instruction.md").write_text("Implement the requested behavior.\n")
    (task / "task.toml").write_text('version = "1.0"\n')
    for directory in ("environment", "solution", "tests"):
        (task / directory).mkdir()
        (task / directory / f"{directory}.txt").write_text(f"{directory}\n")
    return task


def reviewer_files(root: Path, manifest: Path, axis: str) -> list[str]:
    snapshot = json.loads(manifest.read_text())["snapshot_sha256"]
    paths = []
    for side in "AB":
        path = root / "reviewers" / f"{axis}-{side}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"axis": axis, "snapshot_sha256": snapshot, "severity": "None",
                                    "input_completeness": {"status": "complete"}}))
        paths.append(str(path))
    return paths


def report(path: Path, task: Path, manifest: Path, verdicts: dict[str, str] | None = None) -> Path:
    verdicts = verdicts or {}
    data = {
        "snapshot_sha256": GATE.sha256_tree(task),
        "axes": {
            axis: {"verdict": verdicts.get(axis, "None"), "complete": True, "packet_manifest": str(manifest),
                   "reviewers": reviewer_files(path.parent, manifest, axis)}
            for axis in AXIS_SURFACES
        },
    }
    path.write_text(json.dumps(data))
    return path


def test_unchanged_task_reruns_only_finding_axes(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    result = GATE.clearance_axes(task, manifest, ["sound_verifier"])
    assert result["clearance_axes"] == ["sound_verifier"]
    assert "coherent_contract" in result["carried_axes"]


def test_tests_edit_reruns_only_sound_verifier(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    (task / "tests" / "test_new.py").write_text("def test_x():\n    pass\n")
    result = GATE.clearance_axes(task, manifest, [])
    assert result["clearance_axes"] == ["sound_verifier"]


def test_strict_visibility_restores_every_axis_that_sees_tests(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    (task / "tests" / "test_new.py").write_text("def test_x():\n    pass\n")
    result = GATE.clearance_axes(task, manifest, [], strict=True)
    assert result["clearance_axes"] == [
        "coherent_contract", "protected_ground_truth", "sound_verifier", "deterministic_execution",
    ]
    assert result["carried_axes"] == ["correct_reference_solution"]


def test_harness_edit_reruns_ground_truth_and_determinism(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    (task / "tests" / "test.sh").write_text("#!/bin/bash\n")
    result = GATE.clearance_axes(task, manifest, [])
    assert result["clearance_axes"] == ["protected_ground_truth", "sound_verifier", "deterministic_execution"]


def test_instruction_edit_reruns_every_axis(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    (task / "instruction.md").write_text("Changed.\n")
    assert GATE.clearance_axes(task, manifest, [])["carried_axes"] == []


def test_gate_receipts_carry_only_eligible_axes(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest)
    data = json.loads(path.read_text())
    receipt = tmp_path / "determinism.json"
    receipt.write_text("{}")
    data["axes"]["deterministic_execution"] = {"verdict": "None", "complete": True, "source": "gate",
                                               "packet_manifest": str(manifest), "gate_receipts": [str(receipt)]}
    path.write_text(json.dumps(data))
    result = GATE.check(task, path)
    assert result["passed"] and result["gate_carried_axes"] == ["deterministic_execution"]
    data["axes"]["sound_verifier"] = {"verdict": "None", "complete": True, "source": "gate",
                                      "packet_manifest": str(manifest), "gate_receipts": [str(receipt)]}
    path.write_text(json.dumps(data))
    assert any(error.startswith("sound_verifier: needs two panel reviewers")
               for error in GATE.check(task, path)["errors"])


def test_solution_edit_reruns_reference_and_determinism(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    (task / "solution" / "solution.txt").write_text("changed\n")
    result = GATE.clearance_axes(task, manifest, [])
    assert result["clearance_axes"] == ["correct_reference_solution", "deterministic_execution"]


def test_check_passes_clean_panel_and_accepts_ground_truth_minor(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest, {"protected_ground_truth": "Minor"})
    assert GATE.check(task, path)["passed"]


def test_check_rejects_blocking_and_undecided_verdicts(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest,
                  {"sound_verifier": "Minor", "coherent_contract": "Unsure"})
    errors = GATE.check(task, path)["errors"]
    assert any(error.startswith("sound_verifier") for error in errors)
    assert any(error.startswith("coherent_contract") for error in errors)


def test_check_rejects_verdict_carried_across_a_visible_change(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    (task / "tests" / "tests.txt").write_text("changed\n")
    path = report(tmp_path / "report.json", task, manifest)
    errors = GATE.check(task, path)["errors"]
    assert any("stale" in error and error.startswith("sound_verifier") for error in errors)
    assert not any(error.startswith("correct_reference_solution") for error in errors)


def test_check_rejects_report_for_another_snapshot(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest)
    (task / "task.toml").write_text('version = "2.0"\n')
    errors = GATE.check(task, path)["errors"]
    assert any("is not the task snapshot" in error for error in errors)


def test_discovery_report_reruns_undecided_axes(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest, {"coherent_contract": "Unsure"})
    result = GATE.clearance_axes(task, manifest, [], path)
    assert result["clearance_axes"] == ["coherent_contract"]


def test_check_requires_raw_reviews_or_platform_source(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest)
    data = json.loads(path.read_text())
    data["axes"]["sound_verifier"]["reviewers"] = []
    platform = tmp_path / "platform-report.txt"
    platform.write_text("[coherent_contract] None\n")
    data["axes"]["coherent_contract"] = {"verdict": "None", "complete": True, "packet_manifest": str(manifest),
                                         "source": "platform", "platform_report": str(platform)}
    path.write_text(json.dumps(data))
    errors = GATE.check(task, path)["errors"]
    assert errors == ["sound_verifier: expected two raw reviewer responses, found 0"]


def test_check_rejects_review_of_another_snapshot(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = report(tmp_path / "report.json", task, manifest)
    raw = tmp_path / "reviewers" / "sound_verifier-A.json"
    raw.write_text(json.dumps({"axis": "sound_verifier", "snapshot_sha256": "0" * 64,
                               "input_completeness": {"status": "complete"}}))
    assert any("is not a review" in error for error in GATE.check(task, path)["errors"])


def adjudication(tmp_path: Path, manifest: Path, verdicts: dict[str, dict] | None = None) -> Path:
    for axis in AXIS_SURFACES:
        reviewer_files(tmp_path, manifest, axis)
    axes = {axis: {"verdict": "None"} for axis in AXIS_SURFACES}
    axes.update(verdicts or {})
    path = tmp_path / "adjudication.json"
    path.write_text(json.dumps({"packet_manifest": str(manifest), "reviewers_dir": "reviewers", "axes": axes}))
    return path


def test_write_report_builds_a_report_that_check_accepts(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    result = GATE.write_report(task, adjudication(tmp_path, manifest), tmp_path / "out" / "report.json")
    assert result["passed"], result["errors"]
    written = json.loads((tmp_path / "out" / "report.json").read_text())
    assert written["snapshot_sha256"] == GATE.sha256_tree(task)
    assert all(entry["complete"] for entry in written["axes"].values())


def test_write_report_refuses_silent_downgrade(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = adjudication(tmp_path, manifest)
    raw = tmp_path / "reviewers" / "sound_verifier-B.json"
    data = json.loads(raw.read_text()); data["severity"] = "Major"; raw.write_text(json.dumps(data))
    result = GATE.write_report(task, path, tmp_path / "report.json")
    assert not result["passed"]
    assert "downgrade_reason" in result["errors"][0]
    adj = json.loads(path.read_text())
    adj["axes"]["sound_verifier"]["downgrade_reason"] = "B-1 rejected: witness fails on the cited case"
    path.write_text(json.dumps(adj))
    assert GATE.write_report(task, path, tmp_path / "report.json")["passed"]


def test_write_report_marks_missing_review_incomplete(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    manifest = build_packets(task, tmp_path / "packets")
    path = adjudication(tmp_path, manifest)
    (tmp_path / "reviewers" / "coherent_contract-A.json").unlink()
    errors = GATE.write_report(task, path, tmp_path / "report.json")["errors"]
    assert any(error.startswith("coherent_contract: review incomplete") for error in errors)
