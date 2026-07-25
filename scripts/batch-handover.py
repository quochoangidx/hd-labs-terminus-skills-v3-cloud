#!/usr/bin/env python3
"""Fail-closed handover gate for autonomous task batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path


EVIDENCE_FILES = {
    "category": "category-screen.json",
    "design": "design-signature.json",
    "preflight": "preflight.json",
    "probe": "probe-verdict.json",
    "sufficiency": "instruction-sufficiency.json",
}
SIGNATURE_AXES = {
    "work_surface",
    "interaction",
    "input_surface",
    "oracle_type",
    "verifier_type",
    "failure_mode",
}
OPEN_CATEGORIES = {"games", "machine-learning", "system-administration"}
BLOCK_CATEGORY_RULES = {"R1", "R2", "R3", "R4", "R5", "R6", "R7"}
PROBE_PROFILES = {
    "codex": ("gpt-5.5",),
    "claude-code": ("opus-4.8", "opus 4.8", "claude-opus-4.8"),
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


def validate_category(data: dict, slug: str, declared: str, errors: list[str]) -> None:
    if data.get("status") != "pass":
        errors.append("category-screen.json: status must be 'pass'")
    if data.get("task_slug") != slug:
        errors.append("category-screen.json: task_slug mismatch")
    if data.get("declared_category") != declared:
        errors.append("category-screen.json: declared_category mismatch")
    if data.get("predicted_category") not in OPEN_CATEGORIES:
        errors.append("category-screen.json: predicted_category is not open")
    if data.get("predicted_category") != declared:
        errors.append("category-screen.json: predicted_category must match declared_category")
    rules = data.get("rules_fired")
    evidence = data.get("evidence")
    if not isinstance(rules, list):
        errors.append("category-screen.json: rules_fired must be a list")
    elif BLOCK_CATEGORY_RULES.intersection(rules):
        errors.append("category-screen.json: a BLOCK rule fired")
    if not isinstance(evidence, list) or not evidence or not all(nonempty(x) for x in evidence):
        errors.append("category-screen.json: evidence must contain visible-shape citations")
    if rules == []:
        fallback = data.get("fallback_probe")
        if not isinstance(fallback, dict) or fallback.get("status") != "pass":
            errors.append("category-screen.json: no fired rule requires a passing fallback_probe")


def validate_design(data: dict, slug: str, errors: list[str]) -> None:
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


def validate_probe(
    data: dict,
    slug: str,
    required_model: str | None,
    required_effort: str,
    errors: list[str],
) -> None:
    if data.get("status") != "submit_ready":
        errors.append("probe-verdict.json: status must be 'submit_ready'")
    if data.get("task_slug") != slug:
        errors.append("probe-verdict.json: task_slug mismatch")
    runtime = str(data.get("probe_runtime", "")).strip().lower().replace("_", "-")
    if runtime not in PROBE_PROFILES:
        errors.append("probe-verdict.json: probe_runtime must be 'codex' or 'claude-code'")
        accepted_models: tuple[str, ...] = ()
    else:
        accepted_models = PROBE_PROFILES[runtime]
    if required_model:
        accepted_models = (required_model,)
    model = str(data.get("probe_model", "")).lower()
    if not model or not any(candidate.lower() in model for candidate in accepted_models):
        expected = ", ".join(accepted_models) if accepted_models else "the runtime profile model"
        errors.append(f"probe-verdict.json: probe_model must identify one of: {expected}")
    if data.get("reasoning_effort") != required_effort:
        errors.append(f"probe-verdict.json: reasoning_effort must be {required_effort!r}")
    runs = data.get("semantic_runs")
    if not isinstance(runs, int) or isinstance(runs, bool) or not 2 <= runs <= 3:
        errors.append("probe-verdict.json: semantic_runs must be 2 or 3")
    if data.get("setup_failures") != 0:
        errors.append("probe-verdict.json: setup_failures must be 0")
    if data.get("union_coverage") != 1.0:
        errors.append("probe-verdict.json: union_coverage must be 1.0")
    if data.get("common_miss_count") != 0:
        errors.append("probe-verdict.json: common_miss_count must be 0")
    clusters = data.get("failure_clusters")
    if not isinstance(clusters, list) or len(clusters) < 2:
        errors.append("probe-verdict.json: at least two de-correlated failure clusters are required")


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
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--required-probe-model")
    parser.add_argument("--required-reasoning-effort", default="medium")
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    report_dir = args.report_dir.resolve()
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
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"task.toml: {exc}")
        declared = ""
    if declared not in OPEN_CATEGORIES:
        errors.append(f"task.toml: {declared!r} is not open for net-new submissions")

    evidence = {
        key: load_json(report_dir / filename, errors)
        for key, filename in EVIDENCE_FILES.items()
    }
    if evidence["category"]:
        validate_category(evidence["category"], slug, declared, errors)
    if evidence["design"]:
        validate_design(evidence["design"], slug, errors)
    if evidence["preflight"]:
        validate_preflight(evidence["preflight"], slug, errors)
    if evidence["probe"]:
        validate_probe(
            evidence["probe"],
            slug,
            args.required_probe_model,
            args.required_reasoning_effort,
            errors,
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
        "status": "delivered" if not errors else "unverified",
        "artifact": str(zip_path),
        "artifact_sha256": artifact_sha,
        "submission": str(submission),
        "evidence": {key: str(report_dir / filename) for key, filename in EVIDENCE_FILES.items()},
        "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    if errors:
        print(f"UNVERIFIED: {slug} has {len(errors)} blocking finding(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"DELIVERED: {slug} ({artifact_sha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
