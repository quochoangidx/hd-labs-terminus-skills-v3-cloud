from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "quota_guard.py"
SPEC = importlib.util.spec_from_file_location("quota_guard", SCRIPT)
assert SPEC and SPEC.loader
quota_guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quota_guard)


class QuotaGuardTests(unittest.TestCase):
    def ledger(self, root: Path) -> tuple[Path, dict]:
        gates = {}
        for name in quota_guard.GATES:
            evidence = root / f"{name}.log"
            evidence.write_text("pass\n", encoding="utf-8")
            gates[name] = {
                "status": "pass",
                "evidence": evidence.name,
                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
            }
        report_inputs = []
        for kind in ("durable_memory", "pattern_catalog", "batch_portfolio"):
            report = root / f"{kind}.md"
            report.write_text(f"{kind}\n", encoding="utf-8")
            report_inputs.append(
                {
                    "kind": kind,
                    "path": report.name,
                    "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                }
            )
        role_lease_receipts = []
        lease_specs = (
            ("fairness-1", "fairness_reviewer", "high", "thread-fairness-1", "complete", "initial"),
            ("fairness-2", "fairness_reviewer", "high", "thread-fairness-2", "complete", "initial"),
            ("auditor-1", "consolidated_auditor", "max", "thread-auditor-1", "phase_complete", "pre_freeze"),
        )
        for lease_id, role, effort, session_id, status, phase in lease_specs:
            receipt = root / f"{lease_id}-lease.json"
            receipt.write_text(json.dumps({
                "schema_version": 1,
                "lease_id": lease_id,
                "task_slug": "tbrain-example",
                "role": role,
                "model": "gpt-5.6-luna",
                "reasoning_effort": effort,
                "owner": {"session_id": session_id},
                "status": status,
                "phase": phase,
                "remediation_cycles": 0,
            }), encoding="utf-8")
            role_lease_receipts.append({
                "path": receipt.name,
                "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
            })
        data = {
            "schema_version": 2,
            "task_slug": "tbrain-example",
            "mechanical_gates": gates,
            "remediations": {"fairness": 0, "auditor": 0},
            "role_lease_receipts": role_lease_receipts,
            "turns": [
                {
                    "turn_id": "builder-1",
                    "role": "builder",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                    "status": "complete",
                    "execution_surface": "collaboration_subagent",
                    "context_mode": "informed",
                    "purpose": "design_build",
                    "report_inputs": report_inputs,
                },
                *[
                    {
                        "turn_id": f"fairness-{index}",
                        "role": "fairness_reviewer",
                        "model": "gpt-5.6-luna",
                        "reasoning_effort": "high",
                        "status": "complete",
                        "execution_surface": "codex_thread",
                        "runtime": "codex-thread",
                        "session_id": f"thread-fairness-{index}",
                        "thread_id": f"thread-fairness-{index}",
                        "host_id": "local",
                        "context_mode": "fresh",
                    }
                    for index in (1, 2)
                ],
                {
                    "turn_id": "auditor-1",
                    "role": "consolidated_auditor",
                    "model": "gpt-5.6-luna",
                    "reasoning_effort": "max",
                    "status": "complete",
                    "execution_surface": "codex_thread",
                    "runtime": "codex-thread",
                    "session_id": "thread-auditor-1",
                    "thread_id": "thread-auditor-1",
                    "host_id": "local",
                    "context_mode": "independent",
                },
            ],
        }
        path = root / "quota-ledger.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path, data

    def test_pre_solver_accepts_routing_without_fixed_turn_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            errors, summary = quota_guard.validate(data, path, "pre-solver")
            self.assertEqual([], errors)
            self.assertEqual(4, summary["turn_count"])
            self.assertEqual(
                ["thread-fairness-1", "thread-fairness-2"],
                summary["completed_role_session_ids"]["fairness_reviewer"],
            )

    def test_failed_followups_are_recorded_without_blocking_on_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            for index in range(5):
                data["turns"].append(
                    {
                        "turn_id": f"builder-followup-{index}",
                        "role": "builder",
                        "model": "gpt-5.6-sol",
                        "reasoning_effort": "medium",
                        "status": "usage_limited" if index == 4 else "failed",
                        "execution_surface": "collaboration_subagent",
                        "context_mode": "informed",
                        "purpose": "design_build",
                        "report_inputs": data["turns"][0]["report_inputs"],
                    }
                )
            errors, summary = quota_guard.validate(data, path, "pre-solver")
            self.assertEqual([], errors)
            self.assertEqual(9, summary["turn_count"])

    def test_luna_model_is_rejected_for_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            data["turns"][0]["model"] = "gpt-5.6-luna"
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertTrue(any("gpt-5.6-sol" in error for error in errors))

    def test_terra_model_is_rejected_for_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            data["turns"][1]["model"] = "gpt-5.6-terra"
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertTrue(any("gpt-5.6-luna" in error for error in errors))

    def test_builder_cannot_be_fresh_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            data["turns"][0]["context_mode"] = "fresh"
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertTrue(any("must be informed" in error for error in errors))

    def test_remediation_requires_feedback_and_critique_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            builder = data["turns"][0]
            builder["purpose"] = "fairness_remediation"
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertTrue(any("missing reviewer_feedback" in error for error in errors))
            self.assertTrue(any("critique_receipt is required" in error for error in errors))

    def test_informed_builder_can_critique_fairness_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, data = self.ledger(root)
            feedback = root / "fairness-feedback.md"
            feedback.write_text("F-1: evidence source may be ambiguous.\n", encoding="utf-8")
            critique = root / "builder-critique.json"
            critique.write_text(
                json.dumps(
                    {
                        "findings": [
                            {
                                "finding_id": "F-1",
                                "disposition": "partial",
                                "evidence": "The trace is visible but the path is not named.",
                                "action": "Name the trace path without disclosing the inference.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            builder = data["turns"][0]
            builder["purpose"] = "fairness_remediation"
            builder["report_inputs"].append(
                {
                    "kind": "reviewer_feedback",
                    "path": feedback.name,
                    "sha256": hashlib.sha256(feedback.read_bytes()).hexdigest(),
                }
            )
            builder["critique_receipt"] = {
                "path": critique.name,
                "sha256": hashlib.sha256(critique.read_bytes()).hexdigest(),
            }
            data["remediations"]["fairness"] = 1
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertEqual([], errors)

    def test_handover_requires_two_or_three_sol_turns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            for index in (1, 2):
                data["turns"].append(
                    {
                        "turn_id": f"solver-{index}",
                        "role": "blind_solver",
                        "model": "gpt-5.6-sol",
                        "reasoning_effort": "medium",
                        "status": "complete",
                        "execution_surface": "collaboration_subagent",
                        "context_mode": "fresh",
                    }
                )
            auditor_receipt = Path(tmp) / "auditor-1-lease.json"
            auditor = json.loads(auditor_receipt.read_text(encoding="utf-8"))
            auditor.update({"status": "complete", "phase": "post_probe"})
            auditor_receipt.write_text(json.dumps(auditor), encoding="utf-8")
            data["role_lease_receipts"][2]["sha256"] = hashlib.sha256(
                auditor_receipt.read_bytes()
            ).hexdigest()
            errors, _ = quota_guard.validate(data, path, "handover")
            self.assertEqual([], errors)

    def test_reviewer_must_use_codex_thread_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            reviewer = data["turns"][1]
            reviewer["execution_surface"] = "collaboration_subagent"
            reviewer["session_id"] = "not-the-thread"
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertTrue(any("execution_surface must be codex_thread" in error for error in errors))
            self.assertTrue(any("session_id must equal" in error for error in errors))

    def test_failed_luna_launch_does_not_satisfy_completed_role_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, data = self.ledger(Path(tmp))
            reviewer = data["turns"][1]
            reviewer.update(
                {
                    "status": "failed",
                    "runtime": "",
                    "session_id": "",
                    "thread_id": "",
                    "host_id": "",
                    "launch_error": "create_thread rejected the requested profile",
                }
            )
            errors, _ = quota_guard.validate(data, path, "pre-solver")
            self.assertTrue(any("two completed fairness-reviewer" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
