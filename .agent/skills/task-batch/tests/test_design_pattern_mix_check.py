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
    @staticmethod
    def _frontier_stability() -> dict:
        return {
            "dominant_topology_id": "P1",
            "secondary_topology_id": None,
            "amplifier_or_envelope_id": None,
            "planned_mechanism_ids": ["authority", "invalidation", "preservation"],
            "planned_interaction_ids": ["authority-invalidation", "rebuild-preservation"],
            "retrieval_audit": {
                "search_queries": ["issue wording", "error symbol", "version diff"],
                "public_artifacts_checked": ["https://example.invalid/change"],
                "exact_solution_found": False,
                "satisfied_mechanism_ids": [],
                "satisfied_interaction_ids": [],
                "disposition": "pass",
            },
            "orthogonal_traps": [
                {
                    "id": "trap-a",
                    "semantic_node": "authority",
                    "repair_surface": "planner.resolve",
                    "natural_implementation": "trust the first source",
                    "why_wrong": "later evidence supersedes it",
                    "witness_ids": ["authority-late"],
                },
                {
                    "id": "trap-b",
                    "semantic_node": "invalidation",
                    "repair_surface": "cache.rebuild",
                    "natural_implementation": "retain derived cache entries",
                    "why_wrong": "stale entries survive reconciliation",
                    "witness_ids": ["stale-cache"],
                },
            ],
            "shared_fix_rationale": "authority choice and cache invalidation need separate repairs",
        }

    def test_catalog_registers_frontier_experimental_prototypes(self) -> None:
        catalog = SCRIPT.parents[2] / "task-miner" / "frontier_task_design_patterns.md"
        self.assertEqual(
            {
                "X-closed-loop-empirical-convergence",
                "X-cross-layer-feature-completion",
                "X-dynamic-authority-reconciliation",
            },
            set(mix._experimental_ids(catalog)),
        )

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

    def test_registered_x_remains_a_derived_candidate(self) -> None:
        manifest = {
            "schema_version": 1,
            "expected_count": 3,
            "candidates": [
                {
                    "task_slug": "tbrain-layered-feature",
                    "track": "derived",
                    "parent_pattern_ids": ["P1", "P6"],
                    "derived_pattern_id": "X-cross-layer-feature-completion",
                    "transformation_operators": ["cross-layer"],
                    "causal_topology_delta": "dependency graph completion",
                    "verifier_delta": "end-to-end plus layer preservation",
                    "causal_graph": {"nodes": ["api", "store"], "edges": ["api->store"]},
                    "non_equivalence_rationale": "partial layers fail independently",
                    "closest_portfolio_pattern_instance": "none",
                }
            ],
        }
        errors, summary = mix.validate(
            manifest,
            {"P1": "coupled", "P6": "holistic"},
            allow_partial=True,
            experimental_catalog={
                "X-cross-layer-feature-completion": "cross-layer-feature-completion"
            },
        )
        self.assertEqual([], errors)
        self.assertEqual(
            ["X-cross-layer-feature-completion"],
            summary["registered_experimental_used"],
        )

    def test_schema_v2_requires_frontier_stability(self) -> None:
        manifest = {
            "schema_version": 2,
            "expected_count": 1,
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
        errors, _ = mix.validate(manifest, {"P1": "pattern"})
        self.assertTrue(any("requires frontier_stability" in error for error in errors))

    def test_schema_v2_accepts_independent_traps_and_clean_retrieval(self) -> None:
        manifest = {
            "schema_version": 2,
            "expected_count": 1,
            "candidates": [
                {
                    "task_slug": "tbrain-one",
                    "track": "established",
                    "pattern_ids": ["P1"],
                    "causal_graph": {"nodes": ["a", "b"], "edges": ["a->b"]},
                    "non_equivalence_rationale": "new causal mechanism",
                    "closest_portfolio_pattern_instance": "none",
                    "frontier_stability": self._frontier_stability(),
                }
            ],
        }
        errors, summary = mix.validate(manifest, {"P1": "pattern"})
        self.assertEqual([], errors)
        self.assertTrue(summary["frontier_stability_required"])

    def test_schema_v2_rejects_retrievable_multi_mechanism_solution(self) -> None:
        stability = self._frontier_stability()
        stability["retrieval_audit"].update(
            {
                "exact_solution_found": True,
                "satisfied_mechanism_ids": ["authority", "invalidation"],
            }
        )
        manifest = {
            "schema_version": 2,
            "expected_count": 1,
            "candidates": [
                {
                    "task_slug": "tbrain-one",
                    "track": "established",
                    "pattern_ids": ["P1"],
                    "causal_graph": {"nodes": ["a", "b"], "edges": ["a->b"]},
                    "non_equivalence_rationale": "new causal mechanism",
                    "closest_portfolio_pattern_instance": "none",
                    "frontier_stability": stability,
                }
            ],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"})
        self.assertTrue(any("public artifact covers" in error for error in errors))

    def test_schema_v2_rejects_overlapping_trap_witnesses(self) -> None:
        stability = self._frontier_stability()
        stability["orthogonal_traps"][1]["witness_ids"] = ["authority-late"]
        manifest = {
            "schema_version": 2,
            "expected_count": 1,
            "candidates": [
                {
                    "task_slug": "tbrain-one",
                    "track": "established",
                    "pattern_ids": ["P1"],
                    "causal_graph": {"nodes": ["a", "b"], "edges": ["a->b"]},
                    "non_equivalence_rationale": "new causal mechanism",
                    "closest_portfolio_pattern_instance": "none",
                    "frontier_stability": stability,
                }
            ],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"})
        self.assertTrue(any("witness_ids overlap" in error for error in errors))

    def test_schema_v2_accepts_registered_derived_topology(self) -> None:
        stability = self._frontier_stability()
        stability.update(
            {
                "dominant_topology_id": "X-cross-layer-feature-completion",
                "secondary_topology_id": "P1",
                "amplifier_or_envelope_id": "P6",
            }
        )
        manifest = {
            "schema_version": 2,
            "expected_count": 3,
            "candidates": [
                {
                    "task_slug": "tbrain-layered-feature",
                    "track": "derived",
                    "parent_pattern_ids": ["P1", "P6"],
                    "derived_pattern_id": "X-cross-layer-feature-completion",
                    "transformation_operators": ["cross-layer"],
                    "causal_topology_delta": "dependency graph completion",
                    "verifier_delta": "end-to-end plus layer preservation",
                    "causal_graph": {"nodes": ["api", "store"], "edges": ["api->store"]},
                    "non_equivalence_rationale": "partial layers fail independently",
                    "closest_portfolio_pattern_instance": "none",
                    "frontier_stability": stability,
                }
            ],
        }
        errors, summary = mix.validate(
            manifest,
            {"P1": "coupled", "P6": "holistic"},
            allow_partial=True,
            experimental_catalog={
                "X-cross-layer-feature-completion": "cross-layer-feature-completion"
            },
        )
        self.assertEqual([], errors)
        self.assertEqual(
            ["X-cross-layer-feature-completion"],
            summary["registered_experimental_used"],
        )

    def test_schema_v2_rejects_undeclared_pattern_label_stacking(self) -> None:
        manifest = {
            "schema_version": 2,
            "expected_count": 1,
            "candidates": [
                {
                    "task_slug": "tbrain-one",
                    "track": "established",
                    "pattern_ids": ["P1", "P3"],
                    "causal_graph": {"nodes": ["a", "b"], "edges": ["a->b"]},
                    "non_equivalence_rationale": "new causal mechanism",
                    "closest_portfolio_pattern_instance": "none",
                    "frontier_stability": self._frontier_stability(),
                }
            ],
        }
        errors, _ = mix.validate(manifest, {"P1": "coupled", "P3": "evidence"})
        self.assertTrue(any("exactly match declared topology roles" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
