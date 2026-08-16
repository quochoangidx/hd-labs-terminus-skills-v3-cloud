from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "batch-handover.py"
SPEC = importlib.util.spec_from_file_location("batch_handover", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_one_of_three_requires_distinct_multi_node_failures() -> None:
    result = MODULE.semantic_probe_geometry(
        [
            {"result": "fail", "failure_nodes": {"M:a", "I:ab"}},
            {"result": "fail", "failure_nodes": {"M:b", "I:bc"}},
            {"result": "pass", "failure_nodes": set()},
        ]
    )
    assert result["advanced_geometry_pass"] is True


def test_replicated_single_lever_is_not_advanced() -> None:
    result = MODULE.semantic_probe_geometry(
        [
            {"result": "fail", "failure_nodes": {"M:keyword"}},
            {"result": "fail", "failure_nodes": {"M:keyword"}},
            {"result": "pass", "failure_nodes": set()},
        ]
    )
    assert result["advanced_geometry_pass"] is False
    assert result["semantic_de_correlated"] is False


def test_two_identical_multi_node_failures_are_not_advanced() -> None:
    result = MODULE.semantic_probe_geometry(
        [
            {"result": "fail", "failure_nodes": {"M:a", "I:ab"}},
            {"result": "fail", "failure_nodes": {"M:a", "I:ab"}},
            {"result": "pass", "failure_nodes": set()},
        ]
    )
    assert result["advanced_geometry_pass"] is False


def _write_design(report_root: Path, slug: str, domain: str, family: str, suffix: str) -> dict:
    signature = {
        "work_surface": f"work-{suffix}",
        "interaction": f"interaction-{suffix}",
        "input_surface": f"input-{suffix}",
        "oracle_type": f"oracle-{suffix}",
        "verifier_type": f"verifier-{suffix}",
        "failure_mode": f"failure-{suffix}",
    }
    value = {
        "status": "pass",
        "task_slug": slug,
        "batch_id": "batch-1",
        "domain_key": domain,
        "architecture_family": family,
        "signature": signature,
        "compared_against": [],
        "max_pairwise_matches": 0,
    }
    path = report_root / slug / "design-signature.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return value


def test_batch_index_requires_complete_peer_comparison(tmp_path: Path) -> None:
    reports = tmp_path / "workspace" / "reports"
    left = _write_design(reports, "tbrain-left", "media-music", "audio-state", "a")
    right = _write_design(reports, "tbrain-right", "hardware-cad", "solid-geometry", "b")
    left["compared_against"] = ["tbrain-right"]
    right["compared_against"] = ["tbrain-left"]
    for value in (left, right):
        path = reports / value["task_slug"] / "design-signature.json"
        path.write_text(json.dumps(value), encoding="utf-8")
    batch = {
        "schema_version": 1,
        "status": "pass",
        "batch_id": "batch-1",
        "expected_count": 2,
        "task_slugs": ["tbrain-left", "tbrain-right"],
    }
    errors: list[str] = []
    MODULE.validate_batch_index(
        batch,
        "tbrain-left",
        reports / "tbrain-left",
        left,
        2,
        errors,
    )
    assert errors == []


def test_batch_index_rejects_partial_comparison_list(tmp_path: Path) -> None:
    reports = tmp_path / "workspace" / "reports"
    left = _write_design(reports, "tbrain-left", "media-music", "audio-state", "a")
    _write_design(reports, "tbrain-right", "hardware-cad", "solid-geometry", "b")
    batch = {
        "schema_version": 1,
        "status": "pass",
        "batch_id": "batch-1",
        "expected_count": 2,
        "task_slugs": ["tbrain-left", "tbrain-right"],
    }
    errors: list[str] = []
    MODULE.validate_batch_index(
        batch,
        "tbrain-left",
        reports / "tbrain-left",
        left,
        2,
        errors,
    )
    assert any("every other batch task" in error for error in errors)


def test_schema_v2_incremental_index_allows_first_handover(tmp_path: Path) -> None:
    reports = tmp_path / "workspace" / "reports"
    first = _write_design(reports, "tbrain-first", "media-music", "audio-state", "a")
    batch = {
        "schema_version": 2,
        "status": "building",
        "batch_id": "batch-1",
        "expected_count": 3,
        "task_slugs": ["tbrain-first"],
    }
    errors: list[str] = []
    MODULE.validate_batch_index(
        batch,
        "tbrain-first",
        reports / "tbrain-first",
        first,
        3,
        errors,
        incremental=True,
    )
    assert errors == []


def test_schema_v2_final_mode_rejects_building_index(tmp_path: Path) -> None:
    reports = tmp_path / "workspace" / "reports"
    first = _write_design(reports, "tbrain-first", "media-music", "audio-state", "a")
    batch = {
        "schema_version": 2,
        "status": "building",
        "batch_id": "batch-1",
        "expected_count": 1,
        "task_slugs": ["tbrain-first"],
    }
    errors: list[str] = []
    MODULE.validate_batch_index(
        batch,
        "tbrain-first",
        reports / "tbrain-first",
        first,
        1,
        errors,
    )
    assert any("final mode" in error for error in errors)


def _session_budget() -> dict:
    return {
        "builder": {"runtime": "codex", "model": "builder", "session_id": "builder"},
        "fairness_reviewers": [
            {"runtime": "codex", "model": "reviewer", "session_id": "fairness-1"},
            {"runtime": "codex", "model": "reviewer", "session_id": "fairness-2"},
        ],
        "consolidated_auditor": {
            "runtime": "codex",
            "model": "auditor",
            "session_id": "auditor",
        },
    }


def test_final_session_budget_accepts_six_role_sessions(monkeypatch, tmp_path: Path) -> None:
    budget = _session_budget()
    monkeypatch.setattr(
        MODULE,
        "validate_session_budget_receipt",
        lambda task, report: ([], budget),
    )
    auditor = {"runtime": "codex", "model": "auditor", "session_id": "auditor"}
    errors: list[str] = []

    derived = MODULE.validate_final_session_budget(
        tmp_path / "task",
        tmp_path / "report",
        budget,
        {"solver_session_ids": ["solver-1", "solver-2"]},
        {"manual_review": auditor},
        {"auditor": auditor},
        errors,
    )

    assert errors == []
    assert derived["total_sessions"] == 6
    assert derived["external_sessions"] == 5


def test_final_session_budget_accepts_adaptive_seventh_session(monkeypatch, tmp_path: Path) -> None:
    budget = _session_budget()
    monkeypatch.setattr(
        MODULE,
        "validate_session_budget_receipt",
        lambda task, report: ([], budget),
    )
    auditor = {"runtime": "codex", "model": "auditor", "session_id": "auditor"}
    errors: list[str] = []

    derived = MODULE.validate_final_session_budget(
        tmp_path / "task",
        tmp_path / "report",
        budget,
        {"solver_session_ids": ["solver-1", "solver-2", "solver-3"]},
        {"manual_review": auditor},
        {"auditor": auditor},
        errors,
    )

    assert errors == []
    assert derived["total_sessions"] == 7
    assert derived["external_sessions"] == 6


def test_final_session_budget_rejects_new_zip_reviewer(monkeypatch, tmp_path: Path) -> None:
    budget = _session_budget()
    monkeypatch.setattr(
        MODULE,
        "validate_session_budget_receipt",
        lambda task, report: ([], budget),
    )
    auditor = {"runtime": "codex", "model": "auditor", "session_id": "auditor"}
    errors: list[str] = []

    MODULE.validate_final_session_budget(
        tmp_path / "task",
        tmp_path / "report",
        budget,
        {"solver_session_ids": ["solver-1", "solver-2"]},
        {"manual_review": {**auditor, "session_id": "new-final-reviewer"}},
        {"auditor": auditor},
        errors,
    )

    assert any("reuse the consolidated" in error for error in errors)


def test_luna_thread_alignment_accepts_matching_role_receipts() -> None:
    errors: list[str] = []
    MODULE.validate_luna_thread_alignment(
        _session_budget(),
        {
            "completed_role_session_ids": {
                "fairness_reviewer": ["fairness-1", "fairness-2"],
                "consolidated_auditor": ["auditor"],
            }
        },
        errors,
    )
    assert errors == []


def test_luna_thread_alignment_rejects_unbound_thread_ids() -> None:
    errors: list[str] = []
    MODULE.validate_luna_thread_alignment(
        _session_budget(),
        {
            "completed_role_session_ids": {
                "fairness_reviewer": ["other-1", "other-2"],
                "consolidated_auditor": ["other-auditor"],
            }
        },
        errors,
    )
    assert len(errors) == 2


def _submission_packet(*, include_experience: bool) -> str:
    sections = [
        "# Difficulty Explanation\n\nA systems engineer must reconcile the state transitions. No external data is used.",
        "# Solution Explanation\n\nRepair the transition ordering while preserving replay behavior.",
        "# Verification Explanation\n\nThe behavioral cases cover recovery and preservation.",
    ]
    if include_experience:
        sections.append(
            "# Relevant Experience\n\nExperience with state machines and deterministic recovery testing supports the design."
        )
    sections.extend(
        [
            "# Metadata\n\nCanonical image: Yes.",
            "# Rubrics\n\nAgent preserves replay behavior, +5",
        ]
    )
    return "\n\n".join(sections) + "\n"


def test_submission_requires_relevant_experience(tmp_path: Path) -> None:
    task = tmp_path / "task"
    task.mkdir()
    submission = tmp_path / "SUBMISSION-task.md"
    submission.write_text(_submission_packet(include_experience=False), encoding="utf-8")
    errors: list[str] = []

    MODULE.validate_submission(submission, task, errors)

    assert any("Relevant Experience" in error for error in errors)


def test_submission_accepts_all_four_explanation_fields(tmp_path: Path) -> None:
    task = tmp_path / "task"
    task.mkdir()
    submission = tmp_path / "SUBMISSION-task.md"
    submission.write_text(_submission_packet(include_experience=True), encoding="utf-8")
    errors: list[str] = []

    MODULE.validate_submission(submission, task, errors)

    assert errors == []
