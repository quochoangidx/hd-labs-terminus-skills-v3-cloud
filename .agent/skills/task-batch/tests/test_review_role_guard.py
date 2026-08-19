from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = load_module("review_role_guard")
packet_module = load_module("role_context_packet")


class ReviewRoleGuardTests(unittest.TestCase):
    def fairness_packet(self, root: Path, phase: str = "initial") -> Path:
        instruction = root / f"instruction-{phase}.md"
        instruction.write_text("Produce artifact.json\n", encoding="utf-8")
        visible = root / "visible"
        visible.mkdir(exist_ok=True)
        (visible / "evidence.json").write_text("{}\n", encoding="utf-8")
        inputs = [("instruction", instruction), ("task_visible_tree", visible)]
        if phase == "re_review":
            summary = root / "remediation.md"
            summary.write_text("Changed wording only.\n", encoding="utf-8")
            inputs.append(("remediation_summary", summary))
        data = packet_module.build_packet("fairness_reviewer", phase, "tbrain-example", inputs)
        path = root / f"fairness-{phase}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def open_reviewers(self, root: Path) -> list[Path]:
        packet = self.fairness_packet(root)
        args = argparse.Namespace(
            role="fairness_reviewer", phase="initial", task="tbrain-example",
            packet=packet, count=2, deadline_minutes=5,
        )
        with redirect_stdout(StringIO()):
            guard.open_leases(args, root / "leases")
        return guard.paths(root / "leases")

    def auditor_packet(self, root: Path, phase: str) -> Path:
        task = root / "task"
        task.mkdir(exist_ok=True)
        (task / "task.toml").write_text("version = 1\n", encoding="utf-8")
        inputs = [("task_folder", task)]
        if phase == "pre_freeze":
            mechanical = root / "mechanical.json"
            mechanical.write_text("{}\n", encoding="utf-8")
            inputs.append(("mechanical_receipts", mechanical))
        else:
            probe = root / "probe.json"
            probe.write_text("{}\n", encoding="utf-8")
            submission = root / "submission.md"
            submission.write_text("Difficulty Explanation\n", encoding="utf-8")
            inputs.extend([("probe_report", probe), ("submission_packet", submission)])
        data = packet_module.build_packet(
            "consolidated_auditor", phase, "tbrain-example", inputs
        )
        path = root / f"auditor-{phase}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def hook(self, root: Path, event: dict) -> tuple[int, str]:
        output = StringIO()
        with patch("sys.stdin", StringIO(json.dumps(event))), redirect_stdout(output):
            code = guard.hook(root / "leases")
        return code, output.getvalue()

    def test_two_sessions_claim_distinct_reviewer_leases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.open_reviewers(root)
            for session in ("thread-1", "thread-2"):
                code, _ = self.hook(root, {
                    "hook_event_name": "SessionStart", "model": "gpt-5.6-luna", "session_id": session,
                })
                self.assertEqual(0, code)
            owners = {guard.load(path)["owner"]["session_id"] for path in paths}
            self.assertEqual({"thread-1", "thread-2"}, owners)

    def test_reviewer_is_read_only_and_context_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.open_reviewers(root)
            self.hook(root, {
                "hook_event_name": "SessionStart", "model": "gpt-5.6-luna", "session_id": "thread-1",
            })
            code, output = self.hook(root, {
                "hook_event_name": "PreToolUse", "session_id": "thread-1", "turn_id": "turn-1",
                "tool_name": "apply_patch", "tool_input": {"command": "*** Add File: note.md"},
            })
            self.assertEqual(2, code)
            self.assertIn("review-only", output)
            code, output = self.hook(root, {
                "hook_event_name": "PreToolUse", "session_id": "thread-1", "turn_id": "turn-1",
                "tool_name": "Bash", "tool_input": {"command": "sed -n 1,20p AGENTS.md"},
            })
            self.assertEqual(2, code)
            self.assertIn("forbidden", output)

    def test_re_review_requires_transition_and_is_single_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.open_reviewers(root)
            lease_path = paths[0]
            lease = guard.load(lease_path)
            lease["status"] = "phase_complete"
            guard.save(lease_path, lease)
            re_review = self.fairness_packet(root, "re_review")
            args = argparse.Namespace(
                lease=lease["lease_id"], phase="re_review", packet=re_review, deadline_minutes=5,
            )
            with redirect_stdout(StringIO()):
                guard.transition(args, root / "leases")
            updated = guard.load(lease_path)
            self.assertEqual(1, updated["remediation_cycles"])
            updated["status"] = "phase_complete"
            guard.save(lease_path, updated)
            with self.assertRaises(ValueError):
                guard.transition(args, root / "leases")

    def test_completed_turn_can_be_reconciled_without_fabricating_hook_enforcement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lease_path = self.open_reviewers(root)[0]
            lease = guard.load(lease_path)
            started = guard.now()
            ended = started + timedelta(seconds=30)
            evidence = root / "review.md"
            evidence.write_text("Verdict: PASS\n", encoding="utf-8")
            args = argparse.Namespace(
                lease=lease["lease_id"], session_id="thread-1", turn_id="turn-1",
                started_at=started.isoformat(), ended_at=ended.isoformat(),
                model="gpt-5.6-luna", reasoning_effort="high", evidence=evidence,
            )
            with redirect_stdout(StringIO()):
                guard.reconcile_completed(args, root / "leases")
            updated = guard.load(lease_path)
            self.assertEqual("phase_complete", updated["status"])
            self.assertEqual("thread-1", updated["owner"]["session_id"])
            self.assertFalse(updated["hook_enforced"])
            self.assertIn("unavailable", updated["tool_call_accounting"])

    def test_auditor_session_is_reused_for_post_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pre = self.auditor_packet(root, "pre_freeze")
            open_args = argparse.Namespace(
                role="consolidated_auditor", phase="pre_freeze", task="tbrain-example",
                packet=pre, count=1, deadline_minutes=5,
            )
            with redirect_stdout(StringIO()):
                guard.open_leases(open_args, root / "leases")
            self.hook(root, {
                "hook_event_name": "SessionStart", "model": "gpt-5.6-luna", "session_id": "auditor-thread",
            })
            self.hook(root, {"hook_event_name": "Stop", "session_id": "auditor-thread"})
            lease_path = guard.paths(root / "leases")[0]
            lease = guard.load(lease_path)
            self.assertEqual("phase_complete", lease["status"])
            post = self.auditor_packet(root, "post_probe")
            transition_args = argparse.Namespace(
                lease=lease["lease_id"], phase="post_probe", packet=post, deadline_minutes=5,
            )
            with redirect_stdout(StringIO()):
                guard.transition(transition_args, root / "leases")
            transitioned = guard.load(lease_path)
            self.assertEqual("auditor-thread", transitioned["owner"]["session_id"])
            self.hook(root, {"hook_event_name": "Stop", "session_id": "auditor-thread"})
            self.assertEqual("complete", guard.load(lease_path)["status"])


if __name__ == "__main__":
    unittest.main()
