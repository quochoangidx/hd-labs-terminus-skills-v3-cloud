#!/usr/bin/env python3
"""Fail fast on thin Terminus verifier plans and finalized matrices."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROFILES = {
    "cheap_deterministic": {"min_units": 50, "max_units": 1000, "min_clusters": 6},
    "expensive_stateful": {"min_units": 20, "max_units": 80, "min_clusters": 4},
}


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name}: root must be an object")
        return {}
    return value


def string_list(value: object, label: str, errors: list[str], *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or not all(nonempty(item) for item in value):
        errors.append(f"{label} must contain non-empty strings")
        return []
    result = [str(item) for item in value]
    if len(result) < minimum:
        errors.append(f"{label} requires at least {minimum} entries")
    if len(set(result)) != len(result):
        errors.append(f"{label} must not contain duplicates")
    return result


def profile_limits(profile: object, label: str, errors: list[str]) -> dict[str, int] | None:
    if profile not in PROFILES:
        errors.append(
            f"{label} must be cheap_deterministic or expensive_stateful"
        )
        return None
    return PROFILES[str(profile)]


def validate_unit_budget(
    profile: object,
    count: object,
    label: str,
    errors: list[str],
) -> dict[str, int] | None:
    limits = profile_limits(profile, f"{label}.profile", errors)
    if not isinstance(count, int) or isinstance(count, bool):
        errors.append(f"{label}.platform_visible_unit_count must be an integer")
        return limits
    if limits and not limits["min_units"] <= count <= limits["max_units"]:
        errors.append(
            f"{label}: {profile} requires {limits['min_units']}-{limits['max_units']} "
            f"platform-visible units, got {count}"
        )
    return limits


def validate_plan(data: dict) -> list[str]:
    """Validate the verifier architecture declared before task scaffolding."""

    errors: list[str] = []
    candidate = data.get("candidate", data)
    if not isinstance(candidate, dict):
        return ["candidate must be an object"]
    plan = candidate.get("verifier_architecture")
    if not isinstance(plan, dict):
        return ["candidate.verifier_architecture is required before cloning"]
    if plan.get("schema_version") != 1:
        errors.append("verifier_architecture.schema_version must be 1")
    if plan.get("status") != "pass":
        errors.append("verifier_architecture.status must be pass")
    profile = plan.get("profile")
    planned_count = plan.get("planned_platform_visible_unit_count")
    limits = validate_unit_budget(profile, planned_count, "verifier_architecture", errors)

    clusters = plan.get("semantic_clusters")
    cluster_ids: set[str] = set()
    planned_memberships = 0
    if not isinstance(clusters, list):
        errors.append("verifier_architecture.semantic_clusters must be a list")
        clusters = []
    for index, row in enumerate(clusters):
        label = f"verifier_architecture.semantic_clusters[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        cluster_id = row.get("id")
        if not nonempty(cluster_id) or str(cluster_id) in cluster_ids:
            errors.append(f"{label}.id must be unique and non-empty")
            continue
        cluster_ids.add(str(cluster_id))
        if not nonempty(row.get("description")):
            errors.append(f"{label}.description is required")
        planned_units = row.get("planned_unit_count")
        if not isinstance(planned_units, int) or isinstance(planned_units, bool) or planned_units < 1:
            errors.append(f"{label}.planned_unit_count must be a positive integer")
        else:
            planned_memberships += planned_units
    if limits and len(cluster_ids) < limits["min_clusters"]:
        errors.append(
            "verifier_architecture: "
            f"{profile} requires at least {limits['min_clusters']} semantic clusters"
        )
    if isinstance(planned_count, int) and planned_memberships < planned_count:
        errors.append(
            "verifier_architecture: semantic cluster memberships cannot cover the planned unit count"
        )

    surfaces = string_list(
        plan.get("public_surface_ids"),
        "verifier_architecture.public_surface_ids",
        errors,
    )
    candidate_surfaces = candidate.get("public_surfaces")
    declared_surface_ids: set[str] = set()
    if not isinstance(candidate_surfaces, list) or not candidate_surfaces:
        errors.append("candidate.public_surfaces must be a non-empty list")
    else:
        for index, row in enumerate(candidate_surfaces):
            value = row.get("id") if isinstance(row, dict) else row
            if not nonempty(value):
                errors.append(f"candidate.public_surfaces[{index}] needs a non-empty id")
            else:
                declared_surface_ids.add(str(value))
        if declared_surface_ids != set(surfaces):
            errors.append(
                "verifier_architecture.public_surface_ids must exactly match candidate.public_surfaces"
            )
    surface_clusters = plan.get("public_surface_cluster_ids")
    if not isinstance(surface_clusters, dict) or set(surface_clusters) != set(surfaces):
        errors.append(
            "verifier_architecture.public_surface_cluster_ids must map every public surface exactly"
        )
    else:
        for surface_id, value in surface_clusters.items():
            mapped = set(
                string_list(
                    value,
                    f"verifier_architecture.public_surface_cluster_ids[{surface_id!r}]",
                    errors,
                )
            )
            if not mapped <= cluster_ids:
                errors.append(
                    f"verifier_architecture: public surface {surface_id!r} references unknown clusters"
                )

    cross_rows = plan.get("cross_cluster_scenarios")
    if not isinstance(cross_rows, list) or len(cross_rows) < 2:
        errors.append("verifier_architecture.cross_cluster_scenarios requires at least two rows")
        cross_rows = []
    cross_ids: set[str] = set()
    for index, row in enumerate(cross_rows):
        label = f"verifier_architecture.cross_cluster_scenarios[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        row_id = row.get("id")
        if not nonempty(row_id) or str(row_id) in cross_ids:
            errors.append(f"{label}.id must be unique and non-empty")
        else:
            cross_ids.add(str(row_id))
        mapped = set(string_list(row.get("cluster_ids"), f"{label}.cluster_ids", errors, minimum=2))
        if not mapped <= cluster_ids:
            errors.append(f"{label}.cluster_ids references unknown clusters")
        if not nonempty(row.get("discriminating_scenario")):
            errors.append(f"{label}.discriminating_scenario is required")

    shapes = string_list(plan.get("verifier_shapes"), "verifier_architecture.verifier_shapes", errors)
    authority_substitute = plan.get("authority_corpus_substitute") is True
    if len(set(shapes)) < 2 and not (authority_substitute and len(cluster_ids) >= 6):
        errors.append("verifier_architecture requires at least two verifier shapes")
    if not nonempty(plan.get("platform_visibility_strategy")):
        errors.append("verifier_architecture.platform_visibility_strategy is required")
    if not nonempty(plan.get("nop_discrimination_strategy")):
        errors.append("verifier_architecture.nop_discrimination_strategy is required")
    return errors


def ctrf_tests(path: Path, errors: list[str]) -> tuple[list[str], dict]:
    data = load_object(path, errors)
    tests = data.get("tests")
    if not isinstance(tests, list):
        results = data.get("results")
        tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list):
        errors.append("verifier-matrix.json: CTRF tests must be a list")
        return [], data
    ids: list[str] = []
    for index, item in enumerate(tests):
        test_id = (item.get("name") or item.get("testId")) if isinstance(item, dict) else None
        if not nonempty(test_id):
            errors.append(f"verifier-matrix.json: CTRF tests[{index}] has no name/testId")
        else:
            ids.append(str(test_id))
    if len(set(ids)) != len(ids):
        errors.append("verifier-matrix.json: CTRF test IDs must be unique")
    return ids, data


def validate_matrix(
    data: dict,
    report_dir: Path,
    *,
    expected_slug: str | None = None,
    require_ctrf: bool = True,
) -> tuple[list[str], dict]:
    """Validate exact platform-visible units and their semantic architecture."""

    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("verifier-matrix.json: schema_version must be 1")
    if data.get("status") != "pass":
        errors.append("verifier-matrix.json: status must be pass")
    if expected_slug is not None and data.get("task_slug") != expected_slug:
        errors.append("verifier-matrix.json: task_slug mismatch")
    profile = data.get("profile")
    unit_ids = string_list(data.get("unit_ids"), "verifier-matrix.json: unit_ids", errors)
    declared_count = data.get("platform_visible_unit_count")
    if declared_count != len(unit_ids):
        errors.append("verifier-matrix.json: platform_visible_unit_count mismatch")
    limits = validate_unit_budget(profile, len(unit_ids), "verifier-matrix.json", errors)

    unit_clusters = data.get("unit_clusters")
    if not isinstance(unit_clusters, dict) or set(unit_clusters) != set(unit_ids):
        errors.append("verifier-matrix.json: unit_clusters must map every unit ID exactly")
        unit_clusters = {}
    else:
        for unit_id, value in unit_clusters.items():
            string_list(value, f"verifier-matrix.json: unit_clusters[{unit_id!r}]", errors)
    cluster_names = {
        cluster
        for clusters in unit_clusters.values()
        if isinstance(clusters, list)
        for cluster in clusters
        if nonempty(cluster)
    }
    if limits and len(cluster_names) < limits["min_clusters"]:
        errors.append(
            f"verifier-matrix.json: {profile} requires at least {limits['min_clusters']} semantic clusters"
        )
    if unit_ids and unit_clusters and cluster_names:
        dominant_ratio = max(
            sum(cluster in clusters for clusters in unit_clusters.values()) / len(unit_ids)
            for cluster in cluster_names
        )
        if dominant_ratio > 0.35 and not nonempty(data.get("dominant_cluster_justification")):
            errors.append("verifier-matrix.json: a cluster covers >35% of units without justification")

    cross_cluster = string_list(
        data.get("cross_cluster_unit_ids"),
        "verifier-matrix.json: cross_cluster_unit_ids",
        errors,
        minimum=2,
    )
    if not set(cross_cluster) <= set(unit_ids):
        errors.append("verifier-matrix.json: cross_cluster_unit_ids contains unknown units")
    for unit_id in set(cross_cluster) & set(unit_ids):
        if len(unit_clusters.get(unit_id, [])) < 2:
            errors.append(
                f"verifier-matrix.json: cross-cluster unit {unit_id!r} has fewer than two clusters"
            )

    shapes = string_list(data.get("verifier_shapes"), "verifier-matrix.json: verifier_shapes", errors)
    authority_substitute = data.get("authority_corpus_substitute") is True
    if len(set(shapes)) < 2 and not (authority_substitute and len(cluster_names) >= 6):
        errors.append("verifier-matrix.json: at least two verifier shapes are required")

    non_behavior = string_list(
        data.get("non_behavior_test_ids", []),
        "verifier-matrix.json: non_behavior_test_ids",
        errors,
        minimum=0,
    )
    if set(non_behavior) & set(unit_ids):
        errors.append("verifier-matrix.json: behavior and non-behavior test IDs overlap")

    ctrf = data.get("ctrf")
    if not require_ctrf and ctrf is None:
        pass
    elif not isinstance(ctrf, dict):
        errors.append("verifier-matrix.json: ctrf evidence is required")
    else:
        path_value = ctrf.get("path")
        if not nonempty(path_value):
            errors.append("verifier-matrix.json: ctrf.path is required")
        else:
            ctrf_path = (report_dir / str(path_value)).resolve()
            try:
                ctrf_path.relative_to(report_dir.resolve())
            except ValueError:
                errors.append("verifier-matrix.json: ctrf.path escapes the report directory")
            else:
                test_ids, ctrf_data = ctrf_tests(ctrf_path, errors)
                expected_ids = set(unit_ids) | set(non_behavior)
                if set(test_ids) != expected_ids or len(test_ids) != len(expected_ids):
                    errors.append(
                        "verifier-matrix.json: CTRF test IDs must exactly equal behavior plus "
                        "declared non-behavior IDs"
                    )
                summary = ctrf_data.get("summary") if isinstance(ctrf_data, dict) else None
                if not isinstance(summary, dict) and isinstance(ctrf_data, dict):
                    results = ctrf_data.get("results")
                    summary = results.get("summary") if isinstance(results, dict) else None
                if not isinstance(summary, dict) or summary.get("tests") != len(expected_ids):
                    errors.append(
                        "verifier-matrix.json: CTRF summary.tests must equal behavior plus "
                        "declared non-behavior tests"
                    )
                if ctrf.get("sha256") != (sha256(ctrf_path) if ctrf_path.is_file() else None):
                    errors.append("verifier-matrix.json: CTRF sha256 mismatch")

    return errors, {
        "unit_ids": set(unit_ids),
        "non_behavior_test_ids": set(non_behavior),
        "unit_clusters": unit_clusters,
        "cluster_names": cluster_names,
        "profile": profile,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("candidate", type=Path)
    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("verifier_matrix", type=Path)
    matrix_parser.add_argument("--task-slug")
    matrix_parser.add_argument("--allow-missing-ctrf", action="store_true")
    args = parser.parse_args()

    path = args.candidate if args.mode == "plan" else args.verifier_matrix
    load_errors: list[str] = []
    data = load_object(path.resolve(), load_errors)
    if args.mode == "plan":
        errors = load_errors + validate_plan(data)
    else:
        matrix_errors, _ = validate_matrix(
            data,
            path.resolve().parent,
            expected_slug=args.task_slug,
            require_ctrf=not args.allow_missing_ctrf,
        )
        errors = load_errors + matrix_errors
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"PASS: {path.name} verifier architecture meets the declared profile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
