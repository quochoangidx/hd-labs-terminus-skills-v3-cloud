#!/usr/bin/env python3
"""Validate pattern allocation and schema-v2 frontier-stability evidence."""

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
        errors.append(f"{label}: schema v2 requires frontier_stability")
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
        elif not exact_found and (mechanisms or interactions):
            errors.append(
                f"{label}: retrieval overlap cannot be recorded when exact_solution_found is false"
            )
        elif exact_found and (len(set(mechanisms)) >= 2 or interactions):
            errors.append(
                f"{label}: public artifact covers >=2 mechanisms or a genuine interaction"
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


def validate(
    manifest: dict[str, Any],
    catalog: dict[str, str],
    *,
    allow_partial: bool = False,
    experimental_catalog: dict[str, str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    schema_version = manifest.get("schema_version")
    if schema_version not in {1, 2}:
        errors.append("schema_version must equal 1 (legacy) or 2")

    expected = manifest.get("expected_count")
    if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
        errors.append("expected_count must be a positive integer")
        expected = 0

    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates must be an array")
        candidates = []
    if expected:
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

        if schema_version == 2:
            _validate_frontier_stability(entry, label, track, errors)

    derived_target = (expected + 2) // 5 if expected else 0
    established_target = expected - derived_target if expected else 0
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

    summary = {
        "status": "fail" if errors else "pass",
        "schema_version": schema_version,
        "frontier_stability_required": schema_version == 2,
        "partial": allow_partial,
        "expected_count": expected,
        "established_target": established_target,
        "derived_target": derived_target,
        "established_count": counts["established"],
        "derived_count": counts["derived"],
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
        help="Allow a non-empty accepted prefix that does not exceed final track targets.",
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
