#!/usr/bin/env python3
"""Validate model routing, role evidence, review ordering, and role leases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BUILDER_MODEL = "gpt-5.6-sol"
REVIEW_MODEL = "gpt-5.6-sol"
SOLVER_MODEL = "gpt-5.6-sol"
SINGLE_REVIEWER_POLICY = "single_reviewer_two_pass_v1"
FIXED_FIVE_POLICY = "fixed_five_roles_v2"
UNBOUNDED_ROLE_POLICY = "fixed_roles_unbounded_v3"
ROLE_PROFILES = {
    "builder": (BUILDER_MODEL, "medium"),
    "fairness_reviewer": (REVIEW_MODEL, "medium"),
    "consolidated_auditor": (REVIEW_MODEL, "medium"),
    "blind_solver": (SOLVER_MODEL, "medium"),
}
# Every role now runs as a collaboration subagent. The Codex-thread surface existed
# only for the retired Luna reviewer/auditor path.
ROLE_SURFACES = {
    "builder": "collaboration_subagent",
    "fairness_reviewer": "collaboration_subagent",
    "consolidated_auditor": "collaboration_subagent",
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
BUILDER_PURPOSES = {
    "design_build",
    "fairness_remediation",
    "reviewer_remediation",
    "auditor_remediation",
}
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


def valid_runtime_model(runtime: object, model: object) -> bool:
    runtime_name = str(runtime or "").lower()
    model_name = str(model or "")
    if "claude" in runtime_name:
        return model_name in {"opus", "opus-5"} or model_name.startswith("claude-opus-5")
    if "codex" in runtime_name:
        return model_name == BUILDER_MODEL
    return False


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


def validate_review_adjudications(
    ledger_path: Path, records: object, errors: list[str]
) -> None:
    if not isinstance(records, list) or len(records) != 2:
        errors.append("review_adjudications must contain contract_review and final_review")
        return
    phases: set[str] = set()
    for index, record in enumerate(records):
        label = f"review_adjudications[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label} must be an object")
            continue
        phase = record.get("phase")
        if phase not in {"contract_review", "final_review"} or phase in phases:
            errors.append(f"{label}.phase is invalid or duplicated")
        else:
            phases.add(str(phase))
        for field in ("builder_critique", "orchestrator_adjudication"):
            evidence = record.get(field)
            if not isinstance(evidence, dict) or not nonempty(evidence.get("path")):
                errors.append(f"{label}.{field}.path is required")
                continue
            candidate = Path(str(evidence["path"]))
            path = candidate.resolve() if candidate.is_absolute() else (ledger_path.parent / candidate).resolve()
            try:
                path.relative_to(ledger_path.parent.resolve())
            except ValueError:
                errors.append(f"{label}.{field} must stay in the task report directory")
                continue
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"{label}.{field} is missing or empty")
            elif evidence.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
                errors.append(f"{label}.{field} sha256 is stale")
    if phases != {"contract_review", "final_review"}:
        errors.append("review_adjudications phases are incomplete")


def validate_role_lease_receipts(
    ledger_path: Path,
    records: object,
    phase: str,
    task_slug: object,
    completed_sessions: dict[str, set[str]],
    errors: list[str],
    *,
    single_reviewer: bool = False,
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
    if single_reviewer:
        # Review roles run as collaboration subagents, which take no lease. A lease
        # here means a Codex-thread role the hook guard would not protect.
        for role, group in role_groups.items():
            if group:
                errors.append(f"single-reviewer runs take no {role} role lease")
    else:
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

    expected_sessions = {role: set() for role in sessions} if single_reviewer else completed_sessions
    reviewer_sessions = set(sessions["fairness_reviewer"])
    if reviewer_sessions != expected_sessions["fairness_reviewer"]:
        errors.append("fairness lease sessions do not match completed reviewer task sessions")
    auditor_sessions = set(sessions["consolidated_auditor"])
    if auditor_sessions != expected_sessions["consolidated_auditor"]:
        errors.append("auditor lease session does not match completed auditor task session")

    for lease in role_groups["fairness_reviewer"]:
        allowed_phases = {"contract_review", "final_review"} if single_reviewer else {"initial", "re_review"}
        if lease.get("status") != "complete" or lease.get("phase") not in allowed_phases:
            errors.append(f"role lease {lease.get('lease_id')}: reviewer lease is not complete")
    for lease in role_groups["consolidated_auditor"]:
        if single_reviewer and lease.get("status") not in {"complete", "phase_complete"}:
            errors.append(f"role lease {lease.get('lease_id')}: optional auditor lease is incomplete")
        elif phase == "pre-solver":
            if lease.get("status") != "phase_complete" or lease.get("phase") not in {"pre_freeze", "re_audit"}:
                errors.append(f"role lease {lease.get('lease_id')}: auditor pre-solver phase is invalid")
        elif phase == "handover" and (
            lease.get("status") != "complete" or lease.get("phase") != "post_probe"
        ):
            errors.append(f"role lease {lease.get('lease_id')}: auditor post-probe phase is incomplete")
    return {role: sorted(values) for role, values in sessions.items()}


def validate(data: dict[str, Any], path: Path, phase: str) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    fixed_five = data.get("role_policy") == FIXED_FIVE_POLICY
    unbounded_roles = data.get("role_policy") == UNBOUNDED_ROLE_POLICY
    current_roles = fixed_five or unbounded_roles
    single_reviewer = data.get("role_policy") in {
        SINGLE_REVIEWER_POLICY,
        FIXED_FIVE_POLICY,
        UNBOUNDED_ROLE_POLICY,
    }
    expected_schema = 3 if single_reviewer else 2
    if data.get("schema_version") != expected_schema:
        errors.append(f"schema_version must equal {expected_schema}")
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
    completed_review_phases: dict[str, set[str]] = {}
    runtime_families: set[str] = set()
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
        if current_roles:
            runtime_name = str(turn.get("runtime", "")).lower()
            runtime_families.add("claude" if "claude" in runtime_name else "codex" if "codex" in runtime_name else "")
            if not valid_runtime_model(turn.get("runtime"), turn.get("model")):
                errors.append(
                    f"{label}: every role must use gpt-5.6-sol medium on Codex or Opus 5 medium on Claude"
                )
            if turn.get("reasoning_effort") != "medium":
                errors.append(f"{label}.reasoning_effort must be medium")
            expected_surface = "collaboration_subagent"
        elif single_reviewer and role == "fairness_reviewer":
            model = str(turn.get("model", ""))
            default_codex = model == SOLVER_MODEL and turn.get("reasoning_effort") == "medium"
            default_claude = (model == "opus-5" or model.startswith("claude-opus-5")) and turn.get("reasoning_effort") == "medium"
            if not (default_codex or default_claude):
                errors.append(f"{label}: reviewer must use Sol medium or Opus 5 medium")
            expected_surface = "collaboration_subagent"
        else:
            if turn.get("model") != expected_model:
                errors.append(f"{label}.model must be {expected_model} for role {role}")
            if turn.get("reasoning_effort") != expected_effort:
                errors.append(
                    f"{label}.reasoning_effort must be {expected_effort} for role {role}"
                )
            expected_surface = ROLE_SURFACES[str(role)]
        if status not in STATUSES:
            errors.append(f"{label}.status is invalid; failed/interrupted turns still count")
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
                    "reviewer_feedback"
                    if purpose in {"fairness_remediation", "reviewer_remediation"}
                    else "auditor_feedback"
                )
                if feedback_kind not in kinds:
                    errors.append(f"{label}: remediation is missing {feedback_kind}")
                validate_critique_receipt(path, turn, label, errors)
        elif role in {"fairness_reviewer", "blind_solver"} and context_mode != "fresh":
            errors.append(f"{label}.context_mode must be fresh for role {role}")
        elif role == "consolidated_auditor" and context_mode != "independent":
            errors.append(f"{label}.context_mode must be independent for the auditor")
        if single_reviewer and role == "fairness_reviewer" and status == "complete":
            review_phase = turn.get("review_phase")
            if review_phase not in {"contract_review", "final_review"}:
                errors.append(f"{label}.review_phase is required for the single reviewer")
            elif nonempty(turn.get("session_id")):
                completed_review_phases.setdefault(str(turn["session_id"]), set()).add(str(review_phase))

    remediations = data.get("remediations")
    if current_roles and (len(runtime_families) != 1 or "" in runtime_families):
        errors.append(f"{data.get('role_policy')} requires every role to use one active runtime")
    if not isinstance(remediations, dict):
        errors.append("remediations must be an object")
        remediations = {}
    remediation_gates = ("reviewer", "auditor") if single_reviewer else ("fairness", "auditor")
    for gate in remediation_gates:
        count = remediations.get(gate)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append(f"remediations.{gate} must be a non-negative integer")
        elif not unbounded_roles:
            cap = 2 if fixed_five and gate == "reviewer" else 1
            if count > cap:
                errors.append(f"remediations.{gate} exceeds the {cap}-cycle cap")

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
        if single_reviewer:
            if current_roles and len(completed_role_session_ids["builder"]) != 1:
                errors.append("pre-solver requires exactly one completed builder session")
            if len(completed_role_session_ids["fairness_reviewer"]) != 1:
                errors.append("pre-solver requires exactly one completed reviewer session")
            elif set(next(iter(completed_review_phases.values()), set())) != {"contract_review", "final_review"}:
                errors.append("pre-solver requires contract_review and final_review in the same reviewer session")
            validate_review_adjudications(path, data.get("review_adjudications"), errors)
            if current_roles and len(completed_role_session_ids["consolidated_auditor"]) != 1:
                errors.append("pre-solver requires exactly one completed consolidated-auditor session")
        else:
            if completed_role_counts["fairness_reviewer"] < 2:
                errors.append("pre-solver requires at least two completed fairness-reviewer turns")
            if completed_role_counts["consolidated_auditor"] < 1:
                errors.append("pre-solver requires a completed consolidated-auditor turn")
        if role_counts["blind_solver"]:
            errors.append("pre-solver ledger already contains blind-solver turns")
    if phase == "handover" and (
        completed_role_counts["blind_solver"] < 2
        if unbounded_roles
        else completed_role_counts["blind_solver"] != 2
    ):
        requirement = "at least two" if unbounded_roles else "exactly two"
        errors.append(f"handover requires {requirement} completed blind-solver turns")
    if phase == "handover" and single_reviewer:
        validate_review_adjudications(path, data.get("review_adjudications"), errors)

    role_lease_sessions = {"fairness_reviewer": [], "consolidated_auditor": []}
    if phase in {"pre-solver", "handover"}:
        role_lease_sessions = validate_role_lease_receipts(
            path,
            data.get("role_lease_receipts"),
            phase,
            data.get("task_slug"),
            completed_role_session_ids,
            errors,
            single_reviewer=single_reviewer,
        )

    summary = {
        "status": "fail" if errors else "pass",
        "phase": phase,
        "role_policy": data.get("role_policy", "legacy_v1"),
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
