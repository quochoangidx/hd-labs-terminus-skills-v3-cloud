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
                "overlap_classification": "none",
                "callable_solution_available": False,
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

    @classmethod
    def _schema_v3_candidate(cls, slug: str = "tbrain-one") -> dict:
        return {
            "task_slug": slug,
            "classification_timing": "post_crux",
            "disposition": "active",
            "track": "established",
            "pattern_ids": ["P1"],
            "domain_crux": {
                "failure_mode": "durable state becomes stale after replay",
                "native_work_surface": "journal recovery engine",
                "native_artifact_or_behavior": "recovered database state",
                "difficulty_without_incidental_conventions": "ordering and invalidation interact",
            },
            "convention_audit": {
                "status": "pass",
                "assertion_to_source_complete": True,
                "arbitrary_conventions": [],
            },
            "source_smoke": {
                "status": "pass",
                "receipt": "source-smoke.json",
                "runtime_entrypoint": "python3 -m pytest --version",
                "verifier_dependencies": ["python3", "pytest"],
                "unprivileged_candidate_execution": True,
            },
            "structural_signature": {
                "causal_topology": "replay-invalidation",
                "work_surface": "journal",
                "verifier_architecture": "fault-injection",
                "failure_geometry": "stale-derived-state",
                "difficulty_source": "ordering-invariant",
                "artifact_type": "database-state",
            },
            "pattern_fit_evidence": {},
            "causal_graph": {"nodes": ["replay", "cache"], "edges": ["replay->cache"]},
            "non_equivalence_rationale": "new recovery interaction",
            "closest_portfolio_pattern_instance": "none",
            "frontier_stability": cls._frontier_stability(),
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
                "overlap_classification": "exact_solution",
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
        self.assertTrue(any("task-specific repair topology" in error for error in errors))

    def test_schema_v3_accepts_multi_mechanism_substrate_overlap(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["frontier_stability"]["retrieval_audit"].update(
            {
                "overlap_classification": "substrate_primitives",
                "satisfied_mechanism_ids": ["authority", "invalidation"],
                "non_collapse_rationale": (
                    "The public library exposes parsing primitives but not the "
                    "candidate's replay-to-invalidation repair topology."
                ),
            }
        )
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 1,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"}, allow_partial=True)
        self.assertEqual([], errors)

    def test_schema_v3_accepts_compact_causal_core(self) -> None:
        candidate = self._schema_v3_candidate()
        stability = candidate["frontier_stability"]
        stability["planned_mechanism_ids"] = ["authority", "invalidation"]
        stability["planned_interaction_ids"] = ["authority-invalidation"]
        stability["orthogonal_traps"] = [stability["orthogonal_traps"][0]]
        stability.pop("shared_fix_rationale")
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"}, allow_partial=True)
        self.assertEqual([], errors)

    def test_schema_v3_accepts_partial_topology_interaction_overlap(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["frontier_stability"]["retrieval_audit"].update(
            {
                "overlap_classification": "partial_topology",
                "satisfied_interaction_ids": ["authority-invalidation"],
                "non_collapse_rationale": (
                    "The public implementation contains one generic interaction but "
                    "not the task-local evidence chain or complete repair topology."
                ),
            }
        )
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 1,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"}, allow_partial=True)
        self.assertEqual([], errors)

    def test_schema_v3_rejects_task_topology_even_without_exact_patch(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["frontier_stability"]["retrieval_audit"].update(
            {
                "overlap_classification": "task_topology",
                "satisfied_mechanism_ids": ["authority", "invalidation"],
                "satisfied_interaction_ids": ["authority-invalidation"],
            }
        )
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 1,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"}, allow_partial=True)
        self.assertTrue(any("task-specific repair topology" in error for error in errors))

    def test_schema_v3_rejects_callable_public_oracle(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["frontier_stability"]["retrieval_audit"].update(
            {"callable_solution_available": True}
        )
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 1,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P1": "pattern"}, allow_partial=True)
        self.assertTrue(any("callable solution/oracle" in error for error in errors))

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

    def test_schema_v3_accepts_active_candidate_before_acceptance(self) -> None:
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 0,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [self._schema_v3_candidate()],
        }
        errors, summary = mix.validate(
            manifest, {"P1": "coupled"}, allow_partial=True
        )
        self.assertEqual([], errors)
        self.assertTrue(summary["adaptive_candidate_portfolio"])
        self.assertFalse(summary["candidate_limit_enforced"])
        self.assertIsNone(summary["candidate_budget"])
        self.assertFalse(summary["exploration_band"]["enforced"])

    def test_schema_v3_final_acceptance_does_not_require_exact_mix(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["disposition"] = "accepted"
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": [],
            "accepted_task_slugs": ["tbrain-one"],
            "candidates": [candidate],
        }
        errors, summary = mix.validate(manifest, {"P1": "coupled"})
        self.assertEqual([], errors)
        self.assertEqual(["tbrain-one"], summary["accepted_task_slugs"])

    def test_schema_v3_final_rejects_unresolved_active_attempt(self) -> None:
        accepted = self._schema_v3_candidate("tbrain-accepted")
        accepted["disposition"] = "accepted"
        active = self._schema_v3_candidate("tbrain-active")
        active["frontier_stability"]["dominant_topology_id"] = "P2"
        active["pattern_ids"] = ["P2"]
        active["structural_signature"]["causal_topology"] = "recovery-state-machine"
        active["structural_signature"]["work_surface"] = "transaction-log"
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": [],
            "accepted_task_slugs": ["tbrain-accepted"],
            "candidates": [accepted, active],
        }
        errors, _ = mix.validate(manifest, {"P1": "coupled", "P2": "recovery"})
        self.assertTrue(any("cannot contain active attempts" in error for error in errors))

    def test_schema_v3_rejects_untraceable_convention(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["convention_audit"]["arbitrary_conventions"] = [
            {"id": "tie-break", "source_type": "oracle", "source": "hidden"}
        ]
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P1": "coupled"}, allow_partial=True)
        self.assertTrue(any("source_type" in error for error in errors))

    def test_schema_v3_rejects_third_repeated_topology(self) -> None:
        candidates = [
            self._schema_v3_candidate(f"tbrain-{index}") for index in range(3)
        ]
        for index, candidate in enumerate(candidates):
            candidate["structural_signature"]["work_surface"] = f"surface-{index}"
            candidate["structural_signature"]["artifact_type"] = f"artifact-{index}"
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": candidates,
        }
        errors, _ = mix.validate(manifest, {"P1": "coupled"}, allow_partial=True)
        self.assertTrue(any("repeats three times" in error for error in errors))

    def test_schema_v3_requires_two_structural_differences(self) -> None:
        first = self._schema_v3_candidate("tbrain-first")
        second = self._schema_v3_candidate("tbrain-second")
        second["structural_signature"]["work_surface"] = "another surface"
        second["frontier_stability"]["dominant_topology_id"] = "P2"
        second["pattern_ids"] = ["P2"]
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [first, second],
        }
        errors, _ = mix.validate(
            manifest, {"P1": "coupled", "P2": "recovery"}, allow_partial=True
        )
        self.assertTrue(any("fewer than 2 structural axes" in error for error in errors))

    def test_schema_v3_requires_specific_p3_fit_evidence(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["pattern_ids"] = ["P3"]
        candidate["frontier_stability"]["dominant_topology_id"] = "P3"
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": [],
            "accepted_task_slugs": [],
            "candidates": [candidate],
        }
        errors, _ = mix.validate(manifest, {"P3": "evidence"}, allow_partial=True)
        self.assertTrue(any("pattern_fit_evidence.P3" in error for error in errors))

    def test_schema_v3_rolling_mix_is_advisory_not_blocking(self) -> None:
        candidate = self._schema_v3_candidate()
        candidate["disposition"] = "accepted"
        history = [
            {
                "task_slug": f"tbrain-history-{index}",
                "track": "established",
                "dominant_topology_id": "P1",
                "role_stack": ["P1"],
            }
            for index in range(4)
        ]
        manifest = {
            "schema_version": 3,
            "expected_count": 1,
            "candidate_budget": 6,
            "portfolio_history": history,
            "accepted_task_slugs": ["tbrain-one"],
            "candidates": [candidate],
        }
        errors, summary = mix.validate(manifest, {"P1": "coupled"})
        self.assertEqual([], errors)
        self.assertTrue(summary["portfolio_advisories"])


if __name__ == "__main__":
    unittest.main()
