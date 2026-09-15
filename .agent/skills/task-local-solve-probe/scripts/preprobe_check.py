#!/usr/bin/env python3
"""Validate the frozen technical, review, and prose receipts before blind solves."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


SESSION_BUDGET_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "task-batch" / "scripts"
)
sys.path.insert(0, str(SESSION_BUDGET_SCRIPTS))
from session_budget import validate_receipt as validate_session_budget  # noqa: E402
from quota_guard import validate as validate_quota_ledger  # noqa: E402


VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
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
REQUIRED_PREFLIGHT_CHECKS = {
    "policy:static",
    "verifier:reward-dir-mode",
    "docker:daemon",
    "docker:agent-build",
    "docker:verifier-build",
    "docker:oracle",
    "docker:nop",
    "docker:noexec-tmp",
}
REQUIRED_PREFLIGHT_FILES = {
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


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def artifact_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def style_surface_hashes(task_dir: Path) -> dict[str, str]:
    surfaces: dict[str, str] = {}
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file() or any(
            part in VOLATILE_DIRS for part in path.relative_to(task_dir).parts
        ):
            continue
        if path.name != "Dockerfile" and path.suffix.lower() not in STYLE_TEXT_SUFFIXES:
            continue
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        surfaces[path.relative_to(task_dir).as_posix()] = sha256(path)
    return surfaces


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name}: root must be an object")
        return {}
    return value


def receipt_path(report_dir: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label}: path is required")
        return None
    candidate = Path(str(value))
    path = candidate.resolve() if candidate.is_absolute() else (report_dir / candidate).resolve()
    try:
        path.relative_to(report_dir.resolve())
    except ValueError:
        errors.append(f"{label}: evidence must stay inside the report directory")
        return None
    if not path.is_file():
        errors.append(f"{label}: evidence file is missing")
        return None
    return path


def ctrf_statuses(path: Path, label: str, errors: list[str]) -> list[str]:
    data = load_json(path, errors)
    tests = data.get("tests")
    if not isinstance(tests, list):
        results = data.get("results")
        tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list) or not tests:
        errors.append(f"{label}: CTRF tests must be non-empty")
        return []
    statuses: list[str] = []
    for item in tests:
        status = str(item.get("status", "")).lower() if isinstance(item, dict) else ""
        if status not in {"pass", "passed", "fail", "failed"}:
            errors.append(f"{label}: unsupported CTRF status {status!r}")
        statuses.append(status)
    return statuses


def validate_preflight(task_dir: Path, report_dir: Path, errors: list[str]) -> None:
    path = report_dir / "probe-preflight.json"
    data = load_json(path, errors)
    if data.get("task_slug") != task_dir.name:
        errors.append("probe-preflight.json: task_slug mismatch")
    if data.get("status") != "pass" or data.get("strict") is not True or data.get("fail_count") != 0:
        errors.append("probe-preflight.json: strict preflight must pass")
    if data.get("task_snapshot_sha256") != tree_hash(task_dir):
        errors.append("probe-preflight.json: task snapshot is stale")
    checks = data.get("checks")
    check_status = {
        item.get("check"): item.get("status")
        for item in checks
        if isinstance(item, dict)
    } if isinstance(checks, list) else {}
    missing = sorted(REQUIRED_PREFLIGHT_CHECKS - set(check_status))
    failed = sorted(
        name for name in REQUIRED_PREFLIGHT_CHECKS if check_status.get(name) != "pass"
    )
    if missing:
        errors.append("probe-preflight.json: missing checks: " + ", ".join(missing))
    if failed:
        errors.append("probe-preflight.json: checks not passing: " + ", ".join(failed))
    evidence = data.get("evidence_files")
    if not isinstance(evidence, dict):
        errors.append("probe-preflight.json: evidence_files is required")
        return
    missing_files = sorted(REQUIRED_PREFLIGHT_FILES - set(evidence))
    if missing_files:
        errors.append("probe-preflight.json: missing evidence: " + ", ".join(missing_files))
    resolved: dict[str, Path] = {}
    for name in REQUIRED_PREFLIGHT_FILES & set(evidence):
        receipt = evidence[name]
        if not isinstance(receipt, dict):
            errors.append(f"probe-preflight.json: invalid evidence receipt for {name}")
            continue
        evidence_path = receipt_path(report_dir, receipt.get("path"), name, errors)
        if evidence_path is None:
            continue
        resolved[name] = evidence_path
        if receipt.get("sha256") != sha256(evidence_path):
            errors.append(f"probe-preflight.json: sha256 mismatch for {name}")
        if receipt.get("size") != evidence_path.stat().st_size:
            errors.append(f"probe-preflight.json: size mismatch for {name}")
    for label, expected_reward, all_pass in (
        ("oracle", "1", True),
        ("nop", "0", False),
        ("oracle-noexec", "1", True),
    ):
        reward = resolved.get(f"{label}-reward.txt")
        if reward and reward.read_text(errors="replace").strip() != expected_reward:
            errors.append(f"probe-preflight.json: {label} reward mismatch")
        ctrf = resolved.get(f"{label}-ctrf.json")
        if ctrf:
            statuses = ctrf_statuses(ctrf, label, errors)
            has_failure = any(status in {"fail", "failed"} for status in statuses)
            if all_pass and has_failure:
                errors.append(f"probe-preflight.json: {label} CTRF contains failures")
            if not all_pass and statuses and not has_failure:
                errors.append("probe-preflight.json: NOP CTRF contains no failures")


def validate_manual_review(
    manual: object,
    report_dir: Path,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(manual, dict) or manual.get("status") != "pass":
        errors.append(f"{label}: passing manual review is required")
        return
    for field in ("runtime", "model", "session_id"):
        if not nonempty(manual.get(field)):
            errors.append(f"{label}: {field} is required")
    transcript = receipt_path(report_dir, manual.get("transcript"), f"{label}.transcript", errors)
    if transcript and manual.get("transcript_sha256") != sha256(transcript):
        errors.append(f"{label}: transcript sha256 mismatch")


def validate_review(task_dir: Path, report_dir: Path, errors: list[str]) -> None:
    path = report_dir / "pre-freeze-review.json"
    data = load_json(path, errors)
    if data.get("schema_version") != 1:
        errors.append("pre-freeze-review.json: schema_version must be 1")
    scanner = (
        Path(__file__).resolve().parents[2]
        / "task-client-feedback-review"
        / "scripts"
        / "review_task.py"
    )
    if not scanner.is_file() or data.get("scanner_sha256") != sha256(scanner):
        errors.append("pre-freeze-review.json: scanner hash is stale")
    results = data.get("results")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        errors.append("pre-freeze-review.json: exactly one task result is required")
    else:
        result = results[0]
        if result.get("task") != task_dir.name or result.get("status") != "ready":
            errors.append("pre-freeze-review.json: task/status mismatch")
        if result.get("artifact_sha256") != artifact_hash(task_dir):
            errors.append("pre-freeze-review.json: task changed after review")
        counts = result.get("counts")
        # Scanner heuristics intentionally preserve possible false positives in
        # the raw receipt.  A passing independent manual review is the evidence
        # that resolves those non-blocking findings; unresolved blockers still
        # stop the freeze unconditionally.
        if not isinstance(counts, dict) or counts.get("blocker") != 0:
            errors.append("pre-freeze-review.json: blocker findings remain")
    validate_manual_review(data.get("manual_review"), report_dir, "pre-freeze-review.json", errors)


def validate_style(task_dir: Path, report_dir: Path, errors: list[str]) -> None:
    path = report_dir / "task-style-preflight.json"
    data = load_json(path, errors)
    if data.get("schema_version") != 1 or data.get("status") != "pass":
        errors.append("task-style-preflight.json: schema/status mismatch")
    if data.get("task_slug") != task_dir.name or data.get("task_snapshot_sha256") != tree_hash(task_dir):
        errors.append("task-style-preflight.json: task snapshot is stale")
    surfaces = data.get("surfaces")
    recorded = {
        str(item.get("path")): str(item.get("sha256"))
        for item in surfaces
        if isinstance(item, dict) and item.get("status") == "verified"
    } if isinstance(surfaces, list) else {}
    if recorded != style_surface_hashes(task_dir):
        errors.append("task-style-preflight.json: surface inventory/hash mismatch")
    validate_manual_review(data.get("auditor"), report_dir, "task-style-preflight.json", errors)


def validate_quota_override(path: Path | None, task_dir: Path, report_dir: Path) -> bool:
    if path is None:
        return False
    path = path.resolve()
    try:
        path.relative_to(report_dir.resolve())
    except ValueError:
        return False
    data = load_json(path, [])
    return (
        data.get("schema_version") == 1
        and data.get("status") == "authorized"
        and data.get("task_slug") == task_dir.name
        and data.get("authorized_by") == "user"
        and set(data.get("scope", [])) == {"pre_solver_reserve", "model_turn_limit"}
        and data.get("preserve_original_quota_evidence") is True
    )


def validate(
    task_dir: Path,
    report_dir: Path,
    quota_override: Path | None = None,
    handover_revalidation: bool = False,
) -> list[str]:
    errors: list[str] = []
    task_dir = task_dir.resolve()
    report_dir = report_dir.resolve()
    if report_dir.name != task_dir.name:
        errors.append("report directory name must match task slug")
    validate_preflight(task_dir, report_dir, errors)
    validate_review(task_dir, report_dir, errors)
    validate_style(task_dir, report_dir, errors)
    budget_errors, _ = validate_session_budget(task_dir, report_dir)
    errors.extend(f"session budget: {error}" for error in budget_errors)
    quota_path = report_dir / "quota-ledger.json"
    quota_data = load_json(quota_path, errors)
    if quota_data:
        quota_errors, _ = validate_quota_ledger(quota_data, quota_path, "pre-solver")
        if handover_revalidation:
            quota_errors = [
                error
                for error in quota_errors
                if error != "pre-solver ledger already contains blind-solver turns"
            ]
        if validate_quota_override(quota_override, task_dir, report_dir):
            allowed = (
                "pre-solver reserve is too small:",
                "model turn limit exceeded:",
            )
            quota_errors = [error for error in quota_errors if not error.startswith(allowed)]
        errors.extend(f"quota ledger: {error}" for error in quota_errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("--quota-run-override", type=Path)
    parser.add_argument("--handover-revalidation", action="store_true")
    args = parser.parse_args()
    errors = validate(
        args.task_dir,
        args.report_dir,
        args.quota_run_override,
        args.handover_revalidation,
    )
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(
        f"PASS: {args.task_dir.name} is frozen, reviewed, styled, "
        "role/turn-budgeted, and Oracle/NOP-clean"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
