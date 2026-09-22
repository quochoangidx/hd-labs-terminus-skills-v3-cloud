#!/usr/bin/env python3
"""Fail-closed deterministic obligation gate for a Terminus 3 task.

Validates authored obligation evidence and existing deterministic receipts: closure
clauses, expected-value provenance, witness discrimination, orphan units in both
directions, restriction enforcement, determinism and wrong-path receipts.

Every profile runs it. Under ``builder_certified`` it carries most of what a review
panel would otherwise be asked to check; it never emits a semantic quality-axis
``None`` verdict, because no script can establish semantic coherence or reference
correctness over a whole domain.

The file name is historical: it predates the gate being used outside the panel flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_architecture_check import validate_matrix  # noqa: E402


AXES = (
    "coherent_contract",
    "correct_reference_solution",
    "protected_ground_truth",
    "sound_verifier",
    "deterministic_execution",
)
CLASSES = {"core", "support", "non_goal"}
# Where a witness's expected value comes from. `oracle_recorded` makes the verifier
# agree with the reference by construction, so it proves nothing on its own and has to
# be paired with an invariant or a differential that the reference cannot influence.
EXPECTED_SOURCES = {
    "independent_model",
    "authority_text",
    "shipped_differential",
    "invariant",
    "oracle_recorded",
}
NON_CIRCULAR_SOURCES = EXPECTED_SOURCES - {"oracle_recorded"}
# The clauses that close the input domain the authority does not name. Without them a
# boundary case has no stated answer, which is where contract findings come from.
CLOSURE_CLAUSES = ("universal_rule", "silence", "coverage_envelope")
VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in VOLATILE_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: object, label: str, errors: list[dict], *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty) or not all(nonempty(item) for item in value):
        errors.append({"axis": "common", "code": "invalid_list", "message": f"{label} must be a {'possibly empty ' if allow_empty else 'non-empty '}list of strings"})
        return []
    result = [str(item) for item in value]
    if len(result) != len(set(result)):
        errors.append({"axis": "common", "code": "duplicate_id", "message": f"{label} must not contain duplicates"})
    return result


def load_object(path: Path, errors: list[dict], label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append({"axis": "common", "code": "invalid_json", "message": f"{label}: {exc}"})
        return {}
    if not isinstance(value, dict):
        errors.append({"axis": "common", "code": "invalid_object", "message": f"{label} root must be an object"})
        return {}
    return value


def resolve_report_file(manifest_path: Path, value: object, label: str, errors: list[dict]) -> Path | None:
    if not nonempty(value):
        errors.append({"axis": "common", "code": "missing_receipt", "message": f"{label} is required"})
        return None
    path = (manifest_path.parent / str(value)).resolve()
    try:
        path.relative_to(manifest_path.parent.resolve())
    except ValueError:
        errors.append({"axis": "common", "code": "escaping_receipt", "message": f"{label} must stay inside the report directory"})
        return None
    if not path.is_file():
        errors.append({"axis": "common", "code": "missing_receipt", "message": f"{label} does not exist: {value}"})
        return None
    return path


def task_file(task_dir: Path, value: object, label: str, axis: str, errors: list[dict], *, must_exist: bool) -> Path | None:
    if not nonempty(value):
        errors.append({"axis": axis, "code": "missing_path", "message": f"{label} must be a non-empty task-relative path"})
        return None
    path = (task_dir / str(value)).resolve()
    try:
        path.relative_to(task_dir.resolve())
    except ValueError:
        errors.append({"axis": axis, "code": "escaping_path", "message": f"{label} escapes the task folder"})
        return None
    if must_exist and not path.is_file():
        errors.append({"axis": axis, "code": "missing_path", "message": f"{label} does not exist: {value}"})
        return None
    return path


def has_path(edges: dict[str, set[str]], start: str, target: str) -> bool:
    pending = [start]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        pending.extend(edges.get(node, ()))
    return False


def validate(task_dir: Path, manifest_path: Path, *, full: bool) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    manifest = load_object(manifest_path, errors, manifest_path.name)
    snapshot = tree_hash(task_dir) if task_dir.is_dir() else None

    if not task_dir.is_dir():
        errors.append({"axis": "common", "code": "missing_task", "message": f"task folder not found: {task_dir}"})
    try:
        manifest_path.relative_to(task_dir.resolve())
    except ValueError:
        pass
    else:
        errors.append({"axis": "protected_ground_truth", "code": "manifest_inside_task", "message": "panel precheck manifest must stay outside the task and submission ZIP"})
    if manifest.get("schema_version") != 1:
        errors.append({"axis": "common", "code": "schema", "message": "schema_version must be 1"})
    if manifest.get("task_slug") != task_dir.name:
        errors.append({"axis": "common", "code": "slug", "message": "task_slug must match the task folder name"})
    if not nonempty(manifest.get("primary_outcome")):
        errors.append({"axis": "coherent_contract", "code": "primary_outcome", "message": "primary_outcome is required"})

    obligations = manifest.get("obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append({"axis": "coherent_contract", "code": "obligations", "message": "obligations must be a non-empty list"})
        obligations = []

    obligation_ids: set[str] = set()
    core_ids: set[str] = set()
    witness_ids: set[str] = set()
    for index, row in enumerate(obligations):
        label = f"obligations[{index}]"
        if not isinstance(row, dict):
            errors.append({"axis": "coherent_contract", "code": "obligation", "message": f"{label} must be an object"})
            continue
        row_id = row.get("id")
        if not nonempty(row_id) or row_id in obligation_ids:
            errors.append({"axis": "coherent_contract", "code": "obligation_id", "message": f"{label}.id must be unique and non-empty"})
            continue
        row_id = str(row_id)
        obligation_ids.add(row_id)
        row_class = row.get("class")
        if row_class not in CLASSES:
            errors.append({"axis": "coherent_contract", "code": "obligation_class", "message": f"{label}.class must be one of {sorted(CLASSES)}"})
            continue
        if not nonempty(row.get("contribution")):
            errors.append({"axis": "coherent_contract", "code": "contribution", "message": f"{label}.contribution is required"})

        if row_class == "core":
            core_ids.add(row_id)
            authority = row.get("authority")
            if not isinstance(authority, dict):
                errors.append({"axis": "coherent_contract", "code": "authority", "message": f"{label}.authority must be an object"})
            else:
                authority_path = task_file(task_dir, authority.get("file"), f"{label}.authority.file", "coherent_contract", errors, must_exist=full)
                anchor = authority.get("anchor")
                if not nonempty(anchor):
                    errors.append({"axis": "coherent_contract", "code": "authority_anchor", "message": f"{label}.authority.anchor is required"})
                elif full and authority_path and authority_path.is_file():
                    try:
                        if str(anchor) not in authority_path.read_text(encoding="utf-8"):
                            errors.append({"axis": "coherent_contract", "code": "authority_anchor", "message": f"{label}.authority.anchor is absent from {authority.get('file')}"})
                    except UnicodeDecodeError:
                        errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"{label}.authority.file must be UTF-8 text"})

            implementation_sites = string_list(row.get("implementation_sites"), f"{label}.implementation_sites", errors)
            if full:
                for path in implementation_sites:
                    task_file(task_dir, path, f"{label}.implementation_sites", "correct_reference_solution", errors, must_exist=True)

            separability = row.get("separability")
            if not isinstance(separability, dict):
                errors.append({"axis": "coherent_contract", "code": "separability", "message": f"{label}.separability must be an object"})
            else:
                if separability.get("standalone_deliverable") is not False:
                    errors.append({"axis": "coherent_contract", "code": "composite_core", "message": f"{label} must not remain a standalone deliverable when removed from the causal core"})
                if separability.get("joins_before_output") is not True:
                    errors.append({"axis": "coherent_contract", "code": "serialization_only_join", "message": f"{label} must join the causal decision before output serialization"})
                if not nonempty(separability.get("rationale")):
                    errors.append({"axis": "coherent_contract", "code": "separability_rationale", "message": f"{label}.separability.rationale is required"})

            witnesses = row.get("witnesses")
            if not isinstance(witnesses, dict):
                errors.append({"axis": "sound_verifier", "code": "witnesses", "message": f"{label}.witnesses must be an object"})
            else:
                positive = string_list(witnesses.get("positive"), f"{label}.witnesses.positive", errors)
                boundary = string_list(witnesses.get("boundary"), f"{label}.witnesses.boundary", errors, allow_empty=True)
                if not boundary and not nonempty(witnesses.get("boundary_not_applicable")):
                    errors.append({"axis": "sound_verifier", "code": "boundary_witness", "message": f"{label} needs boundary witnesses or boundary_not_applicable"})
                witness_ids.update(positive)
                witness_ids.update(boundary)

            # Where the expected values come from decides whether Oracle=1 is evidence
            # or a tautology. A verifier that records the reference's answers agrees
            # with the reference no matter what the reference got wrong.
            expected_source = row.get("expected_source")
            if expected_source not in EXPECTED_SOURCES:
                errors.append({"axis": "correct_reference_solution", "code": "expected_source", "message": f"{label}.expected_source must be one of {sorted(EXPECTED_SOURCES)}"})
            elif expected_source == "oracle_recorded":
                corroboration = row.get("oracle_recorded_corroboration")
                if corroboration not in NON_CIRCULAR_SOURCES - {"authority_text"}:
                    errors.append({
                        "axis": "correct_reference_solution",
                        "code": "circular_expectation",
                        "message": f"{label} records the reference's own answers; pair it with an invariant or shipped differential in oracle_recorded_corroboration",
                    })

            # A witness only discriminates if some plausible wrong implementation gives
            # a different answer on it. Naming that wrong answer is what separates a
            # real witness from a fixture that any shape happens to pass.
            if not nonempty(row.get("discriminating_instance")):
                errors.append({"axis": "sound_verifier", "code": "discriminating_instance", "message": f"{label}.discriminating_instance is required"})
            if not nonempty(row.get("wrong_but_plausible")):
                errors.append({"axis": "sound_verifier", "code": "wrong_but_plausible", "message": f"{label}.wrong_but_plausible must name the answer the witness rules out"})
        elif row_class == "support":
            if row.get("implementation_complete") is not True or row.get("repair_surface") is not False:
                errors.append({"axis": "coherent_contract", "code": "support_boundary", "message": f"{label} support plumbing must be complete and outside the repair surface"})
            support_paths = string_list(row.get("paths"), f"{label}.paths", errors)
            if full:
                for path in support_paths:
                    task_file(task_dir, path, f"{label}.paths", "coherent_contract", errors, must_exist=True)
                smoke = string_list(row.get("smoke_test_ids"), f"{label}.smoke_test_ids", errors)
                witness_ids.update(smoke)

    if not core_ids:
        errors.append({"axis": "coherent_contract", "code": "causal_core", "message": "at least one core obligation is required"})

    graph = manifest.get("causal_graph")
    graph_edges: dict[str, set[str]] = {}
    if not isinstance(graph, dict) or not isinstance(graph.get("edges"), list):
        errors.append({"axis": "coherent_contract", "code": "causal_graph", "message": "causal_graph.edges must be a list"})
    else:
        for index, edge in enumerate(graph["edges"]):
            if not isinstance(edge, dict) or not nonempty(edge.get("from")) or not nonempty(edge.get("to")):
                errors.append({"axis": "coherent_contract", "code": "causal_edge", "message": f"causal_graph.edges[{index}] requires from/to"})
                continue
            source, target = str(edge["from"]), str(edge["to"])
            if source not in core_ids or (target not in core_ids and target != "PRIMARY_OUTCOME"):
                errors.append({"axis": "coherent_contract", "code": "causal_edge", "message": f"causal_graph.edges[{index}] references an unknown core node"})
                continue
            graph_edges.setdefault(source, set()).add(target)
        for row_id in sorted(core_ids):
            if not has_path(graph_edges, row_id, "PRIMARY_OUTCOME"):
                errors.append({"axis": "coherent_contract", "code": "disconnected_core", "message": f"core obligation {row_id} has no causal path to PRIMARY_OUTCOME"})

    interactions = manifest.get("interactions")
    covered_by_interaction: set[str] = set()
    if not isinstance(interactions, list) or not interactions:
        errors.append({"axis": "coherent_contract", "code": "interaction", "message": "at least one genuine core interaction is required"})
        interactions = []
    for index, row in enumerate(interactions):
        label = f"interactions[{index}]"
        if not isinstance(row, dict) or not nonempty(row.get("id")):
            errors.append({"axis": "coherent_contract", "code": "interaction", "message": f"{label} requires a non-empty id"})
            continue
        members = set(string_list(row.get("obligation_ids"), f"{label}.obligation_ids", errors))
        if len(members) < 2 or not members <= core_ids:
            errors.append({"axis": "coherent_contract", "code": "interaction_members", "message": f"{label} must name at least two declared core obligations"})
        covered_by_interaction.update(members)
        interaction_witnesses = string_list(row.get("witness_ids"), f"{label}.witness_ids", errors)
        witness_ids.update(interaction_witnesses)
        if row.get("joins_before_output") is not True:
            errors.append({"axis": "coherent_contract", "code": "serialization_only_interaction", "message": f"{label} must change the causal result before serialization"})
    for row_id in sorted(core_ids - covered_by_interaction):
        errors.append({"axis": "coherent_contract", "code": "uncoupled_core", "message": f"core obligation {row_id} is not part of a declared interaction; move it to support/non-goal or rescope"})

    exact_outputs = manifest.get("exact_output_requirements", [])
    if not isinstance(exact_outputs, list):
        errors.append({"axis": "coherent_contract", "code": "exact_output", "message": "exact_output_requirements must be a list"})
    else:
        for index, row in enumerate(exact_outputs):
            label = f"exact_output_requirements[{index}]"
            if not isinstance(row, dict) or not nonempty(row.get("id")) or row.get("domain_required") is not True or not nonempty(row.get("rationale")):
                errors.append({"axis": "coherent_contract", "code": "incidental_exact_output", "message": f"{label} must identify a domain-required exact convention with rationale"})
                continue
            # An arbitrary convention the verifier pins has to be readable somewhere the
            # candidate can reach. A rationale explains why it exists; it does not tell
            # the candidate what the convention is.
            anchor = row.get("authority_anchor")
            if not isinstance(anchor, dict) or not nonempty(anchor.get("file")) or not nonempty(anchor.get("anchor")):
                errors.append({"axis": "coherent_contract", "code": "uncited_exact_output", "message": f"{label}.authority_anchor must cite the visible sentence that fixes this convention"})
            elif full:
                anchor_path = task_file(task_dir, anchor.get("file"), f"{label}.authority_anchor.file", "coherent_contract", errors, must_exist=True)
                if anchor_path and anchor_path.is_file():
                    try:
                        if str(anchor.get("anchor")) not in anchor_path.read_text(encoding="utf-8"):
                            errors.append({"axis": "coherent_contract", "code": "uncited_exact_output", "message": f"{label}.authority_anchor.anchor is absent from {anchor.get('file')}"})
                    except UnicodeDecodeError:
                        errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"{label}.authority_anchor.file must be UTF-8 text"})

    # Closure: the clauses that decide what happens outside the cases the authority
    # names. Without them every boundary input is an open question, and an open
    # question is a contract finding waiting to be written.
    closure = manifest.get("closure")
    if not isinstance(closure, dict):
        errors.append({"axis": "coherent_contract", "code": "closure", "message": "closure must be an object carrying the universal-rule, silence and coverage-envelope clauses"})
    else:
        for clause in CLOSURE_CLAUSES:
            row = closure.get(clause)
            if not isinstance(row, dict) or not nonempty(row.get("file")) or not nonempty(row.get("anchor")):
                errors.append({"axis": "coherent_contract", "code": f"closure_{clause}", "message": f"closure.{clause} must cite a file and an anchor sentence"})
                continue
            if not full:
                continue
            clause_path = task_file(task_dir, row.get("file"), f"closure.{clause}.file", "coherent_contract", errors, must_exist=True)
            if clause_path and clause_path.is_file():
                try:
                    if str(row.get("anchor")) not in clause_path.read_text(encoding="utf-8"):
                        errors.append({"axis": "coherent_contract", "code": f"closure_{clause}", "message": f"closure.{clause}.anchor is absent from {row.get('file')}"})
                except UnicodeDecodeError:
                    errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"closure.{clause}.file must be UTF-8 text"})
        # Only meaningful when tests drive public helpers directly rather than going
        # through the top-level entry point every time.
        scope = closure.get("entrypoint_scope")
        if scope is not None and (not isinstance(scope, dict) or not nonempty(scope.get("file")) or not nonempty(scope.get("anchor"))):
            errors.append({"axis": "coherent_contract", "code": "closure_entrypoint_scope", "message": "closure.entrypoint_scope, when present, must cite a file and an anchor sentence"})

    # Determinism is a blocking axis in its own right, and nothing else in this
    # manifest would notice a verifier that depends on the clock, the network or the
    # order its tests happen to run in.
    determinism = manifest.get("determinism")
    if not isinstance(determinism, dict):
        errors.append({"axis": "deterministic_execution", "code": "determinism", "message": "determinism must declare seeds, clock_dependence, network and order_sensitivity"})
    else:
        for field in ("clock_dependence", "network", "order_sensitivity"):
            if not nonempty(determinism.get(field)):
                errors.append({"axis": "deterministic_execution", "code": "determinism", "message": f"determinism.{field} is required"})
        if determinism.get("network") not in (None, "none") and not nonempty(determinism.get("network_rationale")):
            errors.append({"axis": "deterministic_execution", "code": "determinism_network", "message": "a verifier that uses the network needs determinism.network_rationale"})

    if full:
        if manifest.get("task_snapshot_sha256") != snapshot:
            errors.append({"axis": "common", "code": "stale_snapshot", "message": "task_snapshot_sha256 does not match the current task"})

        matrix_path = resolve_report_file(manifest_path, manifest.get("verifier_matrix"), "verifier_matrix", errors)
        known_tests: set[str] = set()
        if matrix_path:
            matrix = load_object(matrix_path, errors, "verifier_matrix")
            matrix_errors, derived = validate_matrix(
                matrix,
                matrix_path.parent,
                expected_slug=task_dir.name,
                require_ctrf=True,
            )
            for message in matrix_errors:
                errors.append({"axis": "sound_verifier", "code": "verifier_matrix", "message": message})
            known_tests = set(derived.get("unit_ids", set()))
        unknown = sorted(witness_ids - known_tests)
        if unknown:
            errors.append({"axis": "sound_verifier", "code": "unknown_witness", "message": "witness IDs missing from verifier_matrix.unit_ids: " + ", ".join(unknown)})

        # Sweep the other way too. A test no obligation claims is either coverage the
        # manifest forgot to declare — so nothing is tracking whether it still
        # discriminates — or a promise the contract never made.
        unclaimed_rationale = manifest.get("unclaimed_units_rationale")
        unclaimed_rationale = unclaimed_rationale if isinstance(unclaimed_rationale, dict) else {}
        orphans = sorted(unit for unit in known_tests - witness_ids if not nonempty(unclaimed_rationale.get(unit)))
        if orphans:
            errors.append({
                "axis": "sound_verifier",
                "code": "orphan_unit",
                "message": "verifier units claimed by no obligation: " + ", ".join(orphans)
                + " — map each to an obligation or justify it in unclaimed_units_rationale",
            })

        # The reference is judged against the instruction alone: no authority document,
        # no tests. A header mapping each contract topic to its change is what keeps a
        # correct reference from reading as unverifiable.
        selfdesc = manifest.get("reference_selfdescription")
        if not nonempty(selfdesc):
            errors.append({"axis": "correct_reference_solution", "code": "reference_selfdescription", "message": "reference_selfdescription must point at the solution file carrying the contract-to-change header"})
        else:
            selfdesc_path = task_file(task_dir, selfdesc, "reference_selfdescription", "correct_reference_solution", errors, must_exist=True)
            if selfdesc_path and selfdesc_path.is_file():
                try:
                    selfdesc_text = selfdesc_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    errors.append({"axis": "correct_reference_solution", "code": "reference_selfdescription", "message": "reference_selfdescription must be UTF-8 text"})
                else:
                    missing_topics = sorted(
                        row_id for row_id in core_ids
                        if row_id.lower() not in selfdesc_text.lower()
                        and not any(
                            nonempty(obligation.get("selfdescription_phrase"))
                            and str(obligation["selfdescription_phrase"]).lower() in selfdesc_text.lower()
                            for obligation in obligations
                            if isinstance(obligation, dict) and obligation.get("id") == row_id
                        )
                    )
                    if missing_topics:
                        errors.append({
                            "axis": "correct_reference_solution",
                            "code": "reference_selfdescription",
                            "message": "the reference header does not account for core obligations: " + ", ".join(missing_topics)
                            + " — name each one, or give it a selfdescription_phrase matching the wording used",
                        })

        preflight_path = resolve_report_file(manifest_path, manifest.get("strict_preflight"), "strict_preflight", errors)
        if preflight_path:
            preflight = load_object(preflight_path, errors, "strict_preflight")
            if preflight.get("status") != "pass" or preflight.get("strict") is not True:
                errors.append({"axis": "protected_ground_truth", "code": "strict_preflight", "message": "strict preflight must pass"})
            if preflight.get("task_snapshot_sha256") != snapshot:
                errors.append({"axis": "common", "code": "stale_preflight", "message": "strict preflight is not bound to the current task snapshot"})
            checks = {item.get("check"): item.get("status") for item in preflight.get("checks", []) if isinstance(item, dict)}
            for check in ("docker:oracle", "docker:nop", "docker:noexec-tmp", "verifier:unprivileged-candidate"):
                if checks.get(check) != "pass":
                    errors.append({"axis": "protected_ground_truth" if check.startswith("verifier:") else "sound_verifier", "code": "preflight_check", "message": f"strict preflight lacks passing {check}"})

        wrong_paths = manifest.get("wrong_paths")
        if not isinstance(wrong_paths, list) or not wrong_paths:
            errors.append({"axis": "sound_verifier", "code": "wrong_paths", "message": "full precheck requires minimal wrong-path evidence"})
            wrong_paths = []
        wrong_covered: set[str] = set()
        has_harness = False
        for index, row in enumerate(wrong_paths):
            label = f"wrong_paths[{index}]"
            if not isinstance(row, dict) or not nonempty(row.get("id")):
                errors.append({"axis": "sound_verifier", "code": "wrong_path", "message": f"{label} requires an id"})
                continue
            members = set(string_list(row.get("obligation_ids"), f"{label}.obligation_ids", errors, allow_empty=row.get("kind") == "harness_bypass"))
            if not members <= core_ids:
                errors.append({"axis": "sound_verifier", "code": "wrong_path_members", "message": f"{label} references unknown core obligations"})
            wrong_covered.update(members)
            has_harness = has_harness or row.get("kind") == "harness_bypass"
            receipt_path = resolve_report_file(manifest_path, row.get("receipt"), f"{label}.receipt", errors)
            if not receipt_path:
                continue
            receipt = load_object(receipt_path, errors, f"{label}.receipt")
            if receipt.get("status") != "pass" or receipt.get("wrong_path_id") != row.get("id"):
                errors.append({"axis": "sound_verifier", "code": "wrong_path_receipt", "message": f"{label} receipt identity/status mismatch"})
            reward = receipt.get("reward")
            if (
                receipt.get("task_snapshot_sha256") != snapshot
                or isinstance(reward, bool)
                or not isinstance(reward, (int, float))
                or reward != 0
            ):
                errors.append({"axis": "sound_verifier", "code": "wrong_path_survived", "message": f"{label} must be snapshot-bound and receive reward 0"})
            failed_ids = set(string_list(receipt.get("failed_test_ids"), f"{label}.receipt.failed_test_ids", errors))
            passed_ids = set(string_list(receipt.get("passed_control_ids"), f"{label}.receipt.passed_control_ids", errors))
            unknown_receipt_ids = sorted((failed_ids | passed_ids) - known_tests)
            if unknown_receipt_ids:
                errors.append({"axis": "sound_verifier", "code": "unknown_wrong_path_test", "message": f"{label} receipt names tests absent from verifier_matrix: " + ", ".join(unknown_receipt_ids)})
            exit_code = receipt.get("exit_code")
            if not nonempty(receipt.get("command")) or isinstance(exit_code, bool) or not isinstance(exit_code, int):
                errors.append({"axis": "sound_verifier", "code": "wrong_path_provenance", "message": f"{label} receipt requires command and exit_code"})
        for row_id in sorted(core_ids - wrong_covered):
            errors.append({"axis": "sound_verifier", "code": "undiscriminated_core", "message": f"core obligation {row_id} is not covered by a wrong path"})
        if not has_harness:
            errors.append({"axis": "protected_ground_truth", "code": "harness_bypass", "message": "full precheck requires one harness_bypass wrong-path receipt"})

    blocked_axes = {error["axis"] for error in errors}
    if "common" in blocked_axes:
        blocked_axes.update(AXES)
    axis_prechecks = {axis: ("blocked" if axis in blocked_axes else "mechanically_ready") for axis in AXES}
    result = {
        "schema_version": 1,
        "mode": "full" if full else "design_only",
        "task_slug": task_dir.name,
        "task_snapshot_sha256": snapshot,
        "status": "fail" if errors else "pass",
        "deterministic_panel_precheck": "fail" if errors else "pass",
        "axis_prechecks": axis_prechecks,
        "semantic_review_required": True,
        "blockers": errors,
        "warnings": warnings,
        "review_questions": [
            "Does the declared causal graph match the actual domain semantics?",
            "Could another contract-correct reference implementation be rejected?",
            "Are any important semantic branches absent from the authored partition inventory?",
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--design-only", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = validate(args.task_dir.resolve(), args.manifest.resolve(), full=args.full)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
