#!/usr/bin/env python3
"""Fail-closed handover gate for autonomous task batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Callable


EVIDENCE_FILES = {
    "category": "category-screen.json",
    "design": "design-signature.json",
    "preflight": "preflight.json",
    "probe": "probe-verdict.json",
    "sufficiency": "instruction-sufficiency.json",
    "verifier": "verifier-matrix.json",
}
SIGNATURE_AXES = {
    "work_surface",
    "interaction",
    "input_surface",
    "oracle_type",
    "verifier_type",
    "failure_mode",
}
TAXONOMY = {
    "Science": {"Biology", "Chemistry", "Physics", "Earth", "Robotics", "Math", "Linguistics"},
    "Software": {"Algorithms", "Systems", "Databases", "Data engineering", "Frontend", "Languages"},
    "ML": {"Training", "Inference", "Evaluation", "Kernels"},
    "Operations": {"Finance", "Logistics", "Supply chain", "Claims", "Compliance", "Marketing"},
    "Security": {"Cryptography", "Reverse engineering", "Forensics", "AppSec"},
    "Hardware": {"CAD", "RTL"},
    "Media": {"Music", "Design"},
}
PROBE_PROFILES = {
    "codex": ("gpt-5.6",),
    "claude-code": ("opus-5", "opus 5", "claude-opus-5"),
}
VALID_PROBE_RUNNERS = {"codex-subagent", "claude-agent"}
FORBIDDEN_PROBE_COMMAND_TOKENS = {"stb ", "terminus-2", "@openai/", "@anthropic/"}
VOLATILE_HASH_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
SANITIZED_HASH_DIRS = VOLATILE_HASH_DIRS | {"solution", "tests"}
RUBRIC_SUFFIXES = ("_rubric.md", "_rubric.txt", "-rubric.md", "-rubric.txt")


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name}: root must be an object")
        return {}
    return value


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path, *, sanitized: bool) -> str:
    digest = hashlib.sha256()
    excluded_dirs = SANITIZED_HASH_DIRS if sanitized else VOLATILE_HASH_DIRS
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in excluded_dirs for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        name = path.name
        if sanitized and (
            name.startswith("rubric")
            or name.endswith(RUBRIC_SUFFIXES)
            or name.endswith(".zip")
        ):
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def file_hash_map(root: Path, *, sanitized: bool) -> dict[str, str]:
    """Return the same file set as tree_hash, keyed by relative POSIX path."""
    files: dict[str, str] = {}
    excluded_dirs = SANITIZED_HASH_DIRS if sanitized else VOLATILE_HASH_DIRS
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in excluded_dirs for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        name = path.name
        if sanitized and (
            name.startswith("rubric")
            or name.endswith(RUBRIC_SUFFIXES)
            or name.endswith(".zip")
        ):
            continue
        files[rel.as_posix()] = sha256(path)
    return files


def recompute_solve_diff(run_dir: Path) -> bytes:
    proc = subprocess.run(
        [
            "diff",
            "-ruN",
            "--exclude",
            ".git",
            str(run_dir / "baseline"),
            str(run_dir / "solve"),
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode not in {0, 1}:
        raise OSError(proc.stderr.decode("utf-8", errors="replace").strip())
    return proc.stdout


def matrix_from_ctrf(path: Path, run_name: str, errors: list[str]) -> dict:
    data = load_json(path, errors)
    tests = data.get("tests")
    if not isinstance(tests, list):
        results = data.get("results")
        tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list) or not tests:
        errors.append(f"{run_name}/verification-ctrf.json: tests must be a non-empty list")
        return {}
    passed: list[str] = []
    failed: list[str] = []
    for index, item in enumerate(tests):
        if not isinstance(item, dict):
            errors.append(
                f"{run_name}/verification-ctrf.json: tests[{index}] must be an object"
            )
            continue
        case_id = item.get("name") or item.get("testId")
        status = str(item.get("status", "")).strip().lower()
        if not nonempty(case_id):
            errors.append(
                f"{run_name}/verification-ctrf.json: tests[{index}] has no name/testId"
            )
        elif status in {"passed", "pass"}:
            passed.append(str(case_id))
        elif status in {"failed", "fail"}:
            failed.append(str(case_id))
        else:
            errors.append(
                f"{run_name}/verification-ctrf.json: tests[{index}] has unsupported status "
                f"{status!r}; skipped/unknown units cannot count as semantic evidence"
            )
    if len(set(passed + failed)) != len(passed) + len(failed):
        errors.append(f"{run_name}/verification-ctrf.json: test names must be unique")
    return {
        "total_units": len(passed) + len(failed),
        "passed_case_ids": sorted(passed),
        "failed_case_ids": sorted(failed),
    }


def run_trusted_nop_verifier(run_dir: Path) -> dict:
    """Rerun the verifier with the fixed local NOP agent and derive its outcome."""
    stb = shutil.which("stb")
    if not stb:
        raise RuntimeError("stb executable is unavailable for trusted local NOP verification")
    verify = (run_dir / "verify").resolve()
    if not verify.is_dir():
        raise RuntimeError(f"verification task is missing: {verify}")
    with tempfile.TemporaryDirectory(prefix="batch-handover-nop-") as temp:
        jobs_dir = Path(temp) / "jobs"
        command = [
            stb,
            "harbor",
            "run",
            "--force-build",
            "-a",
            "nop",
            "-p",
            str(verify),
            "-o",
            str(jobs_dir),
            "-n",
            "1",
            "-y",
        ]
        proc = subprocess.run(
            command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        log = proc.stdout + proc.stderr
        (run_dir / "handover-verifier.log").write_text(log, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(
                f"trusted NOP rerun exited {proc.returncode}; "
                f"see {run_dir / 'handover-verifier.log'}"
            )
        trial_results: list[tuple[Path, dict]] = []
        for path in jobs_dir.rglob("result.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and isinstance(data.get("verifier_result"), dict):
                trial_results.append((path, data))
        if len(trial_results) != 1:
            raise RuntimeError(
                "trusted NOP rerun did not produce exactly one trial result "
                f"(exit={proc.returncode}, trials={len(trial_results)}); "
                f"see {run_dir / 'handover-verifier.log'}"
            )
        result_path, result_data = trial_results[0]
        rewards = result_data["verifier_result"].get("rewards")
        reward = rewards.get("reward") if isinstance(rewards, dict) else None
        if not isinstance(reward, (int, float)) or isinstance(reward, bool):
            raise RuntimeError("trusted NOP rerun result has no numeric reward")
        ctrf_path = result_path.parent / "verifier" / "ctrf.json"
        ctrf_errors: list[str] = []
        matrix = matrix_from_ctrf(ctrf_path, run_dir.name, ctrf_errors)
        if ctrf_errors or not matrix:
            raise RuntimeError(
                "trusted NOP rerun CTRF is invalid: " + "; ".join(ctrf_errors)
            )
        kept_ctrf = run_dir / "handover-verification-ctrf.json"
        shutil.copy2(ctrf_path, kept_ctrf)
        receipt = {
            "schema_version": 1,
            "command": command,
            "command_exit_code": proc.returncode,
            "reward": float(reward),
            "result": "pass" if float(reward) == 1.0 else "fail",
            "task_snapshot_sha256": tree_hash(verify, sanitized=False),
            "ctrf": kept_ctrf.name,
            "ctrf_sha256": sha256(kept_ctrf),
        }
        (run_dir / "handover-verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"matrix": matrix, **receipt}


def artifact_path(run_dir: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not nonempty(value):
        errors.append(f"{run_dir.name}/result.json: missing {label} path")
        return None
    path = (run_dir / str(value)).resolve()
    try:
        path.relative_to(run_dir.resolve())
    except ValueError:
        errors.append(f"{run_dir.name}/result.json: {label} escapes the run directory")
        return None
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"{run_dir.name}/result.json: {label} is missing or empty")
        return None
    return path


def validate_case_matrix(path: Path, run_name: str, errors: list[str]) -> dict:
    data = load_json(path, errors)
    total = data.get("total_units")
    passed = data.get("passed_case_ids")
    failed = data.get("failed_case_ids")
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        errors.append(f"{run_name}/case-matrix.json: total_units must be a positive integer")
        return {}
    for key, value in (("passed_case_ids", passed), ("failed_case_ids", failed)):
        if not isinstance(value, list) or not all(nonempty(item) for item in value):
            errors.append(f"{run_name}/case-matrix.json: {key} must contain non-empty strings")
            return {}
        if len(set(value)) != len(value):
            errors.append(f"{run_name}/case-matrix.json: {key} contains duplicates")
            return {}
    if set(passed) & set(failed):
        errors.append(f"{run_name}/case-matrix.json: passed and failed case IDs overlap")
    if len(passed) + len(failed) != total:
        errors.append(f"{run_name}/case-matrix.json: total_units does not match the case lists")
    return data


def validate_verifier_matrix(
    data: dict,
    slug: str,
    report_dir: Path,
    errors: list[str],
) -> dict:
    if data.get("status") != "pass":
        errors.append("verifier-matrix.json: status must be 'pass'")
    if data.get("task_slug") != slug:
        errors.append("verifier-matrix.json: task_slug mismatch")
    profile = data.get("profile")
    if profile not in {"cheap_deterministic", "expensive_stateful"}:
        errors.append(
            "verifier-matrix.json: profile must be cheap_deterministic or expensive_stateful"
        )
    unit_ids = data.get("unit_ids")
    if not isinstance(unit_ids, list) or not unit_ids or not all(nonempty(item) for item in unit_ids):
        errors.append("verifier-matrix.json: unit_ids must contain non-empty strings")
        unit_ids = []
    elif len(set(unit_ids)) != len(unit_ids):
        errors.append("verifier-matrix.json: unit_ids must be unique")
    declared_count = data.get("platform_visible_unit_count")
    if declared_count != len(unit_ids):
        errors.append("verifier-matrix.json: platform_visible_unit_count mismatch")
    if profile == "cheap_deterministic" and not 50 <= len(unit_ids) <= 1000:
        errors.append("verifier-matrix.json: cheap deterministic tasks need 50-1000 units")
    if profile == "expensive_stateful" and not 20 <= len(unit_ids) <= 80:
        errors.append("verifier-matrix.json: expensive stateful tasks need 20-80 units")

    unit_clusters = data.get("unit_clusters")
    if not isinstance(unit_clusters, dict) or set(unit_clusters) != set(unit_ids):
        errors.append("verifier-matrix.json: unit_clusters must map every unit ID exactly")
        unit_clusters = {}
    else:
        for unit_id, clusters in unit_clusters.items():
            if (
                not isinstance(clusters, list)
                or not clusters
                or not all(nonempty(cluster) for cluster in clusters)
                or len(set(clusters)) != len(clusters)
            ):
                errors.append(
                    f"verifier-matrix.json: unit_clusters[{unit_id!r}] must be unique non-empty strings"
                )
    cluster_names = {
        cluster
        for clusters in unit_clusters.values()
        if isinstance(clusters, list)
        for cluster in clusters
        if nonempty(cluster)
    }
    minimum_clusters = 6 if profile == "cheap_deterministic" else 4
    if len(cluster_names) < minimum_clusters:
        errors.append(
            f"verifier-matrix.json: profile requires at least {minimum_clusters} semantic clusters"
        )
    if unit_ids and unit_clusters and cluster_names:
        dominant = max(
            (
                sum(cluster in clusters for clusters in unit_clusters.values()) / len(unit_ids),
                cluster,
            )
            for cluster in cluster_names
        )
        if dominant[0] > 0.35 and not nonempty(data.get("dominant_cluster_justification")):
            errors.append(
                "verifier-matrix.json: a cluster covers >35% of units without justification"
            )

    cross_cluster = data.get("cross_cluster_unit_ids")
    if (
        not isinstance(cross_cluster, list)
        or len(set(cross_cluster)) < 2
        or not set(cross_cluster).issubset(set(unit_ids))
    ):
        errors.append("verifier-matrix.json: at least two valid cross_cluster_unit_ids are required")
    else:
        for unit_id in set(cross_cluster):
            if len(unit_clusters.get(unit_id, [])) < 2:
                errors.append(
                    f"verifier-matrix.json: cross-cluster unit {unit_id!r} has fewer than two clusters"
                )

    shapes = data.get("verifier_shapes")
    authority_substitute = data.get("authority_corpus_substitute") is True
    if not isinstance(shapes, list) or not all(nonempty(shape) for shape in shapes):
        errors.append("verifier-matrix.json: verifier_shapes must contain non-empty strings")
    elif len(set(shapes)) < 2 and not (authority_substitute and len(cluster_names) >= 6):
        errors.append("verifier-matrix.json: at least two verifier shapes are required")

    non_behavior = data.get("non_behavior_test_ids", [])
    ctrf = data.get("ctrf")
    if not isinstance(ctrf, dict):
        errors.append("verifier-matrix.json: ctrf evidence is required")
    else:
        ctrf_path_value = ctrf.get("path")
        if not nonempty(ctrf_path_value):
            errors.append("verifier-matrix.json: ctrf.path is required")
        else:
            ctrf_path = (report_dir / str(ctrf_path_value)).resolve()
            try:
                ctrf_path.relative_to(report_dir.resolve())
            except ValueError:
                errors.append("verifier-matrix.json: ctrf.path escapes the report directory")
            else:
                ctrf_data = load_json(ctrf_path, errors)
                summary = ctrf_data.get("summary") if isinstance(ctrf_data, dict) else None
                if (
                    not isinstance(non_behavior, list)
                    or not all(nonempty(test_id) for test_id in non_behavior)
                    or len(set(non_behavior)) != len(non_behavior)
                ):
                    errors.append(
                        "verifier-matrix.json: non_behavior_test_ids must be unique strings"
                    )
                    non_behavior = []
                expected_ctrf_tests = len(unit_ids) + len(non_behavior)
                if not isinstance(summary, dict) or summary.get("tests") != expected_ctrf_tests:
                    errors.append(
                        "verifier-matrix.json: CTRF summary.tests must equal behavior plus "
                        "declared non-behavior tests"
                    )
                if ctrf.get("sha256") != (sha256(ctrf_path) if ctrf_path.is_file() else None):
                    errors.append("verifier-matrix.json: CTRF sha256 mismatch")
    return {
        "unit_ids": set(unit_ids),
        "non_behavior_test_ids": set(non_behavior)
        if isinstance(non_behavior, list) and all(nonempty(item) for item in non_behavior)
        else set(),
        "unit_clusters": unit_clusters,
        "cluster_names": cluster_names,
        "profile": profile,
    }


def validate_category(
    data: dict,
    slug: str,
    declared_category: str,
    declared_subcategory: str,
    errors: list[str],
) -> None:
    if data.get("status") != "pass":
        errors.append("category-screen.json: status must be 'pass'")
    if data.get("task_slug") != slug:
        errors.append("category-screen.json: task_slug mismatch")
    if data.get("declared_category") != declared_category:
        errors.append("category-screen.json: declared_category mismatch")
    if data.get("declared_subcategory") != declared_subcategory:
        errors.append("category-screen.json: declared_subcategory mismatch")
    if declared_category not in TAXONOMY or declared_subcategory not in TAXONOMY.get(declared_category, set()):
        errors.append("category-screen.json: invalid Terminus 3 taxonomy pair")
    rationale = data.get("domain_rationale")
    evidence = data.get("evidence")
    if not nonempty(rationale):
        errors.append("category-screen.json: domain_rationale is required")
    if not isinstance(evidence, list) or not evidence or not all(nonempty(x) for x in evidence):
        errors.append("category-screen.json: evidence must contain visible-shape citations")


def validate_design(data: dict, slug: str, report_dir: Path, errors: list[str]) -> None:
    if data.get("status") != "pass":
        errors.append("design-signature.json: status must be 'pass'")
    if data.get("task_slug") != slug:
        errors.append("design-signature.json: task_slug mismatch")
    signature = data.get("signature")
    if not isinstance(signature, dict) or set(signature) != SIGNATURE_AXES:
        errors.append("design-signature.json: signature must contain exactly the six required axes")
    elif not all(nonempty(value) for value in signature.values()):
        errors.append("design-signature.json: every signature axis must be non-empty")
    max_matches = data.get("max_pairwise_matches")
    if not isinstance(max_matches, int) or isinstance(max_matches, bool) or max_matches > 4:
        errors.append("design-signature.json: max_pairwise_matches must be an integer <= 4")
    if not isinstance(data.get("compared_against"), list):
        errors.append("design-signature.json: compared_against must be a list")
        compared_against = []
    else:
        compared_against = data["compared_against"]
    architecture_family = data.get("architecture_family")
    batch_id = data.get("batch_id")
    if not nonempty(architecture_family):
        errors.append("design-signature.json: architecture_family is required")
    if not nonempty(batch_id):
        errors.append("design-signature.json: batch_id is required")

    recomputed_max = 0
    for other_slug in compared_against:
        if not nonempty(other_slug):
            errors.append("design-signature.json: compared_against entries must be slugs")
            continue
        other_path = report_dir.parent / str(other_slug) / EVIDENCE_FILES["design"]
        other = load_json(other_path, errors)
        other_signature = other.get("signature")
        if isinstance(signature, dict) and isinstance(other_signature, dict):
            recomputed_max = max(
                recomputed_max,
                sum(signature.get(axis) == other_signature.get(axis) for axis in SIGNATURE_AXES),
            )
        if (
            nonempty(batch_id)
            and other.get("batch_id") == batch_id
            and nonempty(architecture_family)
            and other.get("architecture_family") == architecture_family
        ):
            errors.append(
                "design-signature.json: only one task per architecture_family is allowed in a batch"
            )
    if compared_against and max_matches != recomputed_max:
        errors.append(
            "design-signature.json: max_pairwise_matches differs from recomputed signatures"
        )


def validate_preflight(data: dict, slug: str, errors: list[str]) -> None:
    if data.get("task_slug") != slug:
        errors.append("preflight.json: task_slug mismatch")
    if data.get("status") != "pass" or data.get("fail_count") != 0:
        errors.append("preflight.json: strict preflight did not pass")
    if data.get("strict") is not True:
        errors.append("preflight.json: strict must be true")
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("preflight.json: checks must be a non-empty list")
    elif not any(check.get("check") == "policy:static" for check in checks if isinstance(check, dict)):
        errors.append("preflight.json: policy:static evidence is missing")


def validate_probe_bundle(
    slug: str,
    task_dir: Path,
    languages: list[str],
    probe_dir: Path,
    verifier: dict,
    required_model: str | None,
    required_effort: str,
    errors: list[str],
    trusted_verifier: Callable[[Path], dict] = run_trusted_nop_verifier,
) -> dict:
    if not probe_dir.is_dir():
        errors.append(f"probe evidence directory not found: {probe_dir}")
        return {}
    manifest = load_json(probe_dir / "probe-manifest.json", errors)
    if manifest.get("schema_version") != 2:
        errors.append("probe-manifest.json: schema_version must be 2")
    if manifest.get("task_slug") != slug:
        errors.append("probe-manifest.json: task_slug mismatch")
    source_value = manifest.get("source_task")
    if not nonempty(source_value) or Path(str(source_value)).resolve() != task_dir.resolve():
        errors.append("probe-manifest.json: source_task mismatch")
    contract_hash = tree_hash(task_dir, sanitized=True)
    if manifest.get("solver_contract_sha256") != contract_hash:
        errors.append(
            "probe-manifest.json: solver contract changed after probe preparation; fresh runs required"
        )

    result_paths = sorted(probe_dir.glob("run_*/result.json"))
    result_count = len(result_paths)
    if result_count not in {2, 3}:
        errors.append("probe evidence: tasks require 2 runs, or 3 after an adaptive escalation")

    expected_units = verifier.get("unit_ids", set())
    current_snapshot = tree_hash(task_dir, sanitized=False)
    current_contract_files = file_hash_map(task_dir, sanitized=True)
    current_full_files = file_hash_map(task_dir, sanitized=False)
    agent_sessions: set[str] = set()
    runtime_values: set[str] = set()
    model_values: set[str] = set()
    effort_values: set[str] = set()
    run_results: list[dict] = []
    setup_failures = 0
    all_failure_clusters: set[str] = set()

    for ordinal, result_path in enumerate(result_paths, start=1):
        run_dir = result_path.parent
        run_error_start = len(errors)
        result = load_json(result_path, errors)
        if result.get("schema_version") != 2:
            errors.append(f"{run_dir.name}/result.json: schema_version must be 2")
        if result.get("task") != slug:
            errors.append(f"{run_dir.name}/result.json: task mismatch")
        if result.get("run") != ordinal or run_dir.name != f"run_{ordinal}":
            errors.append(f"{run_dir.name}/result.json: runs must be contiguous and correctly numbered")
        if result.get("evidence_complete") is not True:
            errors.append(f"{run_dir.name}/result.json: evidence_complete must be true")

        baseline = run_dir / "baseline"
        solve = run_dir / "solve"
        verify = run_dir / "verify"
        if not all(path.is_dir() for path in (baseline, solve, verify)):
            errors.append(
                f"{run_dir.name}: baseline/, solve/, and verify/ directories are required"
            )
        else:
            baseline_files = file_hash_map(baseline, sanitized=False)
            solve_files = file_hash_map(solve, sanitized=False)
            verify_files = file_hash_map(verify, sanitized=False)
            if baseline_files != current_contract_files:
                errors.append(
                    f"{run_dir.name}: baseline/ is not the current sanitized solver contract"
                )
            changed_paths = {
                rel
                for rel in baseline_files.keys() | solve_files.keys()
                if baseline_files.get(rel) != solve_files.get(rel)
            }
            if not changed_paths:
                errors.append(f"{run_dir.name}: solve/ contains no candidate implementation change")
            invalid_changes = sorted(
                rel for rel in changed_paths if not rel.startswith("environment/")
            )
            if invalid_changes:
                errors.append(
                    f"{run_dir.name}: solver changed files outside environment/: "
                    + ", ".join(invalid_changes)
                )
            expected_verify_files = dict(current_full_files)
            for rel in changed_paths:
                if rel in solve_files:
                    expected_verify_files[rel] = solve_files[rel]
                else:
                    expected_verify_files.pop(rel, None)
            if verify_files != expected_verify_files:
                errors.append(
                    f"{run_dir.name}: verify/ is not the current full task plus the solver delta"
                )

        agent = result.get("agent")
        if not isinstance(agent, dict):
            errors.append(f"{run_dir.name}/result.json: agent evidence is required")
            agent = {}
        runner = agent.get("runner")
        if runner not in VALID_PROBE_RUNNERS:
            errors.append(f"{run_dir.name}/result.json: unsupported probe runner {runner!r}")
        if agent.get("fresh_context") is not True:
            errors.append(f"{run_dir.name}/result.json: fresh_context must be true")
        session_id = agent.get("session_id")
        if not nonempty(session_id):
            errors.append(f"{run_dir.name}/result.json: agent session_id is required")
        elif session_id in agent_sessions:
            errors.append(f"{run_dir.name}/result.json: agent session_id must be unique")
        else:
            agent_sessions.add(str(session_id))
        run_runtime = str(agent.get("runtime", "")).strip().lower().replace("_", "-")
        runtime_values.add(run_runtime)
        if run_runtime not in PROBE_PROFILES:
            errors.append(f"{run_dir.name}/result.json: unsupported runtime {run_runtime!r}")
            accepted_models: tuple[str, ...] = ()
        else:
            accepted_models = PROBE_PROFILES[run_runtime]
            expected_runner = "codex-subagent" if run_runtime == "codex" else "claude-agent"
            if runner != expected_runner:
                errors.append(f"{run_dir.name}/result.json: runner/runtime mismatch")
        if required_model:
            accepted_models = (required_model,)
        run_model = str(agent.get("model", "")).lower()
        model_values.add(run_model)
        if not run_model or not any(candidate.lower() in run_model for candidate in accepted_models):
            errors.append(f"{run_dir.name}/result.json: model does not match the runtime profile")
        run_effort = str(agent.get("reasoning_effort", ""))
        effort_values.add(run_effort)
        if run_effort != required_effort:
            errors.append(f"{run_dir.name}/result.json: reasoning effort mismatch")
        launch_command = str(agent.get("launch_command", "")).lower()
        if not launch_command:
            errors.append(f"{run_dir.name}/result.json: launch_command is required")
        elif any(token in launch_command for token in FORBIDDEN_PROBE_COMMAND_TOKENS):
            errors.append(f"{run_dir.name}/result.json: Harbor/stb LLM launch is forbidden")

        artifacts = result.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append(f"{run_dir.name}/result.json: artifact evidence is required")
            artifacts = {}
        artifact_files: dict[str, Path] = {}
        for key in (
            "solve_diff",
            "verifier_log",
            "case_matrix",
            "verification_ctrf",
            "agent_transcript",
        ):
            path = artifact_path(run_dir, artifacts.get(key), key, errors)
            if path is not None:
                artifact_files[key] = path
                if artifacts.get(f"{key}_sha256") != sha256(path):
                    errors.append(f"{run_dir.name}/result.json: {key} sha256 mismatch")
        matrix = (
            validate_case_matrix(artifact_files["case_matrix"], run_dir.name, errors)
            if "case_matrix" in artifact_files
            else {}
        )
        if "solve_diff" in artifact_files and all(
            path.is_dir() for path in (baseline, solve)
        ):
            try:
                recomputed_diff = recompute_solve_diff(run_dir)
            except OSError as exc:
                errors.append(f"{run_dir.name}: could not recompute solve.diff: {exc}")
            else:
                if artifact_files["solve_diff"].read_bytes() != recomputed_diff:
                    errors.append(
                        f"{run_dir.name}: solve.diff does not match baseline/ versus solve/"
                    )
        if "verification_ctrf" in artifact_files:
            derived_matrix = matrix_from_ctrf(
                artifact_files["verification_ctrf"], run_dir.name, errors
            )
            if derived_matrix and matrix != derived_matrix:
                errors.append(
                    f"{run_dir.name}: case-matrix.json differs from verification CTRF"
                )
        all_passed_ids = set(matrix.get("passed_case_ids", []))
        all_failed_ids = set(matrix.get("failed_case_ids", []))
        non_behavior_ids = verifier.get("non_behavior_test_ids", set())
        if expected_units and all_passed_ids | all_failed_ids != expected_units | non_behavior_ids:
            errors.append(f"{run_dir.name}/case-matrix.json: unit IDs differ from verifier-matrix.json")
        if all_failed_ids & non_behavior_ids:
            errors.append(
                f"{run_dir.name}/case-matrix.json: non-behavior verifier checks must pass"
            )
        passed_ids = all_passed_ids & expected_units
        failed_ids = all_failed_ids & expected_units

        verification = result.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{run_dir.name}/result.json: verification evidence is required")
            verification = {}
        if not nonempty(verification.get("command")):
            errors.append(f"{run_dir.name}/result.json: verification command is required")
        verify_command = str(verification.get("command", "")).lower()
        if any(
            token in verify_command
            for token in ("terminus-2", "@openai/", "@anthropic/")
        ):
            errors.append(f"{run_dir.name}/result.json: verifier command invokes a forbidden LLM path")
        if not isinstance(verification.get("exit_code"), int) or isinstance(
            verification.get("exit_code"), bool
        ):
            errors.append(f"{run_dir.name}/result.json: verification exit_code must be an integer")
        if verification.get("task_snapshot_sha256") != current_snapshot:
            errors.append(
                f"{run_dir.name}/result.json: verification target is stale after task/test changes"
            )
        result_value = result.get("result")
        if result_value not in {"pass", "fail"}:
            errors.append(f"{run_dir.name}/result.json: result must be pass or fail")
        if result_value == "pass" and failed_ids:
            errors.append(f"{run_dir.name}/result.json: passing run has failed cases")
        if result_value == "fail" and not failed_ids:
            errors.append(f"{run_dir.name}/result.json: failing run has no failed cases")
        expected_reward = 1.0 if result_value == "pass" else 0.0
        if verification.get("reward") != expected_reward:
            errors.append(
                f"{run_dir.name}/result.json: verification reward must be {expected_reward}"
            )
        failure_type = result.get("failure_type")
        if result_value == "fail" and failure_type != "semantic":
            setup_failures += 1
            errors.append(
                f"{run_dir.name}/result.json: only semantic failures count toward difficulty"
            )
        if result_value == "pass" and failure_type not in {None, ""}:
            errors.append(f"{run_dir.name}/result.json: passing run cannot have a failure_type")

        if len(errors) == run_error_start:
            try:
                trusted = trusted_verifier(run_dir)
            except Exception as exc:  # fail closed on Docker/Harbor/output errors
                errors.append(f"{run_dir.name}: trusted NOP verifier rerun failed: {exc}")
            else:
                if trusted.get("matrix") != matrix:
                    errors.append(
                        f"{run_dir.name}: recorded case matrix differs from trusted NOP rerun"
                    )
                if trusted.get("result") != result_value:
                    errors.append(
                        f"{run_dir.name}: recorded result differs from trusted NOP rerun"
                    )
                if trusted.get("reward") != expected_reward:
                    errors.append(
                        f"{run_dir.name}: recorded reward differs from trusted NOP rerun"
                    )
                if trusted.get("task_snapshot_sha256") != tree_hash(verify, sanitized=False):
                    errors.append(
                        f"{run_dir.name}: trusted NOP receipt does not bind the current verify tree"
                    )

        failed_clusters = {
            cluster
            for unit_id in failed_ids
            for cluster in verifier.get("unit_clusters", {}).get(unit_id, [])
        }
        all_failure_clusters.update(failed_clusters)
        run_results.append(
            {
                "run": ordinal,
                "result": result_value,
                "passed_ids": passed_ids,
                "failed_ids": failed_ids,
                "failure_clusters": failed_clusters,
            }
        )

    solved_runs = sum(1 for item in run_results if item["result"] == "pass")
    if result_count and solved_runs == result_count:
        errors.append("probe evidence: all local runs solved; the task has no local difficulty signal")

    union_passed = (
        set().union(*(item["passed_ids"] for item in run_results)) if run_results else set()
    )
    failed_sets = [item["failed_ids"] for item in run_results]
    common_misses = set.intersection(*failed_sets) if failed_sets else set()
    union_coverage = len(union_passed) / len(expected_units) if expected_units else 0.0
    failed_cluster_sets = [
        frozenset(item["failure_clusters"])
        for item in run_results
        if item["result"] == "fail"
    ]
    de_correlated = len(failed_cluster_sets) >= 2 and len(set(failed_cluster_sets)) >= 2
    if solved_runs == 0:
        if union_coverage != 1.0:
            errors.append("probe evidence: zero-solve Frontier signal requires 100% per-case union coverage")
        if common_misses:
            errors.append("probe evidence: zero-solve Frontier signal must have no common misses")
        if not de_correlated:
            errors.append("probe evidence: zero-solve Frontier failures must be de-correlated")
    if len(runtime_values) != 1:
        errors.append("probe evidence: all runs must use one runtime")
    if len(model_values) != 1:
        errors.append("probe evidence: all runs must use one model")
    if effort_values != {required_effort}:
        errors.append("probe evidence: all runs must use the required reasoning effort")

    derived = {
        "task_slug": slug,
        "probe_runtime": next(iter(runtime_values), ""),
        "probe_model": next(iter(model_values), ""),
        "reasoning_effort": next(iter(effort_values), ""),
        "semantic_runs": result_count,
        "solved_runs": solved_runs,
        "setup_failures": setup_failures,
        "union_coverage": union_coverage,
        "common_miss_count": len(common_misses),
        "failure_clusters": sorted(all_failure_clusters),
        "de_correlated": de_correlated,
        "local_accuracy": solved_runs / result_count if result_count else None,
        "local_tier_signal": (
            "frontier" if solved_runs / result_count < 0.2
            else "advanced" if solved_runs / result_count < 0.5
            else "core" if solved_runs / result_count < 0.8
            else "base"
        ) if result_count else None,
        "task_snapshot_sha256": current_snapshot,
    }
    return derived


def validate_zip(path: Path, errors: list[str]) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"zip: {exc}")
        return
    required = {"task.toml", "instruction.md", "environment/", "solution/", "tests/"}
    present = {
        "task.toml" if "task.toml" in names else "",
        "instruction.md" if "instruction.md" in names else "",
        "environment/" if any(name.startswith("environment/") for name in names) else "",
        "solution/" if any(name.startswith("solution/") for name in names) else "",
        "tests/" if any(name.startswith("tests/") for name in names) else "",
    }
    missing = sorted(required - present)
    if missing:
        errors.append("zip: missing root entries: " + ", ".join(missing))
    if any("\\" in name or name.startswith("/") or ".." in Path(name).parts for name in names):
        errors.append("zip: unsafe or non-POSIX archive path")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--probe-dir", type=Path, required=True)
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--required-probe-model")
    parser.add_argument("--required-reasoning-effort", default="medium")
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    report_dir = args.report_dir.resolve()
    probe_dir = args.probe_dir.resolve()
    zip_path = args.zip_path.resolve()
    submission = args.submission.resolve()
    slug = task_dir.name
    output = (args.output or report_dir / "handover.json").resolve()
    errors: list[str] = []

    if report_dir.name != slug:
        errors.append("report directory name must match the task slug")
    try:
        metadata = tomllib.loads((task_dir / "task.toml").read_text())["metadata"]
        declared = metadata["category"]
        declared_subcategory = metadata["subcategory"]
        languages = metadata["languages"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"task.toml: {exc}")
        declared = ""
        declared_subcategory = ""
        languages = []
    if declared not in TAXONOMY or declared_subcategory not in TAXONOMY.get(declared, set()):
        errors.append(f"task.toml: invalid Terminus 3 taxonomy pair {declared!r} / {declared_subcategory!r}")
    if not isinstance(languages, list) or not all(nonempty(language) for language in languages):
        errors.append("task.toml: metadata.languages must contain non-empty strings")
        languages = []

    evidence = {
        key: load_json(report_dir / filename, errors)
        for key, filename in EVIDENCE_FILES.items()
        if key != "probe"
    }
    evidence["probe"] = {}
    if evidence["category"]:
        validate_category(evidence["category"], slug, declared, declared_subcategory, errors)
    if evidence["design"]:
        validate_design(evidence["design"], slug, report_dir, errors)
    if evidence["preflight"]:
        validate_preflight(evidence["preflight"], slug, errors)
    verifier = (
        validate_verifier_matrix(evidence["verifier"], slug, report_dir, errors)
        if evidence["verifier"]
        else {}
    )
    probe_error_start = len(errors)
    probe_derived = validate_probe_bundle(
        slug,
        task_dir,
        languages,
        probe_dir,
        verifier,
        args.required_probe_model,
        args.required_reasoning_effort,
        errors,
    )
    probe_errors = errors[probe_error_start:]
    probe_verdict = {
        "task_slug": slug,
        "status": "candidate_ready" if not probe_errors else "unverified",
        **probe_derived,
        "errors": probe_errors,
    }
    probe_verdict_path = report_dir / EVIDENCE_FILES["probe"]
    probe_verdict_path.parent.mkdir(parents=True, exist_ok=True)
    probe_verdict_path.write_text(
        json.dumps(probe_verdict, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    policy = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("task-policy.py")), "validate-task", str(task_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if policy.returncode != 0:
        errors.append("task policy: " + policy.stdout.replace("\n", "; ").strip())

    sufficiency_check = (
        Path(__file__).resolve().parents[1]
        / ".agent"
        / "skills"
        / "terminus-regular-task-authoring"
        / "scripts"
        / "sufficiency_manifest_check.py"
    )
    sufficiency = subprocess.run(
        [sys.executable, str(sufficiency_check), str(task_dir), str(report_dir / EVIDENCE_FILES["sufficiency"])],
        capture_output=True,
        text=True,
        check=False,
    )
    if sufficiency.returncode != 0:
        errors.append("instruction sufficiency: " + sufficiency.stdout.replace("\n", "; ").strip())

    if not zip_path.is_file():
        errors.append(f"zip not found: {zip_path}")
    else:
        validate_zip(zip_path, errors)
        if evidence["preflight"] and evidence["preflight"].get("artifact_sha256") != sha256(zip_path):
            errors.append("preflight.json: artifact_sha256 does not match the current ZIP")
    if not submission.is_file():
        errors.append(f"submission metadata not found: {submission}")

    artifact_sha = sha256(zip_path) if zip_path.is_file() else None
    payload = {
        "task_slug": slug,
        "status": "candidate_ready" if not errors else "unverified",
        "artifact": str(zip_path),
        "artifact_sha256": artifact_sha,
        "submission": str(submission),
        "evidence": {key: str(report_dir / filename) for key, filename in EVIDENCE_FILES.items()},
        "probe_evidence": str(probe_dir),
        "probe_derived": probe_derived,
        "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    if errors:
        print(f"UNVERIFIED: {slug} has {len(errors)} blocking finding(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"CANDIDATE_READY: {slug} ({artifact_sha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
