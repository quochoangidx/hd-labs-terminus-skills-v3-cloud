#!/usr/bin/env python3
"""Validate model routing, turn accounting, remediation caps, and role leases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BUILDER_MODEL = "gpt-5.6-sol"
REVIEW_MODEL = "gpt-5.6-luna"
SOLVER_MODEL = "gpt-5.6-sol"
ROLE_PROFILES = {
    "builder": (BUILDER_MODEL, "medium"),
    "fairness_reviewer": (REVIEW_MODEL, "high"),
    "consolidated_auditor": (REVIEW_MODEL, "max"),
    "blind_solver": (SOLVER_MODEL, "medium"),
}
ROLE_SURFACES = {
    "builder": "collaboration_subagent",
    "fairness_reviewer": "codex_thread",
    "consolidated_auditor": "codex_thread",
    "blind_solver": "collaboration_subagent",
}
ROLES = {
    "builder",
    "fairness_reviewer",
    "consolidated_auditor",
    "blind_solver",
}
STATUSES = {"complete", "failed", "interrupted", "usage_limited", "superseded"}
GATES = {
    "instruction_preflight",
    "client_scanner",
    "strict_preflight",
    "artifact_independence",
    "anti_cheat",
}
BUILDER_PURPOSES = {"design_build", "fairness_remediation", "auditor_remediation"}
REPORT_KINDS = {
    "durable_memory",
    "pattern_catalog",
    "batch_portfolio",
    "prior_rejection",
    "reviewer_feedback",
    "auditor_feedback",
}


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read quota ledger: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError("quota ledger root must be an object")
    return data


def validate_evidence(
    ledger_path: Path, name: str, record: object, errors: list[str]
) -> None:
    if not isinstance(record, dict) or record.get("status") != "pass":
        errors.append(f"mechanical_gates.{name}: passing record is required")
        return
    raw_path = record.get("evidence")
    if not nonempty(raw_path):
        errors.append(f"mechanical_gates.{name}.evidence is required")
        return
    candidate = Path(str(raw_path))
    path = candidate.resolve() if candidate.is_absolute() else (ledger_path.parent / candidate).resolve()
    try:
        path.relative_to(ledger_path.parent.resolve())
    except ValueError:
        errors.append(f"mechanical_gates.{name}: evidence must stay in the task report directory")
        return
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"mechanical_gates.{name}: evidence is missing or empty")
        return
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if record.get("sha256") != actual:
        errors.append(f"mechanical_gates.{name}: evidence sha256 is stale")


def validate_report_input(
    ledger_path: Path, record: object, label: str, errors: list[str]
) -> str | None:
    if not isinstance(record, dict):
        errors.append(f"{label}: must be an object")
        return None
    kind = record.get("kind")
    if kind not in REPORT_KINDS:
        errors.append(f"{label}.kind is invalid")
    raw_path = record.get("path")
    if not nonempty(raw_path):
        errors.append(f"{label}.path is required")
        return str(kind) if isinstance(kind, str) else None
    candidate = Path(str(raw_path))
    path = candidate.resolve() if candidate.is_absolute() else (ledger_path.parent / candidate).resolve()
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"{label}: report input is missing or empty")
        return str(kind) if isinstance(kind, str) else None
    if record.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
        errors.append(f"{label}: report input sha256 is stale")
    return str(kind) if isinstance(kind, str) else None


def validate_critique_receipt(
    ledger_path: Path, turn: dict[str, Any], label: str, errors: list[str]
) -> None:
    record = turn.get("critique_receipt")
    if not isinstance(record, dict):
        errors.append(f"{label}.critique_receipt is required for remediation")
        return
    raw_path = record.get("path")
    if not nonempty(raw_path):
        errors.append(f"{label}.critique_receipt.path is required")
        return
    candidate = Path(str(raw_path))
    path = candidate.resolve() if candidate.is_absolute() else (ledger_path.parent / candidate).resolve()
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"{label}.critique_receipt is missing or empty")
        return
    if record.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
        errors.append(f"{label}.critique_receipt sha256 is stale")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}.critique_receipt is invalid JSON: {exc}")
        return
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list) or not findings:
        errors.append(f"{label}.critique_receipt.findings must be non-empty")
        return
    for index, finding in enumerate(findings):
        finding_label = f"{label}.critique_receipt.findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{finding_label} must be an object")
            continue
        if not nonempty(finding.get("finding_id")):
            errors.append(f"{finding_label}.finding_id is required")
        if finding.get("disposition") not in {"accept", "challenge", "partial"}:
            errors.append(f"{finding_label}.disposition is invalid")
        if not nonempty(finding.get("evidence")) or not nonempty(finding.get("action")):
            errors.append(f"{finding_label}.evidence and action are required")


def validate_role_lease_receipts(
    ledger_path: Path,
    records: object,
    phase: str,
    task_slug: object,
    completed_sessions: dict[str, set[str]],
    errors: list[str],
) -> dict[str, list[str]]:
    sessions = {"fairness_reviewer": [], "consolidated_auditor": []}
    if not isinstance(records, list):
        errors.append("role_lease_receipts must be an array")
        return sessions
    leases: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for index, record in enumerate(records):
        label = f"role_lease_receipts[{index}]"
        if not isinstance(record, dict) or not nonempty(record.get("path")):
            errors.append(f"{label}.path is required")
            continue
        candidate = Path(str(record["path"]))
        path = candidate.resolve() if candidate.is_absolute() else (ledger_path.parent / candidate).resolve()
        try:
            path.relative_to(ledger_path.parent.resolve())
        except ValueError:
            errors.append(f"{label}: receipt must stay in the task report directory")
            continue
        if path in seen_paths:
            errors.append(f"{label}: duplicate receipt path")
            continue
        seen_paths.add(path)
        if not path.is_file():
            errors.append(f"{label}: receipt is missing")
            continue
        if record.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            errors.append(f"{label}: receipt sha256 is stale")
        try:
            lease = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: invalid JSON: {exc}")
            continue
        if not isinstance(lease, dict) or lease.get("schema_version") != 1:
            errors.append(f"{label}: invalid lease schema")
            continue
        leases.append(lease)

    role_groups = {
        role: [lease for lease in leases if lease.get("role") == role]
        for role in sessions
    }
    if len(role_groups["fairness_reviewer"]) != 2:
        errors.append("role leases require exactly two fairness reviewers")
    if len(role_groups["consolidated_auditor"]) != 1:
        errors.append("role leases require exactly one consolidated auditor")
    for role, group in role_groups.items():
        expected_model, expected_effort = ROLE_PROFILES[role]
        for lease in group:
            label = f"role lease {lease.get('lease_id', '<unknown>')}"
            if lease.get("task_slug") != task_slug:
                errors.append(f"{label}: task slug mismatch")
            if lease.get("model") != expected_model or lease.get("reasoning_effort") != expected_effort:
                errors.append(f"{label}: model/reasoning routing mismatch")
            session_id = lease.get("owner", {}).get("session_id")
            if not nonempty(session_id):
                errors.append(f"{label}: claimed session_id is required")
            else:
                sessions[role].append(str(session_id))
            if lease.get("remediation_cycles") not in {0, 1}:
                errors.append(f"{label}: remediation cycle cap exceeded")

    reviewer_sessions = set(sessions["fairness_reviewer"])
    if reviewer_sessions != completed_sessions["fairness_reviewer"]:
        errors.append("fairness lease sessions do not match completed reviewer task sessions")
    auditor_sessions = set(sessions["consolidated_auditor"])
    if auditor_sessions != completed_sessions["consolidated_auditor"]:
        errors.append("auditor lease session does not match completed auditor task session")

    for lease in role_groups["fairness_reviewer"]:
        if lease.get("status") != "complete" or lease.get("phase") not in {"initial", "re_review"}:
            errors.append(f"role lease {lease.get('lease_id')}: reviewer lease is not complete")
    for lease in role_groups["consolidated_auditor"]:
        if phase == "pre-solver":
            if lease.get("status") != "phase_complete" or lease.get("phase") not in {"pre_freeze", "re_audit"}:
                errors.append(f"role lease {lease.get('lease_id')}: auditor pre-solver phase is invalid")
        elif phase == "handover" and (
            lease.get("status") != "complete" or lease.get("phase") != "post_probe"
        ):
            errors.append(f"role lease {lease.get('lease_id')}: auditor post-probe phase is incomplete")
    return {role: sorted(values) for role, values in sessions.items()}


def validate(data: dict[str, Any], path: Path, phase: str) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if data.get("schema_version") != 2:
        errors.append("schema_version must equal 2")
    if not nonempty(data.get("task_slug")):
        errors.append("task_slug is required")
    turns = data.get("turns")
    if not isinstance(turns, list):
        errors.append("turns must be an array")
        turns = []
    seen: set[str] = set()
    role_counts = {role: 0 for role in ROLES}
    completed_role_counts = {role: 0 for role in ROLES}
    completed_role_session_ids = {role: set() for role in ROLES}
    for index, turn in enumerate(turns):
        label = f"turns[{index}]"
        if not isinstance(turn, dict):
            errors.append(f"{label}: must be an object")
            continue
        turn_id = turn.get("turn_id")
        if not nonempty(turn_id) or turn_id in seen:
            errors.append(f"{label}.turn_id must be a unique non-empty string")
        else:
            seen.add(str(turn_id))
        role = turn.get("role")
        if role not in ROLES:
            errors.append(f"{label}.role is invalid")
            continue
        role_counts[str(role)] += 1
        status = turn.get("status")
        if status == "complete":
            completed_role_counts[str(role)] += 1
            if nonempty(turn.get("session_id")):
                completed_role_session_ids[str(role)].add(str(turn["session_id"]))
        expected_model, expected_effort = ROLE_PROFILES[str(role)]
        if turn.get("model") != expected_model:
            errors.append(f"{label}.model must be {expected_model} for role {role}")
        if turn.get("reasoning_effort") != expected_effort:
            errors.append(
                f"{label}.reasoning_effort must be {expected_effort} for role {role}"
            )
        if status not in STATUSES:
            errors.append(f"{label}.status is invalid; failed/interrupted turns still count")
        expected_surface = ROLE_SURFACES[str(role)]
        if turn.get("execution_surface") != expected_surface:
            errors.append(
                f"{label}.execution_surface must be {expected_surface} for role {role}"
            )
        if expected_surface == "codex_thread":
            provenance = {
                field: turn.get(field)
                for field in ("runtime", "session_id", "thread_id", "host_id")
            }
            if status == "complete" or any(nonempty(value) for value in provenance.values()):
                for field, value in provenance.items():
                    if not nonempty(value):
                        errors.append(f"{label}.{field} is required for a Codex task")
                if provenance["runtime"] != "codex-thread":
                    errors.append(f"{label}.runtime must be codex-thread")
                if (
                    nonempty(provenance["session_id"])
                    and nonempty(provenance["thread_id"])
                    and provenance["session_id"] != provenance["thread_id"]
                ):
                    errors.append(f"{label}.session_id must equal the actual thread_id")
            elif not nonempty(turn.get("launch_error")):
                errors.append(
                    f"{label}.launch_error is required when Codex task creation fails before an ID exists"
                )
        context_mode = turn.get("context_mode")
        if role == "builder":
            if context_mode != "informed":
                errors.append(f"{label}.context_mode must be informed for the builder")
            purpose = turn.get("purpose")
            if purpose not in BUILDER_PURPOSES:
                errors.append(f"{label}.purpose is invalid for the builder")
            report_inputs = turn.get("report_inputs")
            if not isinstance(report_inputs, list) or not report_inputs:
                errors.append(f"{label}.report_inputs must be a non-empty array")
                report_inputs = []
            kinds = {
                kind
                for input_index, report in enumerate(report_inputs)
                if (
                    kind := validate_report_input(
                        path, report, f"{label}.report_inputs[{input_index}]", errors
                    )
                )
            }
            if purpose == "design_build":
                required = {"durable_memory", "pattern_catalog", "batch_portfolio"}
                missing = sorted(required - kinds)
                if missing:
                    errors.append(f"{label}: design/build report inputs missing {missing}")
            else:
                feedback_kind = (
                    "reviewer_feedback" if purpose == "fairness_remediation" else "auditor_feedback"
                )
                if feedback_kind not in kinds:
                    errors.append(f"{label}: remediation is missing {feedback_kind}")
                validate_critique_receipt(path, turn, label, errors)
        elif role in {"fairness_reviewer", "blind_solver"} and context_mode != "fresh":
            errors.append(f"{label}.context_mode must be fresh for role {role}")
        elif role == "consolidated_auditor" and context_mode != "independent":
            errors.append(f"{label}.context_mode must be independent for the auditor")

    remediations = data.get("remediations")
    if not isinstance(remediations, dict):
        errors.append("remediations must be an object")
        remediations = {}
    for gate in ("fairness", "auditor"):
        count = remediations.get(gate)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append(f"remediations.{gate} must be a non-negative integer")
        elif count > 1:
            errors.append(f"remediations.{gate} exceeds the one-cycle cap")

    gates = data.get("mechanical_gates")
    if not isinstance(gates, dict):
        errors.append("mechanical_gates must be an object")
        gates = {}
    for gate in sorted(GATES):
        validate_evidence(path, gate, gates.get(gate), errors)

    if phase == "pre-review" and (
        role_counts["fairness_reviewer"] or role_counts["consolidated_auditor"]
    ):
        errors.append("review/audit turns were recorded before the mechanical pre-review gate")
    if phase == "pre-solver":
        if completed_role_counts["fairness_reviewer"] < 2:
            errors.append("pre-solver requires at least two completed fairness-reviewer turns")
        if completed_role_counts["consolidated_auditor"] < 1:
            errors.append("pre-solver requires a completed consolidated-auditor turn")
        if role_counts["blind_solver"]:
            errors.append("pre-solver ledger already contains blind-solver turns")
    if phase == "handover" and completed_role_counts["blind_solver"] not in {2, 3}:
        errors.append("handover requires exactly two or three completed blind-solver turns")

    role_lease_sessions = {"fairness_reviewer": [], "consolidated_auditor": []}
    if phase in {"pre-solver", "handover"}:
        role_lease_sessions = validate_role_lease_receipts(
            path,
            data.get("role_lease_receipts"),
            phase,
            data.get("task_slug"),
            completed_role_session_ids,
            errors,
        )

    summary = {
        "status": "fail" if errors else "pass",
        "phase": phase,
        "turn_count": len(turns),
        "role_turn_counts": role_counts,
        "completed_role_turn_counts": completed_role_counts,
        "completed_role_session_ids": {
            role: sorted(session_ids)
            for role, session_ids in completed_role_session_ids.items()
        },
        "role_lease_session_ids": role_lease_sessions,
        "errors": errors,
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--phase", choices=("pre-review", "pre-solver", "handover"), required=True)
    args = parser.parse_args()
    try:
        data = load(args.ledger)
        errors, summary = validate(data, args.ledger.resolve(), args.phase)
    except (TypeError, ValueError) as exc:
        summary = {"status": "fail", "errors": [str(exc)]}
        errors = summary["errors"]
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
