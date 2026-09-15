from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "role_context_packet.py"
SPEC = importlib.util.spec_from_file_location("role_context_packet", SCRIPT)
assert SPEC and SPEC.loader
packet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packet)


class RoleContextPacketTests(unittest.TestCase):
    def test_fairness_packet_accepts_only_task_visible_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instruction = root / "instruction.md"
            instruction.write_text("Produce artifact.json\n", encoding="utf-8")
            visible = root / "visible"
            visible.mkdir()
            (visible / "trace.json").write_text("{}\n", encoding="utf-8")
            result = packet.build_packet(
                "fairness_reviewer",
                "contract_review",
                "tbrain-example",
                [("instruction", instruction), ("task_visible_tree", visible)],
            )
            self.assertEqual("gpt-5.6-luna", result["model"])
            self.assertEqual("high", result["reasoning_effort"])

    def test_fairness_packet_rejects_tests_and_solution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instruction = root / "instruction.md"
            instruction.write_text("goal\n", encoding="utf-8")
            visible = root / "visible"
            (visible / "tests").mkdir(parents=True)
            (visible / "tests/test_hidden.py").write_text("secret\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "leaks"):
                packet.build_packet(
                    "fairness_reviewer",
                    "contract_review",
                    "tbrain-example",
                    [("instruction", instruction), ("task_visible_tree", visible)],
                )


if __name__ == "__main__":
    unittest.main()
