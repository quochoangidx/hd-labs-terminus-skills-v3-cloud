from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "builder_context_packet.py"
SPEC = importlib.util.spec_from_file_location("builder_context_packet", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class BuilderContextPacketTests(unittest.TestCase):
    def test_candidate_gate_hashes_required_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = []
            for kind in ("durable_memory", "pattern_catalog", "batch_portfolio"):
                path = root / f"{kind}.txt"
                path.write_text(kind, encoding="utf-8")
                inputs.append((kind, path))
            receipt = module.build_receipt("candidate_gate", "tbrain-one", inputs)
            self.assertEqual("tbrain-one", receipt["candidate_slug"])
            self.assertEqual(3, len(receipt["inputs"]))

    def test_stage_rejects_irrelevant_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "x"
            path.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not allowed"):
                module.build_receipt(
                    "candidate_gate",
                    "tbrain-one",
                    [
                        ("durable_memory", path),
                        ("pattern_catalog", path),
                        ("batch_portfolio", path),
                        ("reviewer_feedback", path),
                    ],
                )


if __name__ == "__main__":
    unittest.main()
