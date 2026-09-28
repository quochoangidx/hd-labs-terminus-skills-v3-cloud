#!/usr/bin/env python3
"""Fail-closed handover gate for autonomous task batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

AUTHORING_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / ".agent"
    / "skills"
    / "terminus-regular-task-authoring"
    / "scripts"
)
sys.path.insert(0, str(AUTHORING_SCRIPTS))
from verifier_architecture_check import validate_matrix as validate_verifier_architecture  # noqa: E402

SESSION_BUDGET_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / ".agent"
    / "skills"
    / "task-batch"
    / "scripts"
)
sys.path.insert(0, str(SESSION_BUDGET_SCRIPTS))
from session_budget import validate_receipt as validate_session_budget_receipt  # noqa: E402
from quota_guard import validate as validate_quota_ledger  # noqa: E402

RUBRIC_CHECKER = (
    Path(__file__).resolve().parents[1]
    / ".agent"
    / "skills"
    / "terminus-rubric-authoring"
    / "scripts"
    / "check_rubric.py"
)

EVIDENCE_FILES = {
    "agent_session_budget": "agent-session-budget.json",
    "category": "category-screen.json",
    "client_review": "client-review.json",
    "design": "design-signature.json",
    "preflight": "preflight.json",
    "prefreeze_review": "pre-freeze-review.json",
    "probe_preflight": "probe-preflight.json",
    "probe": "probe-verdict.json",
    "quota_ledger": "quota-ledger.json",
    "rubric": "rubric-check.json",
    "semantic": "semantic-coverage.json",
    "style": "style-audit.json",
    "sufficiency": "instruction-sufficiency.json",
    "task_style": "task-style-preflight.json",
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
STYLE_TEXT_SUFFIXES = {
    "",
    ".bash",
    ".c",
    ".cc",
    ".cpp",
    ".go",
    ".h",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".md",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
}


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
            name == "task.toml"
            or name.startswith("rubric")
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
            name == "task.toml"
            or name.startswith("rubric")
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


def semantic_probe_geometry(run_results: list[dict]) -> dict:
    """Derive mechanism-level geometry without weighting replicated fixtures."""
    solved_runs = sum(1 for item in run_results if item.get("result") == "pass")
    failed_node_sets = [
        frozenset(item.get("failure_nodes", set()))
        for item in run_results
        if item.get("result") == "fail"
    ]
    de_correlated = len(failed_node_sets) >= 2 and len(set(failed_node_sets)) >= 2
    advanced_pass = (
        len(run_results) == 3
        and solved_runs == 1
        and len(failed_node_sets) == 2
        and all(len(nodes) >= 2 for nodes in failed_node_sets)
        and de_correlated
    )
    return {
        "solved_runs": solved_runs,
        "failed_node_sets": failed_node_sets,
        "semantic_de_correlated": de_correlated,
        "advanced_geometry_pass": advanced_pass,
    }


def validate_core_plus_outcome(result_count: int, solved_runs: int) -> list[str]:
    errors: list[str] = []
    if result_count != 2:
        errors.append("probe evidence: CORE+ batches require exactly two blind-solver runs")
    if solved_runs > 1:
        errors.append("probe evidence: CORE+ batches require zero or one solved run out of two")
    return errors


def run_trusted_nop_verifier(run_dir: Path) -> dict:
    """Rerun the verifier with the fixed local NOP agent and derive its outcome."""
    verify = (run_dir / "verify").resolve()
    if not verify.is_dir():
        raise RuntimeError(f"verification task is missing: {verify}")
    try:
        task_config = tomllib.loads((verify / "task.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"trusted NOP task.toml is unreadable: {exc}") from exc
    verifier_network_mode = task_config.get("verifier", {}).get("network_mode")
    if verifier_network_mode == "no-network":
        return run_direct_docker_nop_verifier(run_dir, verify)
    stb = shutil.which("stb")
    if not stb:
        raise RuntimeError("stb executable is unavailable for trusted local NOP verification")
    bundled_harbor = Path(stb).resolve().with_name("harbor")
    harbor_command = (
        [str(bundled_harbor), "run"]
        if bundled_harbor.is_file() and os.access(bundled_harbor, os.X_OK)
        else [stb, "harbor", "run"]
    )
    with tempfile.TemporaryDirectory(prefix="batch-handover-nop-") as temp:
        jobs_dir = Path(temp) / "jobs"
        command = [
            *harbor_command,
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
        try:
            proc = subprocess.run(
                command,
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=2400,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            (run_dir / "handover-verifier.log").write_text(
                stdout + stderr,
                encoding="utf-8",
            )
            raise RuntimeError(
                "trusted NOP rerun exceeded 2400 seconds; "
                f"see {run_dir / 'handover-verifier.log'}"
            ) from exc
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


def run_direct_docker_nop_verifier(run_dir: Path, verify: Path) -> dict:
    """Verify a no-network task directly when Harbor's Docker provider rejects it."""
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("docker executable is unavailable for trusted no-network NOP verification")
    with tempfile.TemporaryDirectory(prefix="batch-handover-direct-nop-") as temp:
        logs_dir = Path(temp) / "logs"
        logs_dir.mkdir()
        os.chmod(logs_dir, 0o777)
        build_command = [docker, "build", "-q", str(verify / "tests")]
        build = subprocess.run(
            build_command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        if build.returncode != 0:
            (run_dir / "handover-verifier.log").write_text(
                build.stdout + build.stderr,
                encoding="utf-8",
            )
            raise RuntimeError(
                f"trusted direct-Docker verifier build exited {build.returncode}; "
                f"see {run_dir / 'handover-verifier.log'}"
            )
        image = next(
            (line.strip() for line in reversed(build.stdout.splitlines()) if line.strip()),
            "",
        )
        if not image:
            raise RuntimeError("trusted direct-Docker verifier build returned no image id")
        command = [
            docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev",
            "--tmpfs",
            "/var/tmp:rw,nosuid,nodev",
            "-v",
            f"{verify / 'environment' / 'app'}:/app:ro",
            "-v",
            f"{logs_dir}:/logs/verifier",
            image,
            "bash",
            "/tests/test.sh",
        ]
        try:
            proc = subprocess.run(
                command,
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("trusted direct-Docker NOP rerun exceeded 900 seconds") from exc
        (run_dir / "handover-verifier.log").write_text(
            build.stdout + build.stderr + proc.stdout + proc.stderr,
            encoding="utf-8",
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"trusted direct-Docker NOP rerun exited {proc.returncode}; "
                f"see {run_dir / 'handover-verifier.log'}"
            )
        reward_path = logs_dir / "reward.txt"
        ctrf_path = logs_dir / "ctrf.json"
        try:
            reward = float(reward_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError) as exc:
            raise RuntimeError("trusted direct-Docker NOP produced no numeric reward") from exc
        ctrf_errors: list[str] = []
        matrix = matrix_from_ctrf(ctrf_path, run_dir.name, ctrf_errors)
        if ctrf_errors or not matrix:
            raise RuntimeError(
                "trusted direct-Docker NOP CTRF is invalid: " + "; ".join(ctrf_errors)
            )
        kept_ctrf = run_dir / "handover-verification-ctrf.json"
        shutil.copy2(ctrf_path, kept_ctrf)
        receipt = {
            "schema_version": 1,
            "build_command": build_command,
            "command": command,
            "command_exit_code": proc.returncode,
            "reward": reward,
            "result": "pass" if reward == 1.0 else "fail",
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
    architecture_errors, derived = validate_verifier_architecture(
        data,
        report_dir,
        expected_slug=slug,
        require_ctrf=True,
    )
    errors.extend(architecture_errors)
    return derived


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
    domain_key = data.get("domain_key")
    batch_id = data.get("batch_id")
    if not nonempty(architecture_family):
        errors.append("design-signature.json: architecture_family is required")
    if not nonempty(batch_id):
        errors.append("design-signature.json: batch_id is required")
    if not nonempty(domain_key):
        errors.append("design-signature.json: domain_key is required")

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
        if (
            nonempty(batch_id)
            and other.get("batch_id") == batch_id
            and nonempty(domain_key)
            and other.get("domain_key") == domain_key
        ):
            errors.append("design-signature.json: domain_key must be unique within a batch")
    if compared_against and max_matches != recomputed_max:
        errors.append(
            "design-signature.json: max_pairwise_matches differs from recomputed signatures"
        )


def validate_batch_index(
    data: dict,
    slug: str,
    report_dir: Path,
    design: dict,
    expected_size: int,
    errors: list[str],
    incremental: bool = False,
) -> None:
    """Prove a design receipt was compared with the current or complete batch."""
    status = data.get("status")
    if incremental:
        if data.get("schema_version") != 2:
            errors.append("batch index: incremental mode requires schema_version 2")
        if status not in {"building", "complete"}:
            errors.append("batch index: status must be building or complete")
    elif not (
        (data.get("schema_version") == 1 and status == "pass")
        or (data.get("schema_version") == 2 and status == "complete")
    ):
        errors.append(
            "batch index: final mode requires schema-v1 pass or schema-v2 complete"
        )
    if data.get("batch_id") != design.get("batch_id"):
        errors.append("batch index: batch_id differs from design-signature.json")
    task_slugs = data.get("task_slugs")
    if (
        not isinstance(task_slugs, list)
        or not task_slugs
        or not all(nonempty(item) for item in task_slugs)
        or len(set(task_slugs)) != len(task_slugs)
    ):
        errors.append("batch index: task_slugs must be unique non-empty strings")
        return
    if data.get("expected_count") != expected_size:
        errors.append("batch index: expected_count does not match --expected-batch-size")
    if incremental:
        if len(task_slugs) > expected_size:
            errors.append("batch index: partial task count exceeds --expected-batch-size")
        if status == "complete" and len(task_slugs) != expected_size:
            errors.append("batch index: complete status requires exactly the expected task count")
    elif len(task_slugs) != expected_size:
        errors.append("batch index: task count does not match --expected-batch-size")
    if slug not in task_slugs:
        errors.append("batch index: current task is absent from task_slugs")
    expected_peers = set(task_slugs) - {slug}
    declared_peers = design.get("compared_against")
    if not isinstance(declared_peers, list) or set(declared_peers) != expected_peers:
        errors.append("batch index: compared_against must contain every other batch task exactly")

    designs: dict[str, dict] = {}
    for task_slug in task_slugs:
        path = report_dir.parent / str(task_slug) / EVIDENCE_FILES["design"]
        other = load_json(path, errors)
        designs[str(task_slug)] = other
        if other.get("task_slug") != task_slug or other.get("batch_id") != data.get("batch_id"):
            errors.append(f"batch index: invalid design receipt for {task_slug}")
    domain_keys = [item.get("domain_key") for item in designs.values()]
    families = [item.get("architecture_family") for item in designs.values()]
    if not all(nonempty(value) for value in domain_keys) or len(set(domain_keys)) != len(domain_keys):
        errors.append("batch index: domain_key must be non-empty and unique across the batch")
    if not all(nonempty(value) for value in families) or len(set(families)) != len(families):
        errors.append("batch index: architecture_family must be non-empty and unique across the batch")
    for index, left_slug in enumerate(task_slugs):
        left = designs[str(left_slug)].get("signature")
        if not isinstance(left, dict):
            continue
        for right_slug in task_slugs[index + 1 :]:
            right = designs[str(right_slug)].get("signature")
            if not isinstance(right, dict):
                continue
            matches = sum(left.get(axis) == right.get(axis) for axis in SIGNATURE_AXES)
            if matches > 4:
                errors.append(
                    f"batch index: {left_slug} and {right_slug} match on {matches}/6 axes"
                )


def validate_candidate_ledger(
    path: Path,
    task_slugs: list[str],
    incremental: bool,
    errors: list[str],
) -> None:
    """Validate the adaptive candidate ledger and bind its accepted subset."""
    data = load_json(path, errors)
    if not data:
        return
    checker = (
        Path(__file__).resolve().parents[1]
        / ".agent"
        / "skills"
        / "task-batch"
        / "scripts"
        / "design_pattern_mix_check.py"
    )
    command = [sys.executable, str(checker), str(path)]
    if incremental:
        command.append("--allow-partial")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(
            "candidate ledger: "
            + (result.stdout + result.stderr).replace("\n", "; ").strip()
        )
        return

    if data.get("schema_version") == 3:
        accepted = data.get("accepted_task_slugs")
    else:
        accepted = [
            entry.get("task_slug")
            for entry in data.get("candidates", [])
            if isinstance(entry, dict)
        ]
    if not isinstance(accepted, list) or set(accepted) != set(task_slugs):
        errors.append(
            "candidate ledger: accepted task slugs must match the batch index"
        )


def validate_preflight(
    data: dict,
    slug: str,
    task_dir: Path,
    report_dir: Path,
    errors: list[str],
) -> None:
    if data.get("task_slug") != slug:
        errors.append("preflight.json: task_slug mismatch")
    if data.get("status") != "pass" or data.get("fail_count") != 0:
        errors.append("preflight.json: strict preflight did not pass")
    if data.get("strict") is not True:
        errors.append("preflight.json: strict must be true")
    if data.get("task_snapshot_sha256") != tree_hash(task_dir, sanitized=False):
        errors.append("preflight.json: task changed after strict preflight")
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("preflight.json: checks must be a non-empty list")
    else:
        check_status = {
            check.get("check"): check.get("status")
            for check in checks
            if isinstance(check, dict)
        }
        required_checks = {
            "policy:static",
            "verifier:reward-dir-mode",
            "verifier:unprivileged-candidate",
            "verifier:explicit-promise-alignment",
            "docker:daemon",
            "docker:agent-build",
            "docker:verifier-build",
            "docker:oracle",
            "docker:nop",
            "docker:noexec-tmp",
        }
        missing = sorted(required_checks - set(check_status))
        if missing:
            errors.append("preflight.json: required checks missing: " + ", ".join(missing))
        failed = sorted(name for name in required_checks if check_status.get(name) != "pass")
        if failed:
            errors.append("preflight.json: required checks not passing: " + ", ".join(failed))
    evidence_files = data.get("evidence_files")
    required_logs = {
        "docker-agent-build.log",
        "docker-verifier-build.log",
        "oracle-solve.log",
        "oracle-verifier.log",
        "oracle-ctrf.json",
        "oracle-reward.txt",
        "nop-verifier.log",
        "nop-ctrf.json",
        "nop-reward.txt",
        "oracle-noexec-solve.log",
        "oracle-noexec-verifier.log",
        "oracle-noexec-ctrf.json",
        "oracle-noexec-reward.txt",
    }
    if not isinstance(evidence_files, dict):
        errors.append("preflight.json: evidence_files must hash-bind build and verifier logs")
        return
    missing_logs = sorted(required_logs - set(evidence_files))
    if missing_logs:
        errors.append("preflight.json: required audit logs missing: " + ", ".join(missing_logs))
    validated_paths: dict[str, Path] = {}
    for name, receipt in evidence_files.items():
        if not isinstance(receipt, dict) or not nonempty(receipt.get("path")):
            errors.append(f"preflight.json: invalid evidence receipt for {name}")
            continue
        path = Path(str(receipt["path"]))
        try:
            path.resolve().relative_to(report_dir.resolve())
        except ValueError:
            errors.append(f"preflight.json: evidence must stay inside report directory: {path}")
            continue
        if not path.is_file():
            errors.append(f"preflight.json: evidence file missing: {path}")
            continue
        validated_paths[name] = path
        if receipt.get("sha256") != sha256(path):
            errors.append(f"preflight.json: evidence sha256 mismatch: {name}")
        if receipt.get("size") != path.stat().st_size:
            errors.append(f"preflight.json: evidence size mismatch: {name}")
    for name in required_logs - {"oracle-solve.log", "oracle-noexec-solve.log"}:
        path = validated_paths.get(name)
        if path is not None and path.stat().st_size == 0:
            errors.append(f"preflight.json: required audit artifact is empty: {name}")
    for label, expected_reward, expect_all_pass in (
        ("oracle", "1", True),
        ("nop", "0", False),
        ("oracle-noexec", "1", True),
    ):
        reward_path = validated_paths.get(f"{label}-reward.txt")
        if reward_path is not None and reward_path.read_text(errors="replace").strip() != expected_reward:
            errors.append(f"preflight.json: {label} raw reward does not equal {expected_reward}")
        ctrf_path = validated_paths.get(f"{label}-ctrf.json")
        if ctrf_path is None:
            continue
        matrix = matrix_from_ctrf(ctrf_path, f"preflight-{label}", errors)
        if not matrix:
            continue
        failed = matrix.get("failed_case_ids", [])
        if expect_all_pass and failed:
            errors.append(f"preflight.json: {label} CTRF contains failed tests")
        if not expect_all_pass and not failed:
            errors.append("preflight.json: NOP CTRF contains no failed tests")


def validate_client_review(
    data: dict,
    slug: str,
    zip_path: Path,
    report_dir: Path,
    errors: list[str],
) -> None:
    if data.get("schema_version") != 1:
        errors.append("client-review.json: schema_version must be 1")
    scanner = (
        Path(__file__).resolve().parents[1]
        / ".agent"
        / "skills"
        / "task-client-feedback-review"
        / "scripts"
        / "review_task.py"
    )
    if not scanner.is_file() or data.get("scanner_sha256") != sha256(scanner):
        errors.append("client-review.json: scanner hash is stale or invalid")
    results = data.get("results")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        errors.append("client-review.json: results must contain exactly one task review")
        return
    result = results[0]
    if result.get("schema_version") != 2:
        errors.append("client-review.json: task review schema_version must be 2")
    if result.get("task") != slug:
        errors.append("client-review.json: task slug mismatch")
    expected_sha = sha256(zip_path) if zip_path.is_file() else None
    if result.get("artifact_sha256") != expected_sha:
        errors.append("client-review.json: artifact_sha256 does not match final ZIP")
    if result.get("status") != "ready":
        errors.append("client-review.json: final ZIP review status must be ready")
    counts = result.get("counts")
    if not isinstance(counts, dict):
        errors.append("client-review.json: counts are missing")
    else:
        if counts.get("blocker") != 0:
            errors.append("client-review.json: blocking findings remain")
        if counts.get("should_fix") != 0:
            errors.append("client-review.json: should-fix findings remain")
    manual = data.get("manual_review")
    if not isinstance(manual, dict) or manual.get("status") != "pass":
        errors.append("client-review.json: passing manual review evidence is required")
        return
    for key in ("runtime", "model", "session_id", "transcript", "transcript_sha256"):
        if not nonempty(manual.get(key)):
            errors.append(f"client-review.json: manual_review.{key} is required")
    transcript_value = manual.get("transcript")
    if not nonempty(transcript_value):
        return
    transcript = (report_dir / str(transcript_value)).resolve()
    try:
        transcript.relative_to(report_dir.resolve())
    except ValueError:
        errors.append("client-review.json: manual transcript must stay inside report directory")
        return
    if not transcript.is_file() or transcript.stat().st_size == 0:
        errors.append("client-review.json: manual transcript is missing or empty")
    elif manual.get("transcript_sha256") != sha256(transcript):
        errors.append("client-review.json: manual transcript sha256 mismatch")


def style_surface_hashes(task_dir: Path) -> dict[str, str]:
    surfaces: dict[str, str] = {}
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file() or any(part in VOLATILE_HASH_DIRS for part in path.relative_to(task_dir).parts):
            continue
        if path.name == "Dockerfile" or path.suffix.lower() in STYLE_TEXT_SUFFIXES:
            try:
                path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            surfaces[path.relative_to(task_dir).as_posix()] = sha256(path)
    return surfaces


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^# {re.escape(heading)}\s*$\n(.*?)(?=^# |\Z)",
        text,
    )
    return match.group(1).strip() if match else ""


def validate_submission(
    submission: Path,
    task_dir: Path,
    errors: list[str],
) -> None:
    if not submission.is_file():
        errors.append(f"submission metadata not found: {submission}")
        return
    try:
        text = submission.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"submission metadata is not readable UTF-8: {exc}")
        return
    sections = {
        heading: markdown_section(text, heading)
        for heading in (
            "Difficulty Explanation",
            "Solution Explanation",
            "Verification Explanation",
            "Relevant Experience",
            "Metadata",
            "Rubrics",
        )
    }
    # Since 2026-09-26 the packet holds Relevant Experience, Metadata and Rubrics:
    # the explanations live in task.toml [metadata], which the platform reads from
    # the ZIP, so they are taken from there when the packet does not repeat them.
    try:
        import tomllib

        metadata = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8")).get("metadata", {})
    except (OSError, ValueError):
        metadata = {}
    for heading, key in (
        ("Difficulty Explanation", "difficulty_explanation"),
        ("Solution Explanation", "solution_explanation"),
        ("Verification Explanation", "verification_explanation"),
        ("Relevant Experience", "relevant_experience"),
    ):
        if not sections[heading]:
            sections[heading] = str(metadata.get(key, "")).strip()
    missing = sorted(heading for heading, body in sections.items() if not body)
    if missing:
        errors.append("submission metadata: missing/empty sections: " + ", ".join(missing))
    difficulty = sections["Difficulty Explanation"]
    role_re = re.compile(
        r"(?i)\b(engineer|developer|maintainer|operator|analyst|administrator|"
        r"researcher|specialist|team)\b"
    )
    origin_re = re.compile(
        r"(?i)\b(corpus|capture|trace|dataset|archive|fixture|generated|collected|"
        r"derived|recorded|synthetic|production|real[- ]world|no external data)\b"
    )
    if difficulty and not role_re.search(difficulty):
        errors.append("submission metadata: difficulty explanation must name a professional role")
    if difficulty and not origin_re.search(difficulty):
        errors.append(
            "submission metadata: difficulty explanation must state data origin/realism "
            "or explicitly say no external data"
        )
    scaffold_markers = (
        "TODO: summarize",
        "TODO: <=3 short paragraphs",
        "TODO: apply the reference solution",
        "TODO: 2-4 sentences of realistic project framing",
        "replace the TODO test bodies",
    )
    authored_paths = (
        task_dir / "instruction.md",
        task_dir / "task.toml",
        task_dir / "solution" / "solve.sh",
        task_dir / "tests" / "test_outputs.py",
        task_dir / "environment" / "app" / "README.md",
    )
    authored_text = text + "\n" + "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in authored_paths
        if path.is_file()
    )
    if any(marker in authored_text for marker in scaffold_markers):
        errors.append("submission/task snapshot: unresolved scaffold marker remains")


def validate_rubric_check(
    data: dict,
    submission: Path,
    report_dir: Path,
    style_data: dict,
    errors: list[str],
) -> None:
    label = "rubric-check.json"
    if data.get("schema_version") != 1 or data.get("status") != "pass":
        errors.append(f"{label}: schema_version/status mismatch")

    current = None
    results = data.get("results")
    if not isinstance(results, list) or not results:
        errors.append(f"{label}: non-empty results are required")
    else:
        for result in results:
            if not isinstance(result, dict) or not nonempty(result.get("path")):
                continue
            try:
                result_path = Path(str(result["path"])).resolve()
            except (OSError, RuntimeError):
                continue
            if (
                not result_path.is_file()
                or result.get("sha256") != sha256(result_path)
                or result.get("status") != "pass"
            ):
                errors.append(f"{label}: portfolio packet result is failing or stale")
            if result_path == submission.resolve():
                current = result
        if current is None:
            errors.append(f"{label}: exact current submission is absent from results")
        elif (
            current.get("status") != "pass"
            or current.get("errors") != []
            or not submission.is_file()
            or current.get("sha256") != sha256(submission)
        ):
            errors.append(f"{label}: current submission result is failing or stale")

    warnings = list(data.get("portfolio_warnings") or [])
    if isinstance(current, dict):
        warnings.extend(current.get("warnings") or [])
    if warnings:
        auditor = style_data.get("auditor") if isinstance(style_data, dict) else None
        transcript_value = auditor.get("transcript") if isinstance(auditor, dict) else None
        transcript_text = ""
        if nonempty(transcript_value):
            transcript_path = (report_dir / str(transcript_value)).resolve()
            try:
                transcript_path.relative_to(report_dir.resolve())
                transcript_text = transcript_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError, ValueError):
                transcript_text = ""
        missing_warnings = [warning for warning in warnings if warning not in transcript_text]
        if missing_warnings:
            errors.append(
                f"{label}: rubric warnings lack exact adjudications in style audit transcript"
            )

    coverage = data.get("coverage_matrix")
    expected_matrix = (report_dir / "rubric-coverage.md").resolve()
    if not isinstance(coverage, dict) or coverage.get("status") != "pass":
        errors.append(f"{label}: passing coverage_matrix evidence is required")
        return
    if not nonempty(coverage.get("path")):
        errors.append(f"{label}: coverage_matrix.path is required")
        return
    try:
        coverage_path = Path(str(coverage["path"])).resolve()
    except (OSError, RuntimeError) as exc:
        errors.append(f"{label}: invalid coverage matrix path: {exc}")
        return
    if coverage_path != expected_matrix:
        errors.append(f"{label}: coverage matrix must be {expected_matrix}")
    if (
        not coverage_path.is_file()
        or coverage_path.stat().st_size == 0
        or coverage.get("sha256") != sha256(coverage_path)
    ):
        errors.append(f"{label}: coverage matrix is missing, empty, or stale")
    if submission.is_file() and coverage_path.is_file():
        completed = subprocess.run(
            [
                sys.executable,
                str(RUBRIC_CHECKER),
                str(submission),
                "--coverage-matrix",
                str(coverage_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            errors.append(f"{label}: independent rubric checker failed")


def validate_style_audit(
    data: dict,
    slug: str,
    task_dir: Path,
    submission: Path,
    report_dir: Path,
    errors: list[str],
) -> None:
    if data.get("schema_version") != 2:
        errors.append("style-audit.json: schema_version must be 2")
    if data.get("task_slug") != slug or data.get("status") != "pass":
        errors.append("style-audit.json: task_slug/status mismatch")
    if data.get("task_snapshot_sha256") != tree_hash(task_dir, sanitized=False):
        errors.append("style-audit.json: task changed after style audit")
    if not submission.is_file() or data.get("submission_sha256") != sha256(submission):
        errors.append("style-audit.json: submission file hash mismatch")
    task_style = report_dir / EVIDENCE_FILES["task_style"]
    if not task_style.is_file() or data.get("task_style_preflight_sha256") != sha256(task_style):
        errors.append("style-audit.json: pre-freeze task-style receipt is missing or stale")
    surface = data.get("submission_surface")
    if (
        not isinstance(surface, dict)
        or surface.get("status") != "verified"
        or surface.get("sha256") != (sha256(submission) if submission.is_file() else None)
        or not nonempty(surface.get("path"))
        or Path(str(surface.get("path"))).resolve() != submission.resolve()
    ):
        errors.append("style-audit.json: submission surface receipt mismatch")
    auditor = data.get("auditor")
    if not isinstance(auditor, dict) or auditor.get("status") != "pass":
        errors.append("style-audit.json: passing auditor evidence is required")
        return
    for field in ("runtime", "model", "session_id", "transcript"):
        if not nonempty(auditor.get(field)):
            errors.append(f"style-audit.json: auditor.{field} is required")
    transcript_value = auditor.get("transcript")
    if nonempty(transcript_value):
        transcript = (report_dir / str(transcript_value)).resolve()
        try:
            transcript.relative_to(report_dir.resolve())
        except ValueError:
            errors.append("style-audit.json: auditor transcript escapes report directory")
        else:
            if not transcript.is_file() or transcript.stat().st_size == 0:
                errors.append("style-audit.json: auditor transcript missing or empty")
            elif auditor.get("transcript_sha256") != sha256(transcript):
                errors.append("style-audit.json: auditor transcript sha256 mismatch")


def validate_probe_bundle(
    slug: str,
    task_dir: Path,
    languages: list[str],
    probe_dir: Path,
    verifier: dict,
    semantic: dict,
    semantic_path: Path,
    profile: str,
    required_model: str | None,
    required_effort: str,
    errors: list[str],
    trusted_verifier: Callable[[Path], dict] = run_trusted_nop_verifier,
) -> dict:
    if not probe_dir.is_dir():
        errors.append(f"probe evidence directory not found: {probe_dir}")
        return {}
    manifest = load_json(probe_dir / "probe-manifest.json", errors)
    if manifest.get("schema_version") != 3:
        errors.append("probe-manifest.json: schema_version must be 3")
    if manifest.get("mode") != "counted":
        errors.append("probe-manifest.json: final handover requires counted mode")
    if manifest.get("profile") != profile:
        errors.append("probe-manifest.json: preparation profile differs from handover profile")
    if Path(str(manifest.get("report_dir", ""))).resolve() != semantic_path.parent.resolve():
        errors.append("probe-manifest.json: report_dir mismatch")
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
    if manifest.get("task_snapshot_sha256") != current_snapshot:
        errors.append("probe-manifest.json: counted task/verifier snapshot is stale")
    if not semantic_path.is_file() or manifest.get("semantic_coverage_sha256") != sha256(semantic_path):
        errors.append("probe-manifest.json: semantic coverage receipt is missing or stale")
    sufficiency_path = semantic_path.with_name(EVIDENCE_FILES["sufficiency"])
    sufficiency_manifest_value = manifest.get("instruction_sufficiency")
    if (
        not sufficiency_path.is_file()
        or not nonempty(sufficiency_manifest_value)
        or Path(str(sufficiency_manifest_value)).resolve() != sufficiency_path.resolve()
        or manifest.get("instruction_sufficiency_sha256") != sha256(sufficiency_path)
    ):
        errors.append("probe-manifest.json: V3 evidence-inferability receipt is missing or stale")
    verifier_path = semantic_path.with_name(EVIDENCE_FILES["verifier"])
    verifier_manifest_value = manifest.get("verifier_matrix")
    if (
        not verifier_path.is_file()
        or not nonempty(verifier_manifest_value)
        or Path(str(verifier_manifest_value)).resolve() != verifier_path.resolve()
        or manifest.get("verifier_matrix_sha256") != sha256(verifier_path)
    ):
        errors.append("probe-manifest.json: verifier matrix receipt is missing or stale")
    recorded_preprobe = manifest.get("preprobe_receipts")
    expected_preprobe = {
        filename: sha256(semantic_path.with_name(filename))
        for filename in (
            EVIDENCE_FILES["probe_preflight"],
            EVIDENCE_FILES["prefreeze_review"],
            EVIDENCE_FILES["task_style"],
            EVIDENCE_FILES["agent_session_budget"],
        )
        if semantic_path.with_name(filename).is_file()
    }
    if recorded_preprobe != expected_preprobe or len(expected_preprobe) != 4:
        errors.append(
            "probe-manifest.json: pre-probe technical/review/style/session receipts are stale"
        )
    current_contract_files = file_hash_map(task_dir, sanitized=True)
    current_full_files = file_hash_map(task_dir, sanitized=False)
    agent_sessions: set[str] = set()
    runtime_values: set[str] = set()
    model_values: set[str] = set()
    effort_values: set[str] = set()
    run_results: list[dict] = []
    setup_failures = 0
    all_failure_clusters: set[str] = set()
    all_failure_nodes: set[str] = set()
    test_nodes: dict[str, set[str]] = {}
    for key, prefix in (("mechanisms", "M"), ("interactions", "I")):
        rows = semantic.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or not nonempty(row.get("id")):
                continue
            for test_id in row.get("test_ids", []):
                if nonempty(test_id):
                    test_nodes.setdefault(str(test_id), set()).add(f"{prefix}:{row['id']}")

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
        failed_nodes = {
            node
            for unit_id in failed_ids
            for node in test_nodes.get(unit_id, set())
        }
        all_failure_clusters.update(failed_clusters)
        all_failure_nodes.update(failed_nodes)
        run_results.append(
            {
                "run": ordinal,
                "result": result_value,
                "passed_ids": passed_ids,
                "failed_ids": failed_ids,
                "failure_clusters": failed_clusters,
                "failure_nodes": failed_nodes,
            }
        )

    geometry = semantic_probe_geometry(run_results)
    solved_runs = geometry["solved_runs"]
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
    semantic_de_correlated = geometry["semantic_de_correlated"]
    advanced_geometry_pass = geometry["advanced_geometry_pass"]
    if profile in {"advanced_frontier_only", "core_advanced_frontier"}:
        errors.extend(validate_core_plus_outcome(result_count, solved_runs))
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
        "solver_session_ids": sorted(agent_sessions),
        "solved_runs": solved_runs,
        "setup_failures": setup_failures,
        "union_coverage": union_coverage,
        "common_miss_count": len(common_misses),
        "failure_clusters": sorted(all_failure_clusters),
        "failure_nodes": sorted(all_failure_nodes),
        "de_correlated": de_correlated,
        "semantic_de_correlated": semantic_de_correlated,
        "advanced_geometry_pass": advanced_geometry_pass,
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


def validate_final_session_budget(
    task_dir: Path,
    report_dir: Path,
    budget: dict,
    probe: dict,
    client_review: dict,
    style: dict,
    errors: list[str],
) -> dict:
    budget_errors, canonical = validate_session_budget_receipt(task_dir, report_dir)
    errors.extend(f"agent-session-budget.json: {error}" for error in budget_errors)
    if budget != canonical:
        errors.append("agent-session-budget.json: loaded receipt differs from canonical receipt")

    builder = canonical.get("builder", {}) if isinstance(canonical, dict) else {}
    fairness = canonical.get("fairness_reviewers", []) if isinstance(canonical, dict) else []
    auditor = canonical.get("consolidated_auditor", {}) if isinstance(canonical, dict) else {}
    role_policy = canonical.get("role_policy")
    single_reviewer = role_policy in {
        "single_reviewer_two_pass_v1",
        "fixed_five_roles_v2",
        "fixed_roles_unbounded_v3",
    }
    fixed_five = role_policy == "fixed_five_roles_v2"
    unbounded_roles = role_policy == "fixed_roles_unbounded_v3"
    prefreeze_ids = [
        builder.get("session_id") if isinstance(builder, dict) else None,
        *(
            item.get("session_id")
            for item in fairness
            if isinstance(item, dict)
        ),
        auditor.get("session_id") if isinstance(auditor, dict) else None,
    ]
    solver_ids = probe.get("solver_session_ids", []) if isinstance(probe, dict) else []
    if not isinstance(solver_ids, list) or len(solver_ids) != 2:
        errors.append("agent session budget: exactly two blind solver sessions are required")
        solver_ids = []
    all_ids = [item for item in (*prefreeze_ids, *solver_ids) if nonempty(item)]
    if len(all_ids) != len(set(all_ids)):
        errors.append("agent session budget: every builder/reviewer/optional-auditor/solver role must be distinct")

    final_reviewer = auditor if isinstance(auditor, dict) and auditor else (
        fairness[0] if single_reviewer and isinstance(fairness, list) and fairness else {}
    )
    expected_auditor = {
        field: final_reviewer.get(field) if isinstance(final_reviewer, dict) else None
        for field in ("runtime", "model", "session_id")
    }
    final_records = (
        ("style-audit.json auditor", style.get("auditor") if isinstance(style, dict) else None),
        (
            "client-review.json manual_review",
            client_review.get("manual_review") if isinstance(client_review, dict) else None,
        ),
    )
    if not single_reviewer or auditor:
        for label, record in final_records:
            actual = {
                field: record.get(field) if isinstance(record, dict) else None
                for field in ("runtime", "model", "session_id")
            }
            if actual != expected_auditor:
                errors.append(
                    f"{label}: post-probe review must reuse the consolidated pre-freeze auditor"
                )

    total = len(all_ids)
    external = total - 1 if nonempty(builder.get("session_id") if isinstance(builder, dict) else None) else 0
    if single_reviewer:
        expected_total = 1 + 1 + (1 if auditor else 0) + len(solver_ids)
        if not unbounded_roles and total != expected_total:
            errors.append(f"agent session budget: single-reviewer policy expected {expected_total} sessions, observed {total}")
        if fixed_five and (not auditor or total != 5):
            errors.append("agent session budget: fixed_five_roles_v2 requires builder, reviewer, auditor, and two solvers")
        if fixed_five or unbounded_roles:
            builder_runtime = str(builder.get("runtime", "")).lower()
            expected_probe_runtime = "claude-code" if "claude" in builder_runtime else "codex"
            if probe.get("probe_runtime") != expected_probe_runtime:
                errors.append("agent session budget: blind solvers must use the same runtime as the other roles")
    else:
        if total not in {6, 7}:
            errors.append(f"agent session budget: accepted task must use 6 or 7 sessions, observed {total}")
        if external not in {5, 6}:
            errors.append(
                f"agent session budget: accepted task must use 5 or 6 external sessions, observed {external}"
            )
    return {
        "builder_sessions": 1 if isinstance(builder, dict) and builder else 0,
        "fairness_reviewer_sessions": len(fairness) if isinstance(fairness, list) else 0,
        "consolidated_auditor_sessions": 1 if isinstance(auditor, dict) and auditor else 0,
        "blind_solver_sessions": len(solver_ids),
        "total_sessions": total,
        "external_sessions": external,
    }


def validate_role_session_alignment(
    budget: dict,
    quota_summary: dict,
    errors: list[str],
) -> None:
    """Bind reviewer and auditor session IDs to the quota ledger."""
    fairness = budget.get("fairness_reviewers", []) if isinstance(budget, dict) else []
    auditor = budget.get("consolidated_auditor", {}) if isinstance(budget, dict) else {}
    role_sessions = (
        quota_summary.get("completed_role_session_ids", {})
        if isinstance(quota_summary, dict)
        else {}
    )
    if not isinstance(role_sessions, dict):
        errors.append("quota ledger: completed_role_session_ids must be an object")
        return
    budget_fairness = {
        str(item.get("session_id"))
        for item in fairness
        if isinstance(item, dict) and nonempty(item.get("session_id"))
    }
    ledger_fairness = set(role_sessions.get("fairness_reviewer", []))
    if ledger_fairness != budget_fairness:
        errors.append(
            "quota ledger: reviewer session IDs do not match agent-session-budget.json"
        )
    budget_auditor = {
        str(auditor.get("session_id"))
        if isinstance(auditor, dict) and nonempty(auditor.get("session_id"))
        else ""
    } - {""}
    ledger_auditor = set(role_sessions.get("consolidated_auditor", []))
    if ledger_auditor != budget_auditor:
        errors.append(
            "quota ledger: auditor session ID does not match agent-session-budget.json"
        )


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


def zip_file_hash_map(path: Path, errors: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if "\\" in name or name.startswith("/") or ".." in Path(name).parts:
                    continue
                files[name] = hashlib.sha256(archive.read(info)).hexdigest()
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"zip payload: {exc}")
    return files


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
    parser.add_argument("--batch-index", type=Path)
    parser.add_argument("--expected-batch-size", type=int)
    parser.add_argument(
        "--incremental-batch",
        action="store_true",
        help="Allow a schema-v2 building index with 1..N accepted tasks.",
    )
    parser.add_argument(
        "--profile",
        choices=("general", "advanced_frontier_only", "core_advanced_frontier"),
        default="general",
    )
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    report_dir = args.report_dir.resolve()
    probe_dir = args.probe_dir.resolve()
    zip_path = args.zip_path.resolve()
    submission = args.submission.resolve()
    batch_index_path = args.batch_index.resolve() if args.batch_index else None
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
    if args.profile in {"advanced_frontier_only", "core_advanced_frontier"} and (
        batch_index_path is None or not args.expected_batch_size
    ):
        errors.append(
            "CORE+ handover requires --batch-index and --expected-batch-size"
        )
    if batch_index_path is not None:
        batch_index = load_json(batch_index_path, errors)
        if not args.expected_batch_size or args.expected_batch_size < 1:
            errors.append("--expected-batch-size must be a positive integer with --batch-index")
        elif evidence["design"]:
            validate_batch_index(
                batch_index,
                slug,
                report_dir,
                evidence["design"],
                args.expected_batch_size,
                errors,
                incremental=args.incremental_batch,
            )
            task_slugs = batch_index.get("task_slugs")
            if isinstance(task_slugs, list):
                candidate_ledger_path = batch_index_path.with_name(
                    f"{batch_index_path.stem}-pattern-mix.json"
                )
                validate_candidate_ledger(
                    candidate_ledger_path,
                    task_slugs,
                    args.incremental_batch,
                    errors,
                )
    if evidence["preflight"]:
        validate_preflight(evidence["preflight"], slug, task_dir, report_dir, errors)
    if evidence["client_review"]:
        validate_client_review(
            evidence["client_review"], slug, zip_path, report_dir, errors
        )
    if evidence["style"]:
        validate_style_audit(
            evidence["style"],
            slug,
            task_dir,
            submission,
            report_dir,
            errors,
        )
    if evidence["rubric"]:
        validate_rubric_check(
            evidence["rubric"],
            submission,
            report_dir,
            evidence["style"],
            errors,
        )
    verifier = (
        validate_verifier_matrix(evidence["verifier"], slug, report_dir, errors)
        if evidence["verifier"]
        else {}
    )
    probe_error_start = len(errors)
    preprobe_check = (
        Path(__file__).resolve().parents[1]
        / ".agent"
        / "skills"
        / "task-local-solve-probe"
        / "scripts"
        / "preprobe_check.py"
    )
    preprobe_result = subprocess.run(
        [
            sys.executable,
            str(preprobe_check),
            str(task_dir),
            str(report_dir),
            "--handover-revalidation",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if preprobe_result.returncode != 0:
        errors.append(
            "pre-probe gates: "
            + (preprobe_result.stdout + preprobe_result.stderr).replace("\n", "; ").strip()
        )
    semantic_check = (
        Path(__file__).resolve().parents[1]
        / ".agent"
        / "skills"
        / "terminus-regular-task-authoring"
        / "scripts"
        / "semantic_coverage_check.py"
    )
    semantic_command = [
        sys.executable,
        str(semantic_check),
    ]
    if args.profile in {"advanced_frontier_only", "core_advanced_frontier"}:
        semantic_command.append("--advanced-plus")
    semantic_command.extend(
        [
            str(task_dir),
            str(report_dir / EVIDENCE_FILES["semantic"]),
            str(report_dir / EVIDENCE_FILES["verifier"]),
        ]
    )
    semantic_result = subprocess.run(
        semantic_command,
        capture_output=True,
        text=True,
        check=False,
    )
    if semantic_result.returncode != 0:
        errors.append(
            "semantic coverage: "
            + (semantic_result.stdout + semantic_result.stderr).replace("\n", "; ").strip()
        )
    probe_derived = validate_probe_bundle(
        slug,
        task_dir,
        languages,
        probe_dir,
        verifier,
        evidence.get("semantic", {}),
        report_dir / EVIDENCE_FILES["semantic"],
        args.profile,
        args.required_probe_model,
        args.required_reasoning_effort,
        errors,
    )
    session_budget_derived = validate_final_session_budget(
        task_dir,
        report_dir,
        evidence.get("agent_session_budget", {}),
        probe_derived,
        evidence.get("client_review", {}),
        evidence.get("style", {}),
        errors,
    )
    quota_ledger_derived: dict = {}
    if evidence.get("quota_ledger"):
        quota_errors, quota_ledger_derived = validate_quota_ledger(
            evidence["quota_ledger"],
            report_dir / EVIDENCE_FILES["quota_ledger"],
            "handover",
        )
        errors.extend(f"quota ledger: {error}" for error in quota_errors)
        validate_role_session_alignment(
            evidence.get("agent_session_budget", {}),
            quota_ledger_derived,
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
        [
            sys.executable,
            str(sufficiency_check),
            "--require-v3",
            str(task_dir),
            str(report_dir / EVIDENCE_FILES["sufficiency"]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if sufficiency.returncode != 0:
        errors.append("evidence inferability: " + sufficiency.stdout.replace("\n", "; ").strip())

    if not zip_path.is_file():
        errors.append(f"zip not found: {zip_path}")
    else:
        validate_zip(zip_path, errors)
        zip_files = zip_file_hash_map(zip_path, errors)
        task_files = file_hash_map(task_dir, sanitized=False)
        if zip_files != task_files:
            missing = sorted(set(task_files) - set(zip_files))
            extra = sorted(set(zip_files) - set(task_files))
            changed = sorted(
                name
                for name in set(task_files) & set(zip_files)
                if task_files[name] != zip_files[name]
            )
            errors.append(
                "zip: payload is not byte-identical to the current task tree"
                + (f"; missing={missing}" if missing else "")
                + (f"; extra={extra}" if extra else "")
                + (f"; changed={changed}" if changed else "")
            )
        if evidence["preflight"] and evidence["preflight"].get("artifact_sha256") != sha256(zip_path):
            errors.append("preflight.json: artifact_sha256 does not match the current ZIP")
    validate_submission(submission, task_dir, errors)

    artifact_sha = sha256(zip_path) if zip_path.is_file() else None
    payload = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "handover_script_sha256": sha256(Path(__file__)),
        "task_slug": slug,
        "status": "candidate_ready" if not errors else "unverified",
        "task_snapshot_sha256": tree_hash(task_dir, sanitized=False),
        "artifact": str(zip_path),
        "artifact_sha256": artifact_sha,
        "submission": str(submission),
        "submission_sha256": sha256(submission) if submission.is_file() else None,
        "evidence": {
            key: {
                "path": str(report_dir / filename),
                "sha256": sha256(report_dir / filename)
                if (report_dir / filename).is_file()
                else None,
            }
            for key, filename in EVIDENCE_FILES.items()
        },
        "probe_evidence": str(probe_dir),
        "batch_index": {
            "path": str(batch_index_path) if batch_index_path else None,
            "sha256": sha256(batch_index_path)
            if batch_index_path and batch_index_path.is_file()
            else None,
            "incremental": args.incremental_batch,
        },
        "probe_derived": probe_derived,
        "session_budget_derived": session_budget_derived,
        "quota_ledger_derived": quota_ledger_derived,
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
