from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "panel_precheck.py"
SPEC = importlib.util.spec_from_file_location("panel_precheck", SCRIPT)
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def make_fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    task = tmp_path / "tbrain-precheck"
    (task / "environment/repo").mkdir(parents=True)
    (task / "tests").mkdir()
    (task / "solution").mkdir()
    (task / "instruction.md").write_text(
        "Select historical authority and reconcile state. "
        "A stated rule holds for every argument. "
        "Where this says nothing the shipped behavior stands. "
        "Expect ordinary and extreme states, in either order.\n"
    )
    (task / "task.toml").write_text('version = "1.0"\n')
    (task / "environment/repo/core.py").write_text("def run():\n    return True\n")
    (task / "environment/repo/parser.py").write_text("def parse(x):\n    return x\n")
    (task / "tests/test_outputs.py").write_text("def test_authority(): pass\ndef test_interaction(): pass\ndef test_parser(): pass\n")
    (task / "solution/solve.sh").write_text(
        "#!/bin/sh\n"
        "# AUTHORITY  core.py  select the authority valid at the action\n"
        "# RECONCILE  core.py  reconcile that authority with action evidence\n"
    )

    report = tmp_path / "reports"
    (report / "wrong-paths").mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "task_slug": task.name,
        "primary_outcome": "historical reconciliation result",
        "obligations": [
            {
                "id": "AUTHORITY",
                "class": "core",
                "contribution": "select authority",
                "authority": {"file": "instruction.md", "anchor": "historical authority"},
                "implementation_sites": ["environment/repo/core.py"],
                "separability": {"standalone_deliverable": False, "joins_before_output": True, "rationale": "changes the decision"},
                "witnesses": {"positive": ["test_outputs.py::test_authority"], "boundary": ["test_outputs.py::test_authority"]},
                "expected_source": "independent_model",
                "discriminating_instance": "an action between two authority versions",
                "wrong_but_plausible": "use the newest authority regardless of the action date",
            },
            {
                "id": "RECONCILE",
                "class": "core",
                "contribution": "reconcile state",
                "authority": {"file": "instruction.md", "anchor": "reconcile state"},
                "implementation_sites": ["environment/repo/core.py"],
                "separability": {"standalone_deliverable": False, "joins_before_output": True, "rationale": "changes the same decision"},
                "witnesses": {"positive": ["test_outputs.py::test_interaction"], "boundary": [], "boundary_not_applicable": "finite state join"},
                "expected_source": "invariant",
                "discriminating_instance": "evidence that contradicts the selected authority",
                "wrong_but_plausible": "trust the evidence and drop the authority",
            },
            {
                "id": "PARSER",
                "class": "support",
                "contribution": "decode input",
                "implementation_complete": True,
                "repair_surface": False,
                "paths": ["environment/repo/parser.py"],
                "smoke_test_ids": ["test_outputs.py::test_parser"],
            },
        ],
        "causal_graph": {"edges": [{"from": "AUTHORITY", "to": "RECONCILE"}, {"from": "RECONCILE", "to": "PRIMARY_OUTCOME"}]},
        "interactions": [{"id": "authority-state", "obligation_ids": ["AUTHORITY", "RECONCILE"], "witness_ids": ["test_outputs.py::test_interaction"], "joins_before_output": True}],
        "closure": {
            "universal_rule": {"file": "instruction.md", "anchor": "holds for every argument"},
            "silence": {"file": "instruction.md", "anchor": "the shipped behavior stands"},
            "coverage_envelope": {"file": "instruction.md", "anchor": "ordinary and extreme states"},
        },
        "determinism": {"seeds": [], "clock_dependence": "none", "network": "none", "order_sensitivity": "none"},
        "reference_selfdescription": "solution/solve.sh",
        "exact_output_requirements": [],
        "verifier_matrix": "verifier-matrix.json",
        "strict_preflight": "preflight.json",
        "wrong_paths": [
            {"id": "latest-only", "kind": "semantic_partial", "obligation_ids": ["AUTHORITY", "RECONCILE"], "receipt": "wrong-paths/latest-only.json"},
            {"id": "bypass", "kind": "harness_bypass", "obligation_ids": [], "receipt": "wrong-paths/bypass.json"},
        ],
    }
    return task, report / "panel-precheck-manifest.json", manifest


def finish_receipts(task: Path, manifest_path: Path, manifest: dict) -> None:
    snapshot = CHECK.tree_hash(task)
    manifest["task_snapshot_sha256"] = snapshot
    unit_ids = ["test_outputs.py::test_authority", "test_outputs.py::test_interaction", "test_outputs.py::test_parser"]
    ctrf = {
        "results": {
            "summary": {"tests": len(unit_ids)},
            "tests": [{"name": test_id, "status": "passed"} for test_id in unit_ids],
        }
    }
    ctrf_path = manifest_path.parent / "oracle-ctrf.json"
    ctrf_path.write_text(json.dumps(ctrf))
    matrix = {
        "schema_version": 1,
        "status": "pass",
        "task_slug": task.name,
        "profile": "cheap_deterministic",
        "platform_visible_unit_count": len(unit_ids),
        "unit_ids": unit_ids,
        "unit_clusters": {test_id: ["core"] for test_id in unit_ids},
        "cross_cluster_unit_ids": [],
        "verifier_shapes": ["behavioral"],
        "non_behavior_test_ids": [],
        "ctrf": {"path": ctrf_path.name, "sha256": hashlib.sha256(ctrf_path.read_bytes()).hexdigest()},
    }
    (manifest_path.parent / "verifier-matrix.json").write_text(json.dumps(matrix))
    checks = [
        {"check": "docker:oracle", "status": "pass"},
        {"check": "docker:nop", "status": "pass"},
        {"check": "docker:noexec-tmp", "status": "pass"},
        {"check": "verifier:unprivileged-candidate", "status": "pass"},
    ]
    preflight = {"status": "pass", "strict": True, "task_snapshot_sha256": snapshot, "checks": checks}
    (manifest_path.parent / "preflight.json").write_text(json.dumps(preflight))
    for wrong_id in ("latest-only", "bypass"):
        receipt = {
            "status": "pass",
            "wrong_path_id": wrong_id,
            "task_snapshot_sha256": snapshot,
            "reward": 0,
            "failed_test_ids": ["test_outputs.py::test_interaction"],
            "passed_control_ids": ["test_outputs.py::test_authority"],
            "command": "run focused verifier",
            "exit_code": 0,
        }
        (manifest_path.parent / "wrong-paths" / f"{wrong_id}.json").write_text(json.dumps(receipt))
    manifest_path.write_text(json.dumps(manifest))


def test_design_only_accepts_connected_bounded_core(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest_path.write_text(json.dumps(manifest))
    result = CHECK.validate(task, manifest_path, full=False)
    assert result["status"] == "pass"
    assert result["semantic_review_required"] is True
    assert set(result["axis_prechecks"].values()) == {"mechanically_ready"}


def test_rejects_disconnected_or_uncoupled_core(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest["causal_graph"]["edges"] = [{"from": "RECONCILE", "to": "PRIMARY_OUTCOME"}]
    manifest["interactions"][0]["obligation_ids"] = ["RECONCILE", "MISSING"]
    manifest_path.write_text(json.dumps(manifest))
    result = CHECK.validate(task, manifest_path, full=False)
    codes = {item["code"] for item in result["blockers"]}
    assert "disconnected_core" in codes
    assert "uncoupled_core" in codes


def test_full_accepts_snapshot_bound_closure(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    finish_receipts(task, manifest_path, manifest)
    result = CHECK.validate(task, manifest_path, full=True)
    assert result["status"] == "pass"
    assert result["axis_prechecks"]["sound_verifier"] == "mechanically_ready"


def test_full_rejects_stale_snapshot_and_surviving_wrong_path(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    finish_receipts(task, manifest_path, manifest)
    receipt_path = manifest_path.parent / "wrong-paths/latest-only.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["reward"] = 1
    receipt_path.write_text(json.dumps(receipt))
    (task / "instruction.md").write_text("changed after receipts\n")
    result = CHECK.validate(task, manifest_path, full=True)
    codes = {item["code"] for item in result["blockers"]}
    assert "stale_snapshot" in codes
    assert "wrong_path_survived" in codes


def test_rejects_incidental_exact_output_and_support_repair_surface(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest["exact_output_requirements"] = [{"id": "NIL-LIST", "domain_required": False, "rationale": "matches Oracle"}]
    manifest["obligations"][2]["repair_surface"] = True
    manifest_path.write_text(json.dumps(manifest))
    result = CHECK.validate(task, manifest_path, full=False)
    codes = {item["code"] for item in result["blockers"]}
    assert "incidental_exact_output" in codes
    assert "support_boundary" in codes


def codes(task: Path, manifest_path: Path, manifest: dict, *, full: bool) -> set[str]:
    manifest_path.write_text(json.dumps(manifest))
    result = CHECK.validate(task, manifest_path, full=full)
    return {blocker["code"] for blocker in result["blockers"]}


def test_recording_the_reference_answers_needs_corroboration(tmp_path: Path) -> None:
    """Oracle=1 proves nothing when the expected values came from the Oracle."""
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest["obligations"][0]["expected_source"] = "oracle_recorded"

    assert "circular_expectation" in codes(task, manifest_path, manifest, full=False)

    manifest["obligations"][0]["oracle_recorded_corroboration"] = "invariant"
    assert "circular_expectation" not in codes(task, manifest_path, manifest, full=False)


def test_a_witness_must_name_the_answer_it_rules_out(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    del manifest["obligations"][0]["wrong_but_plausible"]

    assert "wrong_but_plausible" in codes(task, manifest_path, manifest, full=False)


def test_closure_anchors_must_exist_in_the_cited_file(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest["closure"]["silence"]["anchor"] = "a sentence nobody wrote"
    finish_receipts(task, manifest_path, manifest)

    assert "closure_silence" in codes(task, manifest_path, manifest, full=True)


def test_a_missing_closure_clause_blocks(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    del manifest["closure"]["universal_rule"]

    assert "closure_universal_rule" in codes(task, manifest_path, manifest, full=False)


def test_an_exact_convention_must_cite_a_visible_sentence(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest["exact_output_requirements"] = [
        {"id": "ORDER", "domain_required": True, "rationale": "downstream signed exchange"}
    ]

    assert "uncited_exact_output" in codes(task, manifest_path, manifest, full=False)


def test_network_use_needs_a_rationale(tmp_path: Path) -> None:
    task, manifest_path, manifest = make_fixture(tmp_path)
    manifest["determinism"]["network"] = "localhost fixture server"

    assert "determinism_network" in codes(task, manifest_path, manifest, full=False)


def test_a_unit_no_obligation_claims_is_reported(tmp_path: Path) -> None:
    """Either the manifest forgot the coverage, or the suite grades an unmade promise."""
    task, manifest_path, manifest = make_fixture(tmp_path)
    (task / "tests/test_outputs.py").write_text(
        "def test_authority(): pass\ndef test_interaction(): pass\ndef test_parser(): pass\ndef test_stray(): pass\n"
    )
    finish_receipts(task, manifest_path, manifest)
    matrix_path = manifest_path.parent / "verifier-matrix.json"
    matrix = json.loads(matrix_path.read_text())
    matrix["unit_ids"].append("test_outputs.py::test_stray")
    matrix["unit_clusters"]["test_outputs.py::test_stray"] = ["core"]
    matrix["platform_visible_unit_count"] = len(matrix["unit_ids"])
    ctrf_path = manifest_path.parent / "oracle-ctrf.json"
    ctrf = json.loads(ctrf_path.read_text())
    ctrf["results"]["tests"].append({"name": "test_outputs.py::test_stray", "status": "passed"})
    ctrf["results"]["summary"]["tests"] = len(ctrf["results"]["tests"])
    ctrf_path.write_text(json.dumps(ctrf))
    matrix["ctrf"]["sha256"] = hashlib.sha256(ctrf_path.read_bytes()).hexdigest()
    matrix_path.write_text(json.dumps(matrix))
    manifest["task_snapshot_sha256"] = CHECK.tree_hash(task)

    assert "orphan_unit" in codes(task, manifest_path, manifest, full=True)

    manifest["unclaimed_units_rationale"] = {
        "test_outputs.py::test_stray": "collection smoke test, grades no promise"
    }
    assert "orphan_unit" not in codes(task, manifest_path, manifest, full=True)


def test_the_reference_header_must_account_for_every_core_obligation(tmp_path: Path) -> None:
    """The reference is judged with the instruction alone, so it has to explain itself."""
    task, manifest_path, manifest = make_fixture(tmp_path)
    (task / "solution/solve.sh").write_text("#!/bin/sh\n# AUTHORITY core.py pick the authority\n")
    finish_receipts(task, manifest_path, manifest)

    assert "reference_selfdescription" in codes(task, manifest_path, manifest, full=True)
