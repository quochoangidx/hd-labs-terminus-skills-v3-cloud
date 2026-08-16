#!/usr/bin/env python3
"""Validate the 80/20 established/derived task-design pattern manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CATALOG_PATTERN = re.compile(r"^## (P\d+) — `([^`]+)`$", re.MULTILINE)
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


def validate(
    manifest: dict[str, Any],
    catalog: dict[str, str],
    *,
    allow_partial: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must equal 1")

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

            operators = entry.get("transformation_operators")
            if not isinstance(operators, list) or not any(_nonempty(item) for item in operators):
                errors.append(f"{label}: derived track requires transformation_operators")

            changed = [field for field in DERIVED_DELTA_FIELDS if _nonempty(entry.get(field))]
            if len(changed) < 2:
                errors.append(
                    f"{label}: derived track needs material deltas in at least 2 of "
                    + ", ".join(DERIVED_DELTA_FIELDS)
                )

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
        "partial": allow_partial,
        "expected_count": expected,
        "established_target": established_target,
        "derived_target": derived_target,
        "established_count": counts["established"],
        "derived_count": counts["derived"],
        "catalog_pattern_ids": sorted(catalog),
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
        errors, summary = validate(manifest, catalog, allow_partial=args.allow_partial)
    except ValueError as exc:
        print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2))
        return 2

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
