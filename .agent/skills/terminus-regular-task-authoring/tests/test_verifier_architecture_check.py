from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verifier_architecture_check.py"
SPEC = importlib.util.spec_from_file_location("verifier_architecture_check", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def plan(unit_count: int = 20) -> dict:
    return {
        "candidate": {
            "public_surfaces": [{"id": "cli"}, {"id": "report"}],
            "verifier_architecture": {
                "schema_version": 1,
                "status": "pass",
                "profile": "expensive_stateful",
                "planned_platform_visible_unit_count": unit_count,
                "semantic_clusters": [
                    {"id": f"C{index}", "description": f"Cluster {index}", "planned_unit_count": 5}
                    for index in range(1, 5)
                ],
                "public_surface_ids": ["cli", "report"],
                "public_surface_cluster_ids": {"cli": ["C1", "C2"], "report": ["C3", "C4"]},
                "cross_cluster_scenarios": [
                    {
                        "id": "X1",
                        "cluster_ids": ["C1", "C2"],
                        "discriminating_scenario": "State transition through the CLI",
                    },
                    {
                        "id": "X2",
                        "cluster_ids": ["C3", "C4"],
                        "discriminating_scenario": "Report preserves derived state",
                    },
                ],
                "verifier_shapes": ["scenario", "preservation"],
                "platform_visibility_strategy": "Parameterize each scenario as a distinct CTRF unit.",
                "nop_discrimination_strategy": "Every cluster contains a baseline-failing witness.",
            }
        }
    }


def matrix(tmp_path: Path, unit_count: int = 20) -> tuple[dict, Path]:
    unit_ids = [f"test_{index:02d}" for index in range(unit_count)]
    clusters = {test_id: [f"C{index % 4 + 1}"] for index, test_id in enumerate(unit_ids)}
    if unit_count >= 2:
        clusters[unit_ids[0]] = ["C1", "C2"]
        clusters[unit_ids[1]] = ["C3", "C4"]
    ctrf = tmp_path / "oracle-ctrf.json"
    write_json(
        ctrf,
        {
            "summary": {"tests": unit_count},
            "tests": [{"name": test_id, "status": "passed"} for test_id in unit_ids],
        },
    )
    data = {
        "schema_version": 1,
        "task_slug": "tbrain-example",
        "status": "pass",
        "profile": "expensive_stateful",
        "platform_visible_unit_count": unit_count,
        "unit_ids": unit_ids,
        "unit_clusters": clusters,
        "cross_cluster_unit_ids": unit_ids[:2],
        "verifier_shapes": ["scenario", "preservation"],
        "non_behavior_test_ids": [],
        "ctrf": {
            "path": ctrf.name,
            "sha256": hashlib.sha256(ctrf.read_bytes()).hexdigest(),
        },
    }
    return data, ctrf


def test_mining_plan_accepts_complete_stateful_budget() -> None:
    assert MODULE.validate_plan(plan()) == []


def test_mining_plan_accepts_nine_units_without_padding() -> None:
    assert MODULE.validate_plan(plan(unit_count=9)) == []


def test_final_matrix_accepts_twenty_visible_units(tmp_path: Path) -> None:
    data, _ = matrix(tmp_path)
    errors, derived = MODULE.validate_matrix(
        data,
        tmp_path,
        expected_slug="tbrain-example",
        require_ctrf=True,
    )
    assert errors == []
    assert len(derived["unit_ids"]) == 20


def test_final_matrix_accepts_fourteen_visible_units(tmp_path: Path) -> None:
    data, _ = matrix(tmp_path, unit_count=14)
    errors, _ = MODULE.validate_matrix(
        data,
        tmp_path,
        expected_slug="tbrain-example",
        require_ctrf=True,
    )
    assert errors == []


def test_compact_single_cluster_and_shape_are_not_blockers(tmp_path: Path) -> None:
    data, _ = matrix(tmp_path, unit_count=1)
    data["cross_cluster_unit_ids"] = []
    data["verifier_shapes"] = ["scenario"]
    errors, derived = MODULE.validate_matrix(data, tmp_path)
    assert errors == []
    assert derived["diagnostics"] == {
        "unit_count": 1, "cluster_count": 1, "cross_cluster_unit_count": 0,
    }


def test_compact_plan_preserves_surface_mapping() -> None:
    data = plan(1)
    arch = data["candidate"]["verifier_architecture"]
    arch["semantic_clusters"] = [{"id": "C1", "description": "Outcome", "planned_unit_count": 1}]
    arch["public_surface_cluster_ids"] = {"cli": ["C1"], "report": ["C1"]}
    arch["cross_cluster_scenarios"] = []
    arch["verifier_shapes"] = ["scenario"]
    assert MODULE.validate_plan(data) == []
    arch["public_surface_cluster_ids"].pop("report")
    assert MODULE.validate_plan(data)


def test_invalid_inventory_still_blocks(tmp_path: Path) -> None:
    data, _ = matrix(tmp_path, unit_count=1)
    data["unit_ids"].append(data["unit_ids"][0])
    errors, _ = MODULE.validate_matrix(data, tmp_path)
    assert any("duplicates" in error for error in errors)


def test_cross_cluster_claim_requires_actual_memberships(tmp_path: Path) -> None:
    data, _ = matrix(tmp_path, unit_count=1)
    errors, _ = MODULE.validate_matrix(data, tmp_path)
    assert any("fewer than two clusters" in error for error in errors)


def test_zero_unit_plan_is_invalid() -> None:
    assert MODULE.validate_plan(plan(0))


def test_ctrf_ids_must_match_declared_platform_units(tmp_path: Path) -> None:
    data, ctrf = matrix(tmp_path)
    payload = json.loads(ctrf.read_text(encoding="utf-8"))
    payload["tests"][-1]["name"] = "unexpected_test"
    write_json(ctrf, payload)
    data["ctrf"]["sha256"] = hashlib.sha256(ctrf.read_bytes()).hexdigest()
    errors, _ = MODULE.validate_matrix(data, tmp_path, require_ctrf=True)
    assert any("CTRF test IDs must exactly equal" in error for error in errors)
