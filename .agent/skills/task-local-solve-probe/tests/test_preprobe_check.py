from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "preprobe_check.py"
SPEC = importlib.util.spec_from_file_location("preprobe_check", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
import quota_guard  # noqa: E402
import session_budget  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def build_valid_receipts(tmp_path: Path) -> tuple[Path, Path]:
    task = tmp_path / "workspace" / "tasks" / "tbrain-example"
    report = tmp_path / "workspace" / "reports" / task.name
    logs = report / "probe-preflight-logs"
    task.mkdir(parents=True)
    logs.mkdir(parents=True)
    (task / "instruction.md").write_text("Repair the recorded output.\n", encoding="utf-8")
    (task / "task.toml").write_text('category = "Science"\n', encoding="utf-8")

    ctrf = {
        "oracle-ctrf.json": {"tests": [{"name": "case-1", "status": "passed"}]},
        "nop-ctrf.json": {"tests": [{"name": "case-1", "status": "failed"}]},
        "oracle-noexec-ctrf.json": {
            "tests": [{"name": "case-1", "status": "passed"}]
        },
    }
    rewards = {
        "oracle-reward.txt": "1\n",
        "nop-reward.txt": "0\n",
        "oracle-noexec-reward.txt": "1\n",
    }
    for name in MODULE.REQUIRED_PREFLIGHT_FILES:
        path = logs / name
        if name in ctrf:
            write_json(path, ctrf[name])
        elif name in rewards:
            path.write_text(rewards[name], encoding="utf-8")
        else:
            path.write_text(f"evidence for {name}\n", encoding="utf-8")

    evidence = {
        name: {
            "path": str(logs / name),
            "sha256": MODULE.sha256(logs / name),
            "size": (logs / name).stat().st_size,
        }
        for name in MODULE.REQUIRED_PREFLIGHT_FILES
    }
    write_json(
        report / "probe-preflight.json",
        {
            "task_slug": task.name,
            "status": "pass",
            "strict": True,
            "fail_count": 0,
            "task_snapshot_sha256": MODULE.tree_hash(task),
            "checks": [
                {"check": name, "status": "pass"}
                for name in sorted(MODULE.REQUIRED_PREFLIGHT_CHECKS)
            ],
            "evidence_files": evidence,
        },
    )

    review_transcript = report / "consolidated-pre-freeze-audit.md"
    review_transcript.write_text(
        "Semantic realism, folder review, and task-tree style audit passed.\n",
        encoding="utf-8",
    )
    scanner = (
        SCRIPT.resolve().parents[2]
        / "task-client-feedback-review"
        / "scripts"
        / "review_task.py"
    )
    write_json(
        report / "pre-freeze-review.json",
        {
            "schema_version": 1,
            "scanner_sha256": MODULE.sha256(scanner),
            "manual_review": {
                "status": "pass",
                "runtime": "codex-collaboration",
                "model": "gpt-5.6-sol",
                "session_id": "auditor-session",
                "transcript": review_transcript.name,
                "transcript_sha256": MODULE.sha256(review_transcript),
            },
            "results": [
                {
                    "task": task.name,
                    "status": "ready",
                    "artifact_sha256": MODULE.artifact_hash(task),
                    "counts": {"blocker": 0, "should_fix": 0, "polish": 0},
                }
            ],
        },
    )

    surfaces = [
        {"path": name, "sha256": digest, "status": "verified"}
        for name, digest in sorted(MODULE.style_surface_hashes(task).items())
    ]
    write_json(
        report / "task-style-preflight.json",
        {
            "schema_version": 1,
            "task_slug": task.name,
            "status": "pass",
            "task_snapshot_sha256": MODULE.tree_hash(task),
            "auditor": {
                "status": "pass",
                "runtime": "codex-collaboration",
                "model": "gpt-5.6-sol",
                "session_id": "auditor-session",
                "transcript": review_transcript.name,
                "transcript_sha256": MODULE.sha256(review_transcript),
            },
            "surfaces": surfaces,
        },
    )
    fairness_reviewers = []
    for index in range(1):
        transcript = report / f"fairness-{index + 1}.md"
        transcript.write_text("Goal and evidence are independently sufficient.\n", encoding="utf-8")
        fairness_reviewers.append(
            {
                "reviewer_id": f"fairness-{index + 1}",
                "runtime": "codex-collaboration",
                "model": "gpt-5.6-sol",
                "session_id": f"fairness-session-{index + 1}",
                "fresh_context": True,
                "task_visible_only": True,
                "transcript": transcript.name,
                "transcript_sha256": MODULE.sha256(transcript),
            }
        )
    write_json(
        report / "instruction-sufficiency.json",
        {"fairness_review": {"reviewer_count": 1, "reviewers": fairness_reviewers}},
    )
    write_json(
        report / "semantic-coverage.json",
        {
            "review": {
                "status": "pass",
                "runtime": "codex-collaboration",
                "model": "gpt-5.6-sol",
                "session_id": "auditor-session",
                "transcript": review_transcript.name,
                "transcript_sha256": MODULE.sha256(review_transcript),
            }
        },
    )
    budget, budget_errors = session_budget.build_receipt(
        task,
        report,
        {
            "runtime": "codex-subagent",
            "model": "gpt-5.6-sol",
            "session_id": "builder-session",
        },
    )
    assert budget_errors == []
    write_json(report / "agent-session-budget.json", budget)
    mechanical_gates = {}
    for name in quota_guard.GATES:
        evidence_path = report / f"{name}.log"
        evidence_path.write_text("pass\n", encoding="utf-8")
        mechanical_gates[name] = {
            "status": "pass",
            "evidence": evidence_path.name,
            "sha256": MODULE.sha256(evidence_path),
        }
    for kind in ("durable_memory", "pattern_catalog", "batch_portfolio"):
        (report / f"{kind}.md").write_text(f"{kind}\n", encoding="utf-8")
    review_adjudications = []
    for phase in ("contract_review", "final_review"):
        row = {"phase": phase}
        for field in ("builder_critique", "orchestrator_adjudication"):
            evidence_path = report / f"{phase}-{field}.json"
            evidence_path.write_text("{}\n", encoding="utf-8")
            row[field] = {
                "path": evidence_path.name,
                "sha256": MODULE.sha256(evidence_path),
            }
        review_adjudications.append(row)
    write_json(
        report / "quota-ledger.json",
        {
            "schema_version": 3,
            "role_policy": "fixed_roles_unbounded_v3",
            "task_slug": task.name,
            "mechanical_gates": mechanical_gates,
            "remediations": {"reviewer": 0, "auditor": 0},
            "role_lease_receipts": [],
            "review_adjudications": review_adjudications,
            "turns": [
                {
                    "turn_id": "builder-1",
                    "role": "builder",
                    "model": quota_guard.BUILDER_MODEL,
                    "runtime": "codex-collaboration",
                    "session_id": "builder-session",
                    "reasoning_effort": "medium",
                    "status": "complete",
                    "execution_surface": "collaboration_subagent",
                    "context_mode": "informed",
                    "purpose": "design_build",
                    "report_inputs": [
                        {
                            "kind": kind,
                            "path": f"{kind}.md",
                            "sha256": MODULE.sha256(report / f"{kind}.md"),
                        }
                        for kind in ("durable_memory", "pattern_catalog", "batch_portfolio")
                    ],
                },
                {
                    "turn_id": "review-contract",
                    "role": "fairness_reviewer",
                    "model": quota_guard.BUILDER_MODEL,
                    "reasoning_effort": "medium",
                    "status": "complete",
                    "execution_surface": "collaboration_subagent",
                    "runtime": "codex-collaboration",
                    "session_id": "fairness-session-1",
                    "context_mode": "fresh",
                    "review_phase": "contract_review",
                },
                {
                    "turn_id": "review-final",
                    "role": "fairness_reviewer",
                    "model": quota_guard.BUILDER_MODEL,
                    "reasoning_effort": "medium",
                    "status": "complete",
                    "execution_surface": "collaboration_subagent",
                    "runtime": "codex-collaboration",
                    "session_id": "fairness-session-1",
                    "context_mode": "fresh",
                    "review_phase": "final_review",
                },
                {
                    "turn_id": "auditor-1",
                    "role": "consolidated_auditor",
                    "model": quota_guard.BUILDER_MODEL,
                    "reasoning_effort": "medium",
                    "status": "complete",
                    "execution_surface": "collaboration_subagent",
                    "runtime": "codex-collaboration",
                    "session_id": "auditor-session",
                    "context_mode": "independent",
                },
            ],
        },
    )
    return task, report


def test_valid_preprobe_receipts_pass(tmp_path: Path) -> None:
    task, report = build_valid_receipts(tmp_path)

    assert MODULE.validate(task, report) == []


def test_current_role_policy_does_not_cap_remediation_count(tmp_path: Path) -> None:
    task, report = build_valid_receipts(tmp_path)
    ledger_path = report / "quota-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["remediations"] = {"reviewer": 12, "auditor": 7}
    builder = ledger["turns"][0]
    for index in range(8):
        ledger["turns"].append(
            {
                **builder,
                "turn_id": f"failed-builder-{index}",
                "session_id": f"failed-builder-session-{index}",
                "status": "failed",
            }
        )
    write_json(ledger_path, ledger)

    assert MODULE.validate(task, report) == []


def test_current_role_policy_keeps_failed_and_prior_solver_attempts(tmp_path: Path) -> None:
    _, report = build_valid_receipts(tmp_path)
    ledger_path = report / "quota-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    for index in range(7):
        ledger["turns"].append(
            {
                "turn_id": f"solver-attempt-{index}",
                "role": "blind_solver",
                "model": quota_guard.BUILDER_MODEL,
                "runtime": "codex-collaboration",
                "session_id": f"solver-session-{index}",
                "reasoning_effort": "medium",
                "status": "complete" if index < 4 else "failed",
                "execution_surface": "collaboration_subagent",
                "context_mode": "fresh",
            }
        )

    errors, summary = quota_guard.validate(ledger, ledger_path, "handover")

    assert errors == []
    assert summary["turn_count"] == 11


def test_task_edit_invalidates_all_snapshot_receipts(tmp_path: Path) -> None:
    task, report = build_valid_receipts(tmp_path)
    (task / "instruction.md").write_text("Changed after review.\n", encoding="utf-8")

    errors = MODULE.validate(task, report)

    assert any("task snapshot is stale" in error for error in errors)
    assert any("task changed after review" in error for error in errors)
    assert any("surface inventory/hash mismatch" in error for error in errors)


def test_manually_cleared_should_fix_can_enter_counted_probe(tmp_path: Path) -> None:
    task, report = build_valid_receipts(tmp_path)
    path = report / "pre-freeze-review.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["results"][0]["counts"]["should_fix"] = 1
    write_json(path, receipt)
    budget, budget_errors = session_budget.build_receipt(
        task,
        report,
        {
            "runtime": "codex-subagent",
            "model": "gpt-5.6-sol",
            "session_id": "builder-session",
        },
    )
    assert budget_errors == []
    write_json(report / "agent-session-budget.json", budget)

    errors = MODULE.validate(task, report)

    assert errors == []


def test_consolidated_auditor_provenance_must_match(tmp_path: Path) -> None:
    task, report = build_valid_receipts(tmp_path)
    style_path = report / "task-style-preflight.json"
    style = json.loads(style_path.read_text(encoding="utf-8"))
    style["auditor"]["session_id"] = "extra-style-agent"
    write_json(style_path, style)

    errors = MODULE.validate(task, report)

    assert any("share one exact auditor" in error for error in errors)


def test_builder_cannot_be_fairness_reviewer(tmp_path: Path) -> None:
    task, report = build_valid_receipts(tmp_path)
    budget_path = report / "agent-session-budget.json"
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    budget["builder"]["session_id"] = "fairness-session-1"
    write_json(budget_path, budget)

    errors = MODULE.validate(task, report)

    assert any("must be distinct sessions" in error for error in errors)
