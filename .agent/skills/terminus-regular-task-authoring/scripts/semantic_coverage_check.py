#!/usr/bin/env python3
"""Validate frozen semantic-mechanism and mutation coverage evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_architecture_check import validate_matrix  # noqa: E402


VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in VOLATILE_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        digest.update(rel.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_object(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name}: root must be an object")
        return {}
    return value


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_set(value: object, label: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not value or not all(nonempty(item) for item in value):
        errors.append(f"{label} must be a non-empty list of strings")
        return set()
    result = {str(item) for item in value}
    if len(result) != len(value):
        errors.append(f"{label} must not contain duplicates")
    return result


def resolve_evidence(report_dir: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} is required")
        return None
    path = (report_dir / str(value)).resolve()
    try:
        path.relative_to(report_dir.resolve())
    except ValueError:
        errors.append(f"{label} must stay inside the report directory")
        return None
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"{label} is missing or empty")
        return None
    return path


def ctrf_matrix(path: Path, label: str, errors: list[str]) -> tuple[set[str], set[str]]:
    data = load_object(path, errors)
    tests = data.get("tests")
    if not isinstance(tests, list):
        results = data.get("results")
        tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list) or not tests:
        errors.append(f"{label}: CTRF tests must be a non-empty list")
        return set(), set()
    passed: set[str] = set()
    failed: set[str] = set()
    seen: set[str] = set()
    for index, item in enumerate(tests):
        if not isinstance(item, dict):
            errors.append(f"{label}: tests[{index}] must be an object")
            continue
        test_id = item.get("name") or item.get("testId")
        status = str(item.get("status", "")).lower()
        if not nonempty(test_id):
            errors.append(f"{label}: tests[{index}] has no name/testId")
            continue
        test_id = str(test_id)
        if test_id in seen:
            errors.append(f"{label}: duplicate CTRF test ID {test_id}")
            continue
        seen.add(test_id)
        if status in {"pass", "passed"}:
            passed.add(test_id)
        elif status in {"fail", "failed"}:
            failed.add(test_id)
        else:
            errors.append(f"{label}: unsupported CTRF status {status!r}")
    return passed, failed


def materialized_patch_hash(
    task_dir: Path,
    patch: Path,
    label: str,
    errors: list[str],
) -> str | None:
    with tempfile.TemporaryDirectory(prefix="semantic-mutant-") as temp:
        mutant = Path(temp) / task_dir.name
        shutil.copytree(task_dir, mutant)
        try:
            applied = subprocess.run(
                ["patch", "-p1", "--batch", "-i", str(patch)],
                cwd=mutant,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{label}: could not materialize mutant patch: {exc}")
            return None
        if applied.returncode != 0:
            detail = " ".join((applied.stdout + " " + applied.stderr).split())[:500]
            errors.append(f"{label}: mutant patch does not apply cleanly: {detail}")
            return None
        return tree_hash(mutant)


def validate(task_dir: Path, manifest_path: Path, verifier_path: Path, advanced: bool) -> list[str]:
    errors: list[str] = []
    task_dir = task_dir.resolve()
    manifest_path = manifest_path.resolve()
    report_dir = manifest_path.parent
    manifest = load_object(manifest_path, errors)
    verifier = load_object(verifier_path.resolve(), errors)
    if manifest.get("schema_version") != 1:
        errors.append("semantic-coverage.json: schema_version must be 1")
    if manifest.get("task_slug") != task_dir.name:
        errors.append("semantic-coverage.json: task_slug mismatch")
    if manifest.get("status") != "pass":
        errors.append("semantic-coverage.json: status must be pass")
    if manifest.get("task_snapshot_sha256") != tree_hash(task_dir):
        errors.append("semantic-coverage.json: task snapshot is stale")

    architecture_errors, architecture = validate_matrix(
        verifier,
        verifier_path.resolve().parent,
        expected_slug=task_dir.name,
        require_ctrf=True,
    )
    errors.extend(architecture_errors)
    known_tests = architecture.get("unit_ids", set())

    mechanisms = manifest.get("mechanisms")
    minimum_mechanisms = 3 if advanced else 2
    if not isinstance(mechanisms, list) or len(mechanisms) < minimum_mechanisms:
        errors.append(f"semantic-coverage.json: requires at least {minimum_mechanisms} mechanisms")
        mechanisms = []
    interactions = manifest.get("interactions")
    minimum_interactions = 2 if advanced else 1
    if not isinstance(interactions, list) or len(interactions) < minimum_interactions:
        errors.append(f"semantic-coverage.json: requires at least {minimum_interactions} interactions")
        interactions = []
    surfaces = manifest.get("public_surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("semantic-coverage.json: public_surfaces must be non-empty")
        surfaces = []
    mutants = manifest.get("mutants")
    if not isinstance(mutants, list) or not mutants:
        errors.append("semantic-coverage.json: mutants must be non-empty")
        mutants = []

    mechanism_ids: set[str] = set()
    mechanism_tests: dict[str, set[str]] = {}
    mechanism_mutants: dict[str, set[str]] = {}
    for index, item in enumerate(mechanisms):
        label = f"mechanisms[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        item_id = item.get("id")
        if not nonempty(item_id) or item_id in mechanism_ids:
            errors.append(f"{label}.id must be unique and non-empty")
            continue
        item_id = str(item_id)
        mechanism_ids.add(item_id)
        if not nonempty(item.get("description")):
            errors.append(f"{label}.description is required")
        mechanism_tests[item_id] = string_set(item.get("test_ids"), f"{label}.test_ids", errors)
        mechanism_mutants[item_id] = string_set(item.get("mutant_ids"), f"{label}.mutant_ids", errors)

    interaction_ids: set[str] = set()
    interaction_tests: dict[str, set[str]] = {}
    interaction_mutants: dict[str, set[str]] = {}
    for index, item in enumerate(interactions):
        label = f"interactions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        item_id = item.get("id")
        if not nonempty(item_id) or item_id in interaction_ids:
            errors.append(f"{label}.id must be unique and non-empty")
            continue
        item_id = str(item_id)
        interaction_ids.add(item_id)
        if not nonempty(item.get("description")):
            errors.append(f"{label}.description is required")
        members = string_set(item.get("mechanism_ids"), f"{label}.mechanism_ids", errors)
        if len(members) < 2 or not members <= mechanism_ids:
            errors.append(f"{label}.mechanism_ids must name at least two declared mechanisms")
        interaction_tests[item_id] = string_set(item.get("test_ids"), f"{label}.test_ids", errors)
        interaction_mutants[item_id] = string_set(item.get("mutant_ids"), f"{label}.mutant_ids", errors)

    all_declared_tests = set().union(*mechanism_tests.values(), *interaction_tests.values()) if (mechanism_tests or interaction_tests) else set()
    unknown_tests = all_declared_tests - known_tests
    if unknown_tests:
        errors.append("semantic-coverage.json: unknown verifier test IDs: " + ", ".join(sorted(unknown_tests)))
    unmapped_tests = known_tests - all_declared_tests
    if unmapped_tests:
        errors.append(
            "semantic-coverage.json: verifier units without a semantic node: "
            + ", ".join(sorted(unmapped_tests))
        )
    for item_id, tests in mechanism_tests.items():
        other_tests = set().union(*(value for key, value in mechanism_tests.items() if key != item_id))
        if tests and not tests - other_tests:
            errors.append(f"mechanism {item_id} has no discriminating test unique to that mechanism")

    surface_ids: set[str] = set()
    for index, item in enumerate(surfaces):
        label = f"public_surfaces[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        item_id = item.get("id")
        if not nonempty(item_id) or item_id in surface_ids:
            errors.append(f"{label}.id must be unique and non-empty")
            continue
        surface_ids.add(str(item_id))
        if not nonempty(item.get("description")):
            errors.append(f"{label}.description is required")
        sources = string_set(item.get("contract_sources"), f"{label}.contract_sources", errors)
        for source in sources:
            if not (task_dir / source).is_file():
                errors.append(f"{label}: contract source not found in task: {source}")
        tests = string_set(item.get("test_ids"), f"{label}.test_ids", errors)
        if not tests <= known_tests:
            errors.append(f"{label}: contains unknown verifier test IDs")

    mutant_ids: set[str] = set()
    mutant_targets: dict[str, tuple[set[str], set[str]]] = {}
    for index, item in enumerate(mutants):
        label = f"mutants[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        item_id = item.get("id")
        if not nonempty(item_id) or item_id in mutant_ids:
            errors.append(f"{label}.id must be unique and non-empty")
            continue
        item_id = str(item_id)
        mutant_ids.add(item_id)
        if item.get("status") != "killed" or not nonempty(item.get("description")):
            errors.append(f"{label} must describe a killed plausible partial fix")
        target_mechanisms = set(item.get("mechanism_ids", [])) if isinstance(item.get("mechanism_ids"), list) else set()
        target_interactions = set(item.get("interaction_ids", [])) if isinstance(item.get("interaction_ids"), list) else set()
        if not target_mechanisms <= mechanism_ids or not target_interactions <= interaction_ids:
            errors.append(f"{label} references unknown mechanism/interaction IDs")
        if not target_mechanisms and not target_interactions:
            errors.append(f"{label} must target a mechanism or interaction")
        mutant_targets[item_id] = (target_mechanisms, target_interactions)
        patch = resolve_evidence(report_dir, item.get("patch"), f"{label}.patch", errors)
        ctrf = resolve_evidence(report_dir, item.get("ctrf"), f"{label}.ctrf", errors)
        verifier_log = resolve_evidence(
            report_dir,
            item.get("verifier_log"),
            f"{label}.verifier_log",
            errors,
        )
        if patch and item.get("patch_sha256") != sha256(patch):
            errors.append(f"{label}.patch_sha256 mismatch")
        if patch:
            mutant_hash = materialized_patch_hash(task_dir, patch, label, errors)
            if mutant_hash and item.get("mutant_snapshot_sha256") != mutant_hash:
                errors.append(f"{label}.mutant_snapshot_sha256 mismatch")
        if ctrf and item.get("ctrf_sha256") != sha256(ctrf):
            errors.append(f"{label}.ctrf_sha256 mismatch")
        if verifier_log and item.get("verifier_log_sha256") != sha256(verifier_log):
            errors.append(f"{label}.verifier_log_sha256 mismatch")
        if not nonempty(item.get("verification_command")):
            errors.append(f"{label}.verification_command is required")
        exit_code = item.get("verification_exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code == 0:
            errors.append(f"{label}.verification_exit_code must be a non-zero integer")
        expected = string_set(item.get("expected_fail_test_ids"), f"{label}.expected_fail_test_ids", errors)
        if not expected <= known_tests:
            errors.append(f"{label} contains unknown expected fail test IDs")
        target_test_sets = [
            mechanism_tests[target]
            for target in target_mechanisms
            if target in mechanism_tests
        ] + [
            interaction_tests[target]
            for target in target_interactions
            if target in interaction_tests
        ]
        for target_tests in target_test_sets:
            if not expected & target_tests:
                errors.append(f"{label}: expected witnesses do not exercise every targeted node")
        if ctrf:
            passed, failed = ctrf_matrix(ctrf, label, errors)
            if not passed or not failed:
                errors.append(f"{label}: mutant must be a partial fix with both passes and failures")
            if not expected <= failed:
                errors.append(f"{label}: CTRF did not kill every expected witness test")
            if not (passed | failed) <= known_tests:
                errors.append(f"{label}: CTRF contains IDs outside verifier-matrix.json")

    for mechanism_id, claimed in mechanism_mutants.items():
        for mutant_id in claimed - mutant_ids:
            errors.append(f"mechanism {mechanism_id} references unknown mutant {mutant_id}")
        if not any(mutant_targets.get(mid) == ({mechanism_id}, set()) for mid in claimed):
            errors.append(f"mechanism {mechanism_id} needs a dedicated executable mutant")
    for interaction_id, claimed in interaction_mutants.items():
        for mutant_id in claimed - mutant_ids:
            errors.append(f"interaction {interaction_id} references unknown mutant {mutant_id}")
        if not any(
            mutant_targets.get(mid) == (set(), {interaction_id})
            for mid in claimed
        ):
            errors.append(f"interaction {interaction_id} needs a dedicated executable mutant")

    review = manifest.get("review")
    if not isinstance(review, dict) or review.get("status") != "pass":
        errors.append("semantic-coverage.json: independent review status must be pass")
    else:
        for field in ("runtime", "model", "session_id"):
            if not nonempty(review.get(field)):
                errors.append(f"semantic-coverage.json: review.{field} is required")
        transcript = resolve_evidence(report_dir, review.get("transcript"), "review.transcript", errors)
        if transcript and review.get("transcript_sha256") != sha256(transcript):
            errors.append("semantic-coverage.json: review transcript hash mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--advanced-plus", action="store_true")
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("verifier_matrix", type=Path)
    args = parser.parse_args()
    errors = validate(args.task_dir, args.manifest, args.verifier_matrix, args.advanced_plus)
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"PASS: {args.task_dir.name} semantic coverage is frozen and mutation-backed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
