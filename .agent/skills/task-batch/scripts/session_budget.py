#!/usr/bin/env python3
"""Create and validate task-batch role-session receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


SOURCE_RECEIPTS = (
    "instruction-sufficiency.json",
    "semantic-coverage.json",
    "pre-freeze-review.json",
    "task-style-preflight.json",
)
LEGACY_POLICY = {
    "builder_sessions": 1,
    "fairness_reviewer_sessions": 2,
    "consolidated_auditor_sessions": 1,
    "initial_blind_solver_sessions": 2,
    "max_adaptive_blind_solver_sessions": 1,
    "accepted_total_sessions_min": 6,
    "accepted_total_sessions_max": 7,
    "accepted_external_sessions_min": 5,
    "accepted_external_sessions_max": 6,
}
LEGACY_FIXED_FIVE_POLICY_NAME = "fixed_five_roles_v2"
SINGLE_REVIEWER_POLICY_NAME = "fixed_roles_unbounded_v3"
SINGLE_REVIEWER_POLICY = {
    "builder_sessions": 1,
    "reviewer_sessions": 1,
    "required_review_phases": ["contract_review", "final_review"],
    "consolidated_auditor_sessions": 1,
    "required_valid_blind_solver_results": 2,
    "failed_attempt_limit": None,
    "remediation_limit": None,
}
IDENTITY_FIELDS = ("runtime", "model", "session_id")
SOL_MODEL = "gpt-5.6-sol"
LUNA_MODEL = "gpt-5.6-luna"
LUNA_RUNTIME = "codex-thread"


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def identity(record: object, label: str, errors: list[str]) -> dict[str, str]:
    if not isinstance(record, dict):
        errors.append(f"{label}: identity must be an object")
        return {}
    result: dict[str, str] = {}
    for field in IDENTITY_FIELDS:
        value = record.get(field)
        if not nonempty(value):
            errors.append(f"{label}.{field} is required")
        else:
            result[field] = str(value)
    return result


def audit_identity(record: object, label: str, errors: list[str]) -> dict[str, str]:
    result = identity(record, label, errors)
    if not isinstance(record, dict):
        return result
    for field in ("transcript", "transcript_sha256"):
        value = record.get(field)
        if not nonempty(value):
            errors.append(f"{label}.{field} is required")
        else:
            result[field] = str(value)
    return result


def validate_role_route(
    role: dict[str, str], label: str, expected_model: str, errors: list[str],
    *, expected_runtime: str | None = None,
) -> None:
    if role.get("model") != expected_model:
        errors.append(f"{label}.model must be {expected_model}")
    if expected_runtime is not None and role.get("runtime") != expected_runtime:
        errors.append(f"{label}.runtime must be {expected_runtime}")


def is_default_reviewer(role: dict[str, str]) -> bool:
    model = role.get("model", "")
    return model == SOL_MODEL or model == "opus-5" or model.startswith("claude-opus-5")


def validate_runtime_model(role: dict[str, str], label: str, errors: list[str]) -> None:
    runtime = role.get("runtime", "").lower()
    model = role.get("model", "")
    if "claude" in runtime:
        if not (model in {"opus", "opus-5"} or model.startswith("claude-opus-5")):
            errors.append(f"{label}.model must be Opus 5 for Claude")
    elif "codex" in runtime:
        if model != SOL_MODEL:
            errors.append(f"{label}.model must be {SOL_MODEL} for Codex")
    else:
        errors.append(f"{label}.runtime must identify Codex or Claude")


def runtime_family(role: dict[str, str]) -> str:
    runtime = role.get("runtime", "").lower()
    if "claude" in runtime:
        return "claude"
    if "codex" in runtime:
        return "codex"
    return ""


def derive_roles(report_dir: Path, errors: list[str]) -> tuple[list[dict[str, str]], dict[str, str], str]:
    sufficiency = load_json(report_dir / "instruction-sufficiency.json", errors)
    semantic = load_json(report_dir / "semantic-coverage.json", errors)
    review = load_json(report_dir / "pre-freeze-review.json", errors)
    style = load_json(report_dir / "task-style-preflight.json", errors)

    fairness = sufficiency.get("fairness_review", {})
    reviewers = fairness.get("reviewers") if isinstance(fairness, dict) else None
    if not isinstance(reviewers, list) or len(reviewers) != 1:
        errors.append("instruction-sufficiency.json: exactly one fairness reviewer is required")
        reviewers = []
    fairness_roles: list[dict[str, str]] = []
    for index, reviewer in enumerate(reviewers):
        role = identity(reviewer, f"fairness reviewer {index + 1}", errors)
        if isinstance(reviewer, dict) and nonempty(reviewer.get("reviewer_id")):
            role["reviewer_id"] = str(reviewer["reviewer_id"])
        if isinstance(reviewer, dict):
            if reviewer.get("fresh_context") is not True:
                errors.append(f"fairness reviewer {index + 1}: fresh_context must be true")
            if reviewer.get("task_visible_only") is not True:
                errors.append(f"fairness reviewer {index + 1}: task_visible_only must be true")
        validate_runtime_model(role, f"fairness reviewer {index + 1}", errors)
        fairness_roles.append(role)

    audit_records = (
        ("semantic-coverage.json review", semantic.get("review")),
        ("pre-freeze-review.json manual_review", review.get("manual_review")),
        ("task-style-preflight.json auditor", style.get("auditor")),
    )
    audits = [audit_identity(record, label, errors) for label, record in audit_records]
    consolidated = audits[0] if audits else {}
    if any(candidate != consolidated for candidate in audits[1:]):
        errors.append(
            "pre-freeze semantic, folder, and task-style receipts must share one exact "
            "auditor identity and transcript provenance"
        )
    validate_runtime_model(consolidated, "consolidated auditor", errors)
    reviewer_identity = {field: fairness_roles[0].get(field) for field in IDENTITY_FIELDS} if fairness_roles else {}
    audit_identity_only = {field: consolidated.get(field) for field in IDENTITY_FIELDS}
    if audit_identity_only == reviewer_identity:
        errors.append("consolidated auditor must be distinct from the fairness reviewer")
    return fairness_roles, consolidated, SINGLE_REVIEWER_POLICY_NAME


def source_hashes(report_dir: Path, errors: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in SOURCE_RECEIPTS:
        path = report_dir / name
        if not path.is_file():
            errors.append(f"{name}: source receipt is missing")
        else:
            result[name] = sha256(path)
    return result


def build_receipt(
    task_dir: Path,
    report_dir: Path,
    builder: dict[str, str],
) -> tuple[dict, list[str]]:
    errors: list[str] = []
    if report_dir.name != task_dir.name:
        errors.append("report directory name must match task slug")
    builder_role = identity(builder, "builder", errors)
    validate_runtime_model(builder_role, "builder", errors)
    fairness, auditor, role_policy = derive_roles(report_dir, errors)
    role_sessions = [
        builder_role.get("session_id", ""),
        *(item.get("session_id", "") for item in fairness),
        auditor.get("session_id", ""),
    ]
    nonempty_sessions = [item for item in role_sessions if item]
    if len(nonempty_sessions) != len(set(nonempty_sessions)):
        errors.append("builder, reviewer, and auditor must be distinct sessions")
    families = {
        runtime_family(role)
        for role in (builder_role, *fairness, auditor)
        if role
    }
    if len(families) != 1 or "" in families:
        errors.append("builder, reviewer, and auditor must use the same active runtime")
    policy = SINGLE_REVIEWER_POLICY if role_policy == SINGLE_REVIEWER_POLICY_NAME else LEGACY_POLICY
    payload = {
        "schema_version": 3 if role_policy == SINGLE_REVIEWER_POLICY_NAME else 2,
        "role_policy": role_policy,
        "task_slug": task_dir.name,
        "status": "pass" if not errors else "fail",
        "builder": builder_role,
        "fairness_reviewers": fairness,
        "consolidated_auditor": auditor,
        "source_receipts": source_hashes(report_dir, errors),
        "policy": policy,
    }
    if errors:
        payload["status"] = "fail"
    return payload, errors


def validate_receipt(task_dir: Path, report_dir: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    path = report_dir / "agent-session-budget.json"
    receipt = load_json(path, errors)
    if not receipt:
        return errors, {}
    role_policy = receipt.get("role_policy", "legacy_luna_v1")
    current_policy = role_policy == SINGLE_REVIEWER_POLICY_NAME
    historical_single_reviewer = role_policy == LEGACY_FIXED_FIVE_POLICY_NAME
    expected_schema = 3 if current_policy or historical_single_reviewer else 2
    if receipt.get("schema_version") != expected_schema:
        errors.append(f"agent-session-budget.json: schema_version must be {expected_schema}")
    if receipt.get("task_slug") != task_dir.name or receipt.get("status") != "pass":
        errors.append("agent-session-budget.json: task_slug/status mismatch")
    expected_policy = (
        SINGLE_REVIEWER_POLICY
        if current_policy
        else receipt.get("policy")
        if historical_single_reviewer
        else LEGACY_POLICY
    )
    if receipt.get("policy") != expected_policy:
        errors.append("agent-session-budget.json: role policy mismatch")

    builder = identity(receipt.get("builder"), "agent-session-budget.json builder", errors)
    expected, derive_errors = build_receipt(task_dir, report_dir, builder)
    errors.extend(derive_errors)
    for field in ("builder", "fairness_reviewers", "consolidated_auditor", "source_receipts"):
        if receipt.get(field) != expected.get(field):
            errors.append(f"agent-session-budget.json: {field} is stale or inconsistent")
    return errors, receipt


def create(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    report_dir = args.report_dir.resolve()
    builder = {
        "runtime": args.builder_runtime,
        "model": args.builder_model,
        "session_id": args.builder_session_id,
    }
    payload, errors = build_receipt(task_dir, report_dir, builder)
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    output = (args.output or report_dir / "agent-session-budget.json").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE: {output} ({payload['role_policy']})")
    return 0


def check(args: argparse.Namespace) -> int:
    errors, _ = validate_receipt(args.task_dir.resolve(), args.report_dir.resolve())
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"PASS: {args.task_dir.name} pre-freeze role receipt is valid")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("task_dir", type=Path)
    create_parser.add_argument("report_dir", type=Path)
    create_parser.add_argument("--builder-runtime", required=True)
    create_parser.add_argument("--builder-model", required=True)
    create_parser.add_argument("--builder-session-id", required=True)
    create_parser.add_argument("--output", type=Path)
    create_parser.set_defaults(func=create)
    check_parser = sub.add_parser("check")
    check_parser.add_argument("task_dir", type=Path)
    check_parser.add_argument("report_dir", type=Path)
    check_parser.set_defaults(func=check)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
