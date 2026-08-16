from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "design_pattern_mix_check.py"
SPEC = importlib.util.spec_from_file_location("design_pattern_mix_check", SCRIPT)
assert SPEC and SPEC.loader
mix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mix)


class DesignPatternMixTests(unittest.TestCase):
    def test_partial_prefix_may_be_handed_over(self) -> None:
        manifest = {
            "schema_version": 1,
            "expected_count": 3,
            "candidates": [
                {
                    "task_slug": "tbrain-one",
                    "track": "established",
                    "pattern_ids": ["P1"],
                    "causal_graph": {"nodes": ["a", "b"], "edges": ["a->b"]},
                    "non_equivalence_rationale": "new causal mechanism",
                    "closest_portfolio_pattern_instance": "none",
                }
            ],
        }
        errors, summary = mix.validate(manifest, {"P1": "pattern"}, allow_partial=True)
        self.assertEqual([], errors)
        self.assertTrue(summary["partial"])

    def test_strict_final_still_requires_exact_mix(self) -> None:
        manifest = {
            "schema_version": 1,
            "expected_count": 3,
            "candidates": [],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"})
        self.assertTrue(any("candidate count" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
