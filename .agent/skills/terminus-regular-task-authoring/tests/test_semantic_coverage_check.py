from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "semantic_coverage_check.py"
SPEC = importlib.util.spec_from_file_location("semantic_coverage_check", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def ctrf(test_ids: list[str], failed: str) -> dict:
    return {
        "summary": {"tests": len(test_ids)},
        "tests": [
            {"name": test_id, "status": "failed" if test_id == failed else "passed"}
            for test_id in test_ids
        ]
    }


def fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    task = tmp_path / "workspace" / "tasks" / "tbrain-example"
    report = tmp_path / "workspace" / "reports" / task.name
    (task / "environment").mkdir(parents=True)
    (task / "instruction.md").write_text("Repair every public path.\n", encoding="utf-8")
    (task / "environment" / "app.py").write_text("pass\n", encoding="utf-8")
    test_ids = [
        "t_m1",
        "t_m2",
        "t_m3",
        "t_i1",
        "t_i2",
        "t_surface",
        *[f"t_extra_{index:02d}" for index in range(1, 15)],
    ]
    verifier = report / "verifier-matrix.json"
    oracle_ctrf = report / "oracle-ctrf.json"
    write_json(oracle_ctrf, ctrf(test_ids, failed="unused"))
    unit_clusters = {
        test_id: [f"C{index % 4 + 1}"]
        for index, test_id in enumerate(test_ids)
    }
    unit_clusters["t_i1"] = ["C1", "C2"]
    unit_clusters["t_i2"] = ["C2", "C3"]
    write_json(
        verifier,
        {
            "schema_version": 1,
            "task_slug": task.name,
            "status": "pass",
            "profile": "expensive_stateful",
            "platform_visible_unit_count": len(test_ids),
            "unit_ids": test_ids,
            "unit_clusters": unit_clusters,
            "cross_cluster_unit_ids": ["t_i1", "t_i2"],
            "verifier_shapes": ["scenario", "preservation"],
            "non_behavior_test_ids": [],
            "ctrf": {
                "path": oracle_ctrf.name,
                "sha256": digest(oracle_ctrf),
            },
        },
    )
    mutants = []
    rows = [
        ("u_m1", ["M1"], [], "t_m1"),
        ("u_m2", ["M2"], [], "t_m2"),
        ("u_m3", ["M3"], [], "t_m3"),
        ("u_i1", [], ["I1"], "t_i1"),
        ("u_i2", [], ["I2"], "t_i2"),
    ]
    for mutant_id, mechanisms, interactions, witness in rows:
        patch = report / "semantic-coverage" / f"{mutant_id}.patch"
        matrix = report / "semantic-coverage" / f"{mutant_id}.ctrf.json"
        verifier_log = report / "semantic-coverage" / f"{mutant_id}.verifier.log"
        patch.parent.mkdir(parents=True, exist_ok=True)
        patch.write_text(
            "--- a/environment/app.py\n"
            "+++ b/environment/app.py\n"
            "@@ -1 +1 @@\n"
            "-pass\n"
            f"+pass  # {mutant_id}\n",
            encoding="utf-8",
        )
        write_json(matrix, ctrf(test_ids, witness))
        verifier_log.write_text(f"{mutant_id}: witness failed\n", encoding="utf-8")
        patch_errors: list[str] = []
        mutant_hash = MODULE.materialized_patch_hash(task, patch, mutant_id, patch_errors)
        assert patch_errors == [] and mutant_hash
        mutants.append(
            {
                "id": mutant_id,
                "description": f"Partial fix {mutant_id}",
                "mechanism_ids": mechanisms,
                "interaction_ids": interactions,
                "status": "killed",
                "patch": str(patch.relative_to(report)),
                "patch_sha256": digest(patch),
                "mutant_snapshot_sha256": mutant_hash,
                "ctrf": str(matrix.relative_to(report)),
                "ctrf_sha256": digest(matrix),
                "verifier_log": str(verifier_log.relative_to(report)),
                "verifier_log_sha256": digest(verifier_log),
                "verification_command": "pytest -q",
                "verification_exit_code": 1,
                "expected_fail_test_ids": [witness],
            }
        )
    transcript = report / "semantic-coverage-review.md"
    transcript.write_text("Independent review: mechanisms and mutants are distinct.\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "task_slug": task.name,
        "status": "pass",
        "task_snapshot_sha256": MODULE.tree_hash(task),
        "public_surfaces": [
            {
                "id": "S1",
                "description": "Public repair surface",
                "contract_sources": ["instruction.md"],
                "test_ids": ["t_surface"],
            }
        ],
        "mechanisms": [
            {
                "id": "M1",
                "description": "First",
                "test_ids": ["t_m1", "t_surface", *[f"t_extra_{index:02d}" for index in range(1, 6)]],
                "mutant_ids": ["u_m1"],
            },
            {
                "id": "M2",
                "description": "Second",
                "test_ids": ["t_m2", *[f"t_extra_{index:02d}" for index in range(6, 10)]],
                "mutant_ids": ["u_m2"],
            },
            {
                "id": "M3",
                "description": "Third",
                "test_ids": ["t_m3", *[f"t_extra_{index:02d}" for index in range(10, 13)]],
                "mutant_ids": ["u_m3"],
            },
        ],
        "interactions": [
            {
                "id": "I1",
                "description": "First interaction",
                "mechanism_ids": ["M1", "M2"],
                "test_ids": ["t_i1", "t_extra_13"],
                "mutant_ids": ["u_i1"],
            },
            {
                "id": "I2",
                "description": "Second interaction",
                "mechanism_ids": ["M2", "M3"],
                "test_ids": ["t_i2", "t_extra_14"],
                "mutant_ids": ["u_i2"],
            },
        ],
        "mutants": mutants,
        "review": {
            "status": "pass",
            "runtime": "codex",
            "model": "test-model",
            "session_id": "review-1",
            "transcript": transcript.name,
            "transcript_sha256": digest(transcript),
        },
    }
    manifest_path = report / "semantic-coverage.json"
    write_json(manifest_path, manifest)
    return task, manifest_path, verifier, manifest


def test_valid_advanced_manifest_passes(tmp_path: Path) -> None:
    task, manifest, verifier, _ = fixture(tmp_path)
    assert MODULE.validate(task, manifest, verifier, True) == []


def test_advanced_manifest_accepts_compact_causal_core(tmp_path: Path) -> None:
    task, manifest_path, verifier, manifest = fixture(tmp_path)
    second = manifest["mechanisms"][1]
    removed_mechanism = manifest["mechanisms"].pop()
    second["test_ids"].extend(removed_mechanism["test_ids"])
    kept_interaction = manifest["interactions"][0]
    removed_interaction = manifest["interactions"].pop()
    kept_interaction["test_ids"].extend(removed_interaction["test_ids"])
    manifest["mutants"] = [
        row for row in manifest["mutants"] if row["id"] not in {"u_m3", "u_i2"}
    ]
    write_json(manifest_path, manifest)
    assert MODULE.validate(task, manifest_path, verifier, True) == []


def test_replicated_mechanism_rows_are_rejected(tmp_path: Path) -> None:
    task, manifest_path, verifier, manifest = fixture(tmp_path)
    manifest["mechanisms"][1]["test_ids"] = ["t_m1"]
    write_json(manifest_path, manifest)
    errors = MODULE.validate(task, manifest_path, verifier, True)
    assert any("no discriminating test unique" in error for error in errors)


def test_wholesale_breakage_is_not_a_partial_fix(tmp_path: Path) -> None:
    task, manifest_path, verifier, manifest = fixture(tmp_path)
    mutant = manifest["mutants"][0]
    ctrf_path = manifest_path.parent / mutant["ctrf"]
    test_ids = json.loads(verifier.read_text())["unit_ids"]
    write_json(ctrf_path, {"tests": [{"name": item, "status": "failed"} for item in test_ids]})
    mutant["ctrf_sha256"] = digest(ctrf_path)
    write_json(manifest_path, manifest)
    errors = MODULE.validate(task, manifest_path, verifier, True)
    assert any("both passes and failures" in error for error in errors)


def test_task_change_invalidates_manifest(tmp_path: Path) -> None:
    task, manifest, verifier, _ = fixture(tmp_path)
    (task / "instruction.md").write_text("Changed contract.\n", encoding="utf-8")
    errors = MODULE.validate(task, manifest, verifier, True)
    assert any("task snapshot is stale" in error for error in errors)


def test_every_verifier_unit_requires_a_semantic_node(tmp_path: Path) -> None:
    task, manifest_path, verifier, manifest = fixture(tmp_path)
    manifest["mechanisms"][0]["test_ids"].remove("t_surface")
    write_json(manifest_path, manifest)
    errors = MODULE.validate(task, manifest_path, verifier, True)
    assert any("without a semantic node" in error for error in errors)


def test_mutant_witness_must_exercise_its_target(tmp_path: Path) -> None:
    task, manifest_path, verifier, manifest = fixture(tmp_path)
    mutant = manifest["mutants"][0]
    mutant["expected_fail_test_ids"] = ["t_m2"]
    write_json(manifest_path, manifest)
    errors = MODULE.validate(task, manifest_path, verifier, True)
    assert any("do not exercise every targeted node" in error for error in errors)


def test_mutant_patch_must_materialize_to_recorded_snapshot(tmp_path: Path) -> None:
    task, manifest_path, verifier, manifest = fixture(tmp_path)
    manifest["mutants"][0]["mutant_snapshot_sha256"] = "0" * 64
    write_json(manifest_path, manifest)
    errors = MODULE.validate(task, manifest_path, verifier, True)
    assert any("mutant_snapshot_sha256 mismatch" in error for error in errors)
