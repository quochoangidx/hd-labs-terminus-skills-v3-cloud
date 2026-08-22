#!/usr/bin/env python3
"""Validate legacy fixed mixes and adaptive schema-v3 candidate portfolios."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CATALOG_PATTERN = re.compile(r"^## (P\d+) — `([^`]+)`$", re.MULTILINE)
EXPERIMENTAL_PATTERN = re.compile(
    r"^## (X-[a-z0-9]+(?:-[a-z0-9]+)*) — `([^`]+)`$", re.MULTILINE
)
DERIVED_DELTA_FIELDS = (
    "causal_topology_delta",
    "work_surface_delta",
    "verifier_delta",
    "failure_geometry_delta",
)
STRUCTURAL_SIGNATURE_FIELDS = (
    "causal_topology",
    "work_surface",
    "verifier_architecture",
    "failure_geometry",
    "difficulty_source",
    "artifact_type",
)
RETRIEVAL_OVERLAP_CLASSIFICATIONS = {
    "none",
    "substrate_primitives",
    "partial_topology",
    "task_topology",
    "exact_solution",
}


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a JSON object")
    return data


def _catalog_ids(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read pattern catalog {path}: {exc}") from exc
    patterns = dict(CATALOG_PATTERN.findall(text))
    if not patterns:
        raise ValueError(f"no P* pattern headings found in {path}")
    return patterns


def _experimental_ids(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read pattern catalog {path}: {exc}") from exc
    return dict(EXPERIMENTAL_PATTERN.findall(text))


def _validate_causal_graph(entry: dict[str, Any], label: str, errors: list[str]) -> None:
    graph = entry.get("causal_graph")
    if not isinstance(graph, dict):
        errors.append(f"{label}: causal_graph must be an object")
        return
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or len(nodes) < 2:
        errors.append(f"{label}: causal_graph.nodes must contain at least 2 nodes")
    if not isinstance(edges, list) or not edges:
        errors.append(f"{label}: causal_graph.edges must contain at least 1 edge")


def _string_list(
    value: Any,
    field: str,
    label: str,
    errors: list[str],
    *,
    min_items: int = 0,
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"{label}: {field} must be an array of non-empty strings")
        return []
    if len(value) < min_items:
        errors.append(f"{label}: {field} must contain at least {min_items} items")
    return value


def _validate_frontier_stability(
    entry: dict[str, Any],
    label: str,
    track: str,
    errors: list[str],
) -> None:
    stability = entry.get("frontier_stability")
    if not isinstance(stability, dict):
        errors.append(f"{label}: schema v2+ requires frontier_stability")
        return

    if track == "established":
        applied = set(entry.get("pattern_ids") or [])
        expected_dominant = applied
    else:
        applied = set(entry.get("parent_pattern_ids") or [])
        derived_id = entry.get("derived_pattern_id")
        expected_dominant = {derived_id} if isinstance(derived_id, str) else set()

    dominant = stability.get("dominant_topology_id")
    if not isinstance(dominant, str) or dominant not in expected_dominant:
        errors.append(
            f"{label}: dominant_topology_id must be an applied P* ID for "
            "established or the candidate's X-* ID for derived"
        )

    secondary = stability.get("secondary_topology_id")
    if secondary is not None and (
        not isinstance(secondary, str) or secondary not in applied
    ):
        errors.append(f"{label}: secondary_topology_id must be an applied/parent P* ID")

    amplifier = stability.get("amplifier_or_envelope_id")
    if amplifier is not None and (amplifier not in {"P4", "P6"} or amplifier not in applied):
        errors.append(
            f"{label}: amplifier_or_envelope_id must be applied P4 or P6"
        )
    roles = [role for role in (dominant, secondary, amplifier) if isinstance(role, str)]
    if len(roles) != len(set(roles)):
        errors.append(f"{label}: topology role IDs must be distinct")
    if track == "established" and applied != set(roles):
        errors.append(
            f"{label}: established pattern_ids must exactly match declared topology roles"
        )

    planned_mechanisms = _string_list(
        stability.get("planned_mechanism_ids"),
        "frontier_stability.planned_mechanism_ids",
        label,
        errors,
        min_items=3,
    )
    planned_interactions = _string_list(
        stability.get("planned_interaction_ids"),
        "frontier_stability.planned_interaction_ids",
        label,
        errors,
        min_items=2,
    )
    if len(planned_mechanisms) != len(set(planned_mechanisms)):
        errors.append(f"{label}: planned_mechanism_ids must be unique")
    if len(planned_interactions) != len(set(planned_interactions)):
        errors.append(f"{label}: planned_interaction_ids must be unique")
    planned_nodes = set(planned_mechanisms) | set(planned_interactions)

    retrieval = stability.get("retrieval_audit")
    if not isinstance(retrieval, dict):
        errors.append(f"{label}: frontier_stability.retrieval_audit must be an object")
    else:
        _string_list(
            retrieval.get("search_queries"),
            "retrieval_audit.search_queries",
            label,
            errors,
            min_items=3,
        )
        _string_list(
            retrieval.get("public_artifacts_checked"),
            "retrieval_audit.public_artifacts_checked",
            label,
            errors,
            min_items=1,
        )
        mechanisms = _string_list(
            retrieval.get("satisfied_mechanism_ids"),
            "retrieval_audit.satisfied_mechanism_ids",
            label,
            errors,
        )
        interactions = _string_list(
            retrieval.get("satisfied_interaction_ids"),
            "retrieval_audit.satisfied_interaction_ids",
            label,
            errors,
        )
        unknown_mechanisms = set(mechanisms) - set(planned_mechanisms)
        unknown_interactions = set(interactions) - set(planned_interactions)
        if unknown_mechanisms:
            errors.append(
                f"{label}: retrieval audit names unknown mechanisms: "
                f"{sorted(unknown_mechanisms)}"
            )
        if unknown_interactions:
            errors.append(
                f"{label}: retrieval audit names unknown interactions: "
                f"{sorted(unknown_interactions)}"
            )
        exact_found = retrieval.get("exact_solution_found")
        if not isinstance(exact_found, bool):
            errors.append(f"{label}: retrieval_audit.exact_solution_found must be boolean")

        overlap_classification = retrieval.get("overlap_classification")
        if overlap_classification is None:
            # Read historical schema-v2/v3 receipts without forcing a rewrite.
            overlap_classification = "exact_solution" if exact_found else "none"
        elif overlap_classification not in RETRIEVAL_OVERLAP_CLASSIFICATIONS:
            errors.append(
                f"{label}: retrieval_audit.overlap_classification must be one of "
                f"{sorted(RETRIEVAL_OVERLAP_CLASSIFICATIONS)}"
            )

        callable_solution = retrieval.get("callable_solution_available", False)
        if not isinstance(callable_solution, bool):
            errors.append(
                f"{label}: retrieval_audit.callable_solution_available must be boolean"
            )

        if overlap_classification == "none" and (mechanisms or interactions):
            errors.append(
                f"{label}: retrieval overlap IDs require a non-none overlap_classification"
            )
        if overlap_classification in {"substrate_primitives", "partial_topology"}:
            if not (mechanisms or interactions):
                errors.append(
                    f"{label}: {overlap_classification} must name the overlapping "
                    "mechanisms or interactions"
                )
            if not _nonempty(retrieval.get("non_collapse_rationale")):
                errors.append(
                    f"{label}: retrieval_audit.non_collapse_rationale is required "
                    f"for {overlap_classification}"
                )
        if exact_found and overlap_classification != "exact_solution":
            errors.append(
                f"{label}: exact_solution_found=true requires overlap_classification=exact_solution"
            )
        if overlap_classification == "exact_solution" and not exact_found:
            errors.append(
                f"{label}: overlap_classification=exact_solution requires exact_solution_found=true"
            )
        if overlap_classification in {"task_topology", "exact_solution"}:
            errors.append(
                f"{label}: reachable public artifact contains the task-specific repair topology"
            )
        if callable_solution is True:
            errors.append(
                f"{label}: reachable public artifact provides a callable solution/oracle"
            )
        if retrieval.get("disposition") != "pass":
            errors.append(f"{label}: retrieval_audit.disposition must be pass")

    traps = stability.get("orthogonal_traps")
    if not isinstance(traps, list) or len(traps) < 2:
        errors.append(f"{label}: frontier_stability requires at least 2 orthogonal_traps")
    else:
        seen_ids: set[str] = set()
        seen_nodes: set[str] = set()
        seen_surfaces: set[str] = set()
        seen_witnesses: set[str] = set()
        for index, trap in enumerate(traps):
            trap_label = f"{label}.orthogonal_traps[{index}]"
            if not isinstance(trap, dict):
                errors.append(f"{trap_label}: trap must be an object")
                continue
            for field in (
                "id",
                "semantic_node",
                "repair_surface",
                "natural_implementation",
                "why_wrong",
            ):
                if not _nonempty(trap.get(field)):
                    errors.append(f"{trap_label}: {field} is required")
            trap_id = trap.get("id")
            node = trap.get("semantic_node")
            surface = trap.get("repair_surface")
            if isinstance(trap_id, str) and trap_id in seen_ids:
                errors.append(f"{trap_label}: trap id must be unique")
            if isinstance(node, str) and node in seen_nodes:
                errors.append(f"{trap_label}: semantic_node must be distinct")
            if isinstance(node, str) and node not in planned_nodes:
                errors.append(f"{trap_label}: semantic_node must reference a planned node")
            if isinstance(surface, str) and surface in seen_surfaces:
                errors.append(f"{trap_label}: repair_surface must be distinct")
            if isinstance(trap_id, str):
                seen_ids.add(trap_id)
            if isinstance(node, str):
                seen_nodes.add(node)
            if isinstance(surface, str):
                seen_surfaces.add(surface)
            witnesses = _string_list(
                trap.get("witness_ids"),
                f"orthogonal_traps[{index}].witness_ids",
                label,
                errors,
                min_items=1,
            )
            if len(witnesses) != len(set(witnesses)):
                errors.append(f"{trap_label}: witness_ids must be unique within the trap")
            overlap = seen_witnesses.intersection(witnesses)
            if overlap:
                errors.append(
                    f"{trap_label}: witness_ids overlap earlier traps: {sorted(overlap)}"
                )
            seen_witnesses.update(witnesses)

    if not _nonempty(stability.get("shared_fix_rationale")):
        errors.append(f"{label}: frontier_stability.shared_fix_rationale is required")


def _validate_schema_v3_candidate(
    entry: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    if entry.get("classification_timing") != "post_crux":
        errors.append(f"{label}: classification_timing must equal post_crux")

    crux = entry.get("domain_crux")
    if not isinstance(crux, dict):
        errors.append(f"{label}: schema v3 requires domain_crux")
    else:
        for field in (
            "failure_mode",
            "native_work_surface",
            "native_artifact_or_behavior",
            "difficulty_without_incidental_conventions",
        ):
            if not _nonempty(crux.get(field)):
                errors.append(f"{label}: domain_crux.{field} is required")

    audit = entry.get("convention_audit")
    if not isinstance(audit, dict):
        errors.append(f"{label}: schema v3 requires convention_audit")
    else:
        if audit.get("status") != "pass":
            errors.append(f"{label}: convention_audit.status must be pass")
        if audit.get("assertion_to_source_complete") is not True:
            errors.append(
                f"{label}: convention_audit.assertion_to_source_complete must be true"
            )
        conventions = audit.get("arbitrary_conventions")
        if not isinstance(conventions, list):
            errors.append(f"{label}: arbitrary_conventions must be an array")
        else:
            seen: set[str] = set()
            for index, convention in enumerate(conventions):
                item_label = f"{label}.arbitrary_conventions[{index}]"
                if not isinstance(convention, dict):
                    errors.append(f"{item_label}: convention must be an object")
                    continue
                convention_id = convention.get("id")
                if not _nonempty(convention_id):
                    errors.append(f"{item_label}: id is required")
                elif convention_id in seen:
                    errors.append(f"{item_label}: id must be unique")
                else:
                    seen.add(str(convention_id))
                if convention.get("source_type") not in {
                    "authority",
                    "visible_evidence",
                    "explicit_instruction",
                }:
                    errors.append(
                        f"{item_label}: source_type must be authority, "
                        "visible_evidence, or explicit_instruction"
                    )
                if not _nonempty(convention.get("source")):
                    errors.append(f"{item_label}: source is required")

    smoke = entry.get("source_smoke")
    if not isinstance(smoke, dict) or smoke.get("status") != "pass":
        errors.append(f"{label}: source_smoke.status must be pass")
    else:
        if not _nonempty(smoke.get("receipt")):
            errors.append(f"{label}: source_smoke.receipt is required")
        if not _nonempty(smoke.get("runtime_entrypoint")):
            errors.append(f"{label}: source_smoke.runtime_entrypoint is required")
        _string_list(
            smoke.get("verifier_dependencies"),
            "source_smoke.verifier_dependencies",
            label,
            errors,
            min_items=1,
        )
        if smoke.get("unprivileged_candidate_execution") is not True:
            errors.append(
                f"{label}: source_smoke.unprivileged_candidate_execution must be true"
            )

    signature = entry.get("structural_signature")
    if not isinstance(signature, dict):
        errors.append(f"{label}: schema v3 requires structural_signature")
    else:
        for field in STRUCTURAL_SIGNATURE_FIELDS:
            if not _nonempty(signature.get(field)):
                errors.append(f"{label}: structural_signature.{field} is required")

    fit = entry.get("pattern_fit_evidence")
    if not isinstance(fit, dict):
        errors.append(f"{label}: schema v3 requires pattern_fit_evidence")
        return
    stability = entry.get("frontier_stability")
    roles = set()
    if isinstance(stability, dict):
        roles = {
            value
            for value in (
                stability.get("dominant_topology_id"),
                stability.get("secondary_topology_id"),
                stability.get("amplifier_or_envelope_id"),
            )
            if isinstance(value, str)
        }
    if "P3" in roles:
        p3 = fit.get("P3")
        if not isinstance(p3, dict):
            errors.append(f"{label}: applied P3 requires pattern_fit_evidence.P3")
        else:
            _string_list(
                p3.get("authentic_evidence_sources"),
                "pattern_fit_evidence.P3.authentic_evidence_sources",
                label,
                errors,
                min_items=2,
            )
            if p3.get("synthetic_partition_only") is not False:
                errors.append(
                    f"{label}: P3 synthetic_partition_only must be false"
                )
    if "P5" in roles:
        p5 = fit.get("P5")
        if not isinstance(p5, dict):
            errors.append(f"{label}: applied P5 requires pattern_fit_evidence.P5")
        else:
            _string_list(
                p5.get("independent_native_consumers"),
                "pattern_fit_evidence.P5.independent_native_consumers",
                label,
                errors,
                min_items=2,
            )
    if "P6" in roles:
        p6 = fit.get("P6")
        if not isinstance(p6, dict):
            errors.append(f"{label}: applied P6 requires pattern_fit_evidence.P6")
        else:
            _string_list(
                p6.get("interacting_delivery_axes"),
                "pattern_fit_evidence.P6.interacting_delivery_axes",
                label,
                errors,
                min_items=2,
            )


def _validate_schema_v3_portfolio(
    manifest: dict[str, Any],
    candidates: list[Any],
    expected: int,
    allow_partial: bool,
    errors: list[str],
) -> tuple[list[str], list[str]]:
    budget = manifest.get("candidate_budget")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < expected:
        errors.append("candidate_budget must be an integer >= expected_count")
        budget = 0
    if budget and len(candidates) > budget:
        errors.append(
            f"candidate count {len(candidates)} exceeds candidate_budget {budget}"
        )
    if not candidates:
        errors.append("schema v3 requires at least one qualified candidate attempt")

    history = manifest.get("portfolio_history")
    if not isinstance(history, list):
        errors.append("portfolio_history must be an array")
    else:
        for index, item in enumerate(history):
            label = f"portfolio_history[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label}: entry must be an object")
                continue
            if not _nonempty(item.get("task_slug")):
                errors.append(f"{label}: task_slug is required")
            if item.get("track") not in {"established", "derived"}:
                errors.append(f"{label}: track must be established or derived")
            if not _nonempty(item.get("dominant_topology_id")):
                errors.append(f"{label}: dominant_topology_id is required")
            role_stack = item.get("role_stack")
            if not isinstance(role_stack, list) or any(
                not isinstance(value, str) or not value for value in role_stack
            ):
                errors.append(f"{label}: role_stack must be an array of non-empty strings")

    accepted = manifest.get("accepted_task_slugs")
    if not isinstance(accepted, list) or any(
        not isinstance(item, str) or not item.strip() for item in accepted
    ):
        errors.append("accepted_task_slugs must be an array of non-empty strings")
        accepted = []
    if len(accepted) != len(set(accepted)):
        errors.append("accepted_task_slugs must be unique")
    if allow_partial:
        if len(accepted) > expected:
            errors.append("accepted task count exceeds expected_count")
    elif len(accepted) != expected:
        errors.append(
            f"accepted task count {len(accepted)} does not equal expected_count {expected}"
        )

    candidate_slugs = {
        entry.get("task_slug")
        for entry in candidates
        if isinstance(entry, dict) and isinstance(entry.get("task_slug"), str)
    }
    unknown = set(accepted) - candidate_slugs
    if unknown:
        errors.append(
            f"accepted_task_slugs contains candidates absent from the ledger: {sorted(unknown)}"
        )

    for index, entry in enumerate(candidates):
        if not isinstance(entry, dict):
            continue
        disposition = entry.get("disposition")
        if disposition not in {"active", "rejected", "accepted"}:
            errors.append(
                f"candidates[{index}]: disposition must be active, rejected, or accepted"
            )
        slug = entry.get("task_slug")
        if not allow_partial and disposition == "active":
            errors.append(f"{slug}: final candidate ledger cannot contain active attempts")
        if slug in accepted and disposition != "accepted":
            errors.append(f"{slug}: accepted task must have disposition accepted")
        if disposition == "accepted" and slug not in accepted:
            errors.append(f"{slug}: disposition accepted requires accepted_task_slugs membership")
        if disposition == "rejected" and not _nonempty(entry.get("rejection_reason")):
            errors.append(f"{slug}: rejected candidate requires rejection_reason")

    dominant_ids: list[str] = []
    role_stacks: list[tuple[str, ...]] = []
    signatures: list[dict[str, Any]] = []
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        stability = entry.get("frontier_stability")
        if isinstance(stability, dict):
            dominant = stability.get("dominant_topology_id")
            dominant_ids.append(dominant if isinstance(dominant, str) else "")
            role_stacks.append(
                tuple(
                    value
                    for value in (
                        stability.get("dominant_topology_id"),
                        stability.get("secondary_topology_id"),
                        stability.get("amplifier_or_envelope_id"),
                    )
                    if isinstance(value, str)
                )
            )
        signature = entry.get("structural_signature")
        signatures.append(signature if isinstance(signature, dict) else {})

    for index in range(2, len(dominant_ids)):
        if dominant_ids[index] and len(set(dominant_ids[index - 2 : index + 1])) == 1:
            errors.append(
                f"candidates[{index}]: dominant topology repeats three times consecutively"
            )
        if role_stacks[index] and len(set(role_stacks[index - 2 : index + 1])) == 1:
            errors.append(
                f"candidates[{index}]: exact pattern-role stack repeats three times consecutively"
            )

    for index in range(1, len(signatures)):
        left = signatures[index - 1]
        right = signatures[index]
        if not left or not right:
            continue
        differences = sum(left.get(field) != right.get(field) for field in STRUCTURAL_SIGNATURE_FIELDS)
        if differences < 2:
            errors.append(
                f"candidates[{index}]: consecutive candidate differs on fewer than 2 structural axes"
            )

    return accepted, dominant_ids


def validate(
    manifest: dict[str, Any],
    catalog: dict[str, str],
    *,
    allow_partial: bool = False,
    experimental_catalog: dict[str, str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    schema_version = manifest.get("schema_version")
    if schema_version not in {1, 2, 3}:
        errors.append("schema_version must equal 1 or 2 (legacy), or 3")

    expected = manifest.get("expected_count")
    if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
        errors.append("expected_count must be a positive integer")
        expected = 0

    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates must be an array")
        candidates = []
    if expected and schema_version in {1, 2}:
        if allow_partial and not 1 <= len(candidates) <= expected:
            errors.append(
                f"partial candidate count {len(candidates)} must be between 1 and {expected}"
            )
        elif not allow_partial and len(candidates) != expected:
            errors.append(
                f"candidate count {len(candidates)} does not equal expected_count {expected}"
            )

    slugs: set[str] = set()
    counts = {"established": 0, "derived": 0}
    registered_experimental_used: set[str] = set()

    for index, raw_entry in enumerate(candidates):
        label = f"candidates[{index}]"
        if not isinstance(raw_entry, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        entry = raw_entry
        slug = entry.get("task_slug")
        if not isinstance(slug, str) or not slug.strip():
            errors.append(f"{label}: task_slug must be a non-empty string")
        elif slug in slugs:
            errors.append(f"{label}: duplicate task_slug {slug!r}")
        else:
            slugs.add(slug)
            label = slug

        track = entry.get("track")
        if track not in counts:
            errors.append(f"{label}: track must be established or derived")
            continue
        counts[track] += 1
        _validate_causal_graph(entry, label, errors)

        if not _nonempty(entry.get("non_equivalence_rationale")):
            errors.append(f"{label}: non_equivalence_rationale is required")
        if not _nonempty(entry.get("closest_portfolio_pattern_instance")):
            errors.append(f"{label}: closest_portfolio_pattern_instance is required")

        if track == "established":
            pattern_ids = entry.get("pattern_ids")
            if not isinstance(pattern_ids, list) or not pattern_ids:
                errors.append(f"{label}: established track requires pattern_ids")
            else:
                invalid = sorted(
                    {repr(item) for item in pattern_ids if not isinstance(item, str) or item not in catalog}
                )
                if invalid:
                    errors.append(f"{label}: unknown established pattern IDs {invalid}")
            if _nonempty(entry.get("derived_pattern_id")):
                errors.append(f"{label}: established track cannot set derived_pattern_id")
        else:
            parents = entry.get("parent_pattern_ids")
            if not isinstance(parents, list) or not parents:
                errors.append(f"{label}: derived track requires parent_pattern_ids")
            else:
                invalid = sorted(
                    {repr(item) for item in parents if not isinstance(item, str) or item not in catalog}
                )
                if invalid:
                    errors.append(f"{label}: unknown parent pattern IDs {invalid}")

            derived_id = entry.get("derived_pattern_id")
            if not isinstance(derived_id, str) or not re.fullmatch(
                r"X-[a-z0-9]+(?:-[a-z0-9]+)*", derived_id
            ):
                errors.append(f"{label}: derived_pattern_id must match X-<kebab-case>")
            elif experimental_catalog and derived_id in experimental_catalog:
                registered_experimental_used.add(derived_id)

            operators = entry.get("transformation_operators")
            if not isinstance(operators, list) or not any(_nonempty(item) for item in operators):
                errors.append(f"{label}: derived track requires transformation_operators")

            changed = [field for field in DERIVED_DELTA_FIELDS if _nonempty(entry.get(field))]
            if len(changed) < 2:
                errors.append(
                    f"{label}: derived track needs material deltas in at least 2 of "
                    + ", ".join(DERIVED_DELTA_FIELDS)
                )

        if schema_version in {2, 3}:
            _validate_frontier_stability(entry, label, track, errors)
        if schema_version == 3:
            _validate_schema_v3_candidate(entry, label, errors)

    derived_target = (expected + 2) // 5 if expected else 0
    established_target = expected - derived_target if expected else 0
    accepted: list[str] = []
    advisories: list[str] = []
    if schema_version in {1, 2}:
        if allow_partial and counts["derived"] > derived_target:
            errors.append(
                f"derived count {counts['derived']} exceeds final target {derived_target}"
            )
        elif not allow_partial and counts["derived"] != derived_target:
            errors.append(
                f"derived count {counts['derived']} does not match target {derived_target}"
            )
        if allow_partial and counts["established"] > established_target:
            errors.append(
                f"established count {counts['established']} exceeds final target {established_target}"
            )
        elif not allow_partial and counts["established"] != established_target:
            errors.append(
                f"established count {counts['established']} does not match target "
                f"{established_target}"
            )
    elif schema_version == 3:
        accepted, _ = _validate_schema_v3_portfolio(
            manifest, candidates, expected, allow_partial, errors
        )

    budget = manifest.get("candidate_budget") if schema_version == 3 else expected
    derived_min = 1 if isinstance(budget, int) and budget >= 3 else 0
    derived_max = max(derived_min, (3 * budget + 9) // 10) if isinstance(budget, int) else 0
    mix_in_band = derived_min <= counts["derived"] <= derived_max
    if schema_version == 3 and len(candidates) >= 3 and not mix_in_band:
        advisories.append(
            "derived attempts are outside the non-blocking 20-30% exploration band"
        )

    if schema_version == 3:
        by_slug = {
            entry.get("task_slug"): entry
            for entry in candidates
            if isinstance(entry, dict)
        }
        rolling: list[dict[str, Any]] = [
            item
            for item in manifest.get("portfolio_history", [])
            if isinstance(item, dict)
        ]
        for slug in accepted:
            entry = by_slug.get(slug, {})
            stability = entry.get("frontier_stability", {})
            rolling.append(
                {
                    "task_slug": slug,
                    "track": entry.get("track"),
                    "dominant_topology_id": stability.get("dominant_topology_id"),
                    "role_stack": [
                        value
                        for value in (
                            stability.get("dominant_topology_id"),
                            stability.get("secondary_topology_id"),
                            stability.get("amplifier_or_envelope_id"),
                        )
                        if isinstance(value, str)
                    ],
                }
            )
        window = rolling[-5:]
        if len(window) == 5:
            derived_accepted = sum(item.get("track") == "derived" for item in window)
            if derived_accepted not in {1, 2}:
                advisories.append(
                    "rolling five accepted tasks should contain one or two derived tasks"
                )
            dominants = [item.get("dominant_topology_id") for item in window]
            if any(dominants.count(value) > 3 for value in set(dominants) if value):
                advisories.append(
                    "one dominant topology exceeds three of the rolling five accepted tasks"
                )
            stacks = [tuple(item.get("role_stack") or []) for item in window]
            if any(
                stacks[index]
                and stacks[index] == stacks[index - 1] == stacks[index - 2]
                for index in range(2, len(stacks))
            ):
                advisories.append(
                    "an exact role stack occurs three times consecutively in the rolling window"
                )

    summary = {
        "status": "fail" if errors else "pass",
        "schema_version": schema_version,
        "frontier_stability_required": schema_version in {2, 3},
        "adaptive_candidate_portfolio": schema_version == 3,
        "partial": allow_partial,
        "expected_count": expected,
        "established_target": established_target if schema_version in {1, 2} else None,
        "derived_target": derived_target if schema_version in {1, 2} else None,
        "established_count": counts["established"],
        "derived_count": counts["derived"],
        "candidate_budget": budget,
        "accepted_task_slugs": accepted,
        "exploration_band": {
            "derived_min": derived_min,
            "derived_max": derived_max,
            "in_band": mix_in_band,
            "enforced": False,
        },
        "portfolio_advisories": advisories,
        "catalog_pattern_ids": sorted(catalog),
        "registered_experimental_pattern_ids": sorted(experimental_catalog or {}),
        "registered_experimental_used": sorted(registered_experimental_used),
        "errors": errors,
    }
    return errors, summary


def main() -> int:
    default_catalog = (
        Path(__file__).resolve().parents[2]
        / "task-miner"
        / "frontier_task_design_patterns.md"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--catalog", type=Path, default=default_catalog)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow an incomplete accepted prefix; schema v3 still validates every recorded attempt.",
    )
    args = parser.parse_args()

    try:
        manifest = _load_json(args.manifest)
        catalog = _catalog_ids(args.catalog)
        experimental_catalog = _experimental_ids(args.catalog)
        errors, summary = validate(
            manifest,
            catalog,
            allow_partial=args.allow_partial,
            experimental_catalog=experimental_catalog,
        )
    except ValueError as exc:
        print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2))
        return 2

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
