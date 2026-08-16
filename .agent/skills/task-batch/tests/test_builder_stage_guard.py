from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "builder_stage_guard.py"
SPEC = importlib.util.spec_from_file_location("builder_stage_guard", SCRIPT)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class BuilderStageGuardTests(unittest.TestCase):
    def state(self, root: Path) -> Path:
        state = {
            "schema_version": 1,
            "status": "active",
            "runtime": "codex",
            "batch_id": "batch-1",
            "candidate_slug": "tbrain-one",
            "stage": "candidate_gate",
            "agent_type_pattern": "builder",
            "owner": {},
            "bound_turn_id": None,
            "deadline_at": guard.iso(guard.utcnow() + guard.timedelta(minutes=10)),
            "infrastructure_repairs": 0,
            "source_smoke_receipt": None,
        }
        path = root / "lease.json"
        guard.write_state(path, state)
        return path

    def call_hook(self, path: Path, event: dict) -> tuple[int, str]:
        output = StringIO()
        with patch("sys.stdin", StringIO(json.dumps(event))), redirect_stdout(output):
            code = guard.hook("codex", path)
        return code, output.getvalue()

    def test_only_matching_subagent_is_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.state(Path(tmp))
            code, _ = self.call_hook(path, {
                "hook_event_name": "SubagentStart", "agent_type": "blind_solver", "agent_id": "s1"
            })
            self.assertEqual(0, code)
            self.assertEqual({}, guard.read_json(path)["owner"])
            self.call_hook(path, {
                "hook_event_name": "SubagentStart", "agent_type": "batch_builder", "agent_id": "b1", "session_id": "p1"
            })
            self.assertEqual("b1", guard.read_json(path)["owner"]["agent_id"])

    def test_stage_a_blocks_scaffold_and_candidate_rollover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.state(Path(tmp))
            self.call_hook(path, {
                "hook_event_name": "SubagentStart", "agent_type": "batch_builder", "agent_id": "b1"
            })
            code, output = self.call_hook(path, {
                "hook_event_name": "PreToolUse",
                "agent_id": "b1",
                "turn_id": "turn-1",
                "tool_name": "apply_patch",
                "tool_input": {"command": "*** Add File: workspace/tasks/tbrain-two/task.toml"},
            })
            self.assertEqual(2, code)
            self.assertIn("permissionDecision", output)

    def test_read_only_commands_are_not_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.state(Path(tmp))
            self.call_hook(path, {
                "hook_event_name": "SubagentStart", "agent_type": "batch_builder", "agent_id": "b1"
            })
            code, _ = self.call_hook(path, {
                "hook_event_name": "PreToolUse", "agent_id": "b1", "turn_id": "turn-1",
                "tool_name": "Bash", "tool_input": {"command": "rg tbrain-two workspace/reports"},
            })
            self.assertEqual(0, code)

    def test_source_smoke_is_snapshot_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            file = source / "main.rs"
            file.write_text("fn main() {}\n", encoding="utf-8")
            receipt = root / "smoke.json"
            receipt.write_text(json.dumps({
                "schema_version": 1,
                "status": "pass",
                "candidate_slug": "tbrain-one",
                "image": "rust@sha256:" + "a" * 64,
                "source_dir": str(source),
                "source_tree_sha256": guard.hash_tree(source),
            }), encoding="utf-8")
            guard.validate_smoke_receipt(receipt, "tbrain-one")
            file.write_text("fn main() { panic!() }\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                guard.validate_smoke_receipt(receipt, "tbrain-one")


if __name__ == "__main__":
    unittest.main()
