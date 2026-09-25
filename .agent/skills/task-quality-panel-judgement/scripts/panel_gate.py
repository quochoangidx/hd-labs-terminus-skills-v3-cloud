#!/usr/bin/env python3
"""Mechanical quality-panel bookkeeping: which axes a clearance must re-run, and
whether a snapshot carries a non-blocking verdict on every axis.

An axis verdict is valid for a snapshot only while every file that axis's
reviewers could see is unchanged. Both subcommands apply that one rule, so a
carried verdict is never a judgement call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_packets import AXIS_SURFACES, iter_files, sha256_file, sha256_tree  # noqa: E402

PACKET_OWN_FILES = ("_panel_docs/", "packet-manifest.json")
# Portal thresholds: Minor and Major block everywhere except
# protected_ground_truth, where only Major blocks. Unsure leaves the axis
# undecided, which never clears.
CLEARING = {"None", "Advisory"}
CLEARING_BY_AXIS = {"protected_ground_truth": {"None", "Advisory", "Minor"}}
SEVERITY_RANK = {"None": 0, "Advisory": 1, "Minor": 2, "Unsure": 2, "Major": 3}


def surface_files(task: Path, axis: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for surface in AXIS_SURFACES[axis]:
        source = task / surface
        if source.is_file():
            files[surface] = sha256_file(source)
            continue
        for path in iter_files(source):
            if not path.is_symlink():
                files[f"{surface}/{path.relative_to(source).as_posix()}"] = sha256_file(path)
    return files


def reviewed_files(packet_root_manifest: Path, axis: str) -> dict[str, str]:
    root = json.loads(packet_root_manifest.read_text())
    packet = Path(root["axis_packets"][axis])
    manifest = json.loads((packet / "packet-manifest.json").read_text())
    if manifest.get("axis") != axis:
        raise ValueError(f"{packet} is not the {axis} packet")
    return {
        path: digest
        for path, digest in manifest["files"].items()
        if not path.startswith(PACKET_OWN_FILES)
    }


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def clears(axis: str, entry: dict) -> bool:
    return entry.get("complete") is True and entry.get("verdict") in CLEARING_BY_AXIS.get(axis, CLEARING)


def clearance_axes(task: Path, discovery_manifest: Path, finding_axes: list[str],
                   discovery_report: Path | None = None) -> dict:
    unknown = sorted(set(finding_axes) - set(AXIS_SURFACES))
    if unknown:
        raise ValueError(f"unknown axis: {', '.join(unknown)}")
    finding_axes = list(finding_axes)
    if discovery_report is not None:
        # An Unsure, incomplete or still-blocking discovery axis was never
        # decided; carrying it would leave `check` failing with no way forward.
        axes = json.loads(discovery_report.read_text()).get("axes", {})
        finding_axes += [axis for axis in AXIS_SURFACES if not clears(axis, axes.get(axis, {}))]
    rerun, carried, changes = [], [], {}
    for axis in AXIS_SURFACES:
        changed = changed_paths(reviewed_files(discovery_manifest, axis), surface_files(task, axis))
        changes[axis] = changed
        (rerun if changed or axis in finding_axes else carried).append(axis)
    return {
        "discovery_snapshot_sha256": json.loads(discovery_manifest.read_text())["snapshot_sha256"],
        "current_snapshot_sha256": sha256_tree(task),
        "finding_axes": sorted(set(finding_axes)),
        "discovery_report": str(discovery_report) if discovery_report else None,
        "changed_files_by_axis": changes,
        "clearance_axes": rerun,
        "carried_axes": carried,
    }


def evidence_errors(axis: str, entry: dict, manifest: Path) -> list[str]:
    """A verdict must rest on raw reviews of that very packet, or on a cited
    platform report for an axis the platform did not flag."""
    reviewed = json.loads(manifest.read_text())["snapshot_sha256"]
    if entry.get("source") == "platform":
        platform = entry.get("platform_report")
        if not platform or not Path(platform).is_file():
            return [f"{axis}: platform verdict without an existing platform_report: {platform!r}"]
        return []
    errors = []
    reviewers = entry.get("reviewers") or []
    if len(reviewers) != 2:
        return [f"{axis}: expected two raw reviewer responses, found {len(reviewers)}"]
    for path in reviewers:
        if not Path(path).is_file():
            errors.append(f"{axis}: reviewer response missing: {path}")
            continue
        raw = json.loads(Path(path).read_text())
        if raw.get("axis") != axis or raw.get("snapshot_sha256") != reviewed:
            errors.append(f"{axis}: {path} is not a review of this axis on snapshot {reviewed}")
        if (raw.get("input_completeness") or {}).get("status") != "complete":
            errors.append(f"{axis}: {path} reports incomplete input")
    return errors


def check(task: Path, report: Path) -> dict:
    data = json.loads(report.read_text())
    snapshot = sha256_tree(task)
    errors: list[str] = []
    if data.get("snapshot_sha256") != snapshot:
        errors.append(f"report snapshot {data.get('snapshot_sha256')} is not the task snapshot {snapshot}")
    axes = data.get("axes", {})
    for axis in AXIS_SURFACES:
        entry = axes.get(axis)
        if not entry:
            errors.append(f"{axis}: no verdict recorded")
            continue
        if entry.get("complete") is not True:
            errors.append(f"{axis}: review incomplete")
        verdict = entry.get("verdict")
        if verdict not in CLEARING_BY_AXIS.get(axis, CLEARING):
            errors.append(f"{axis}: verdict {verdict!r} does not clear")
        manifest = entry.get("packet_manifest")
        if not manifest or not Path(manifest).is_file():
            errors.append(f"{axis}: packet_manifest missing: {manifest!r}")
            continue
        errors.extend(evidence_errors(axis, entry, Path(manifest)))
        changed = changed_paths(reviewed_files(Path(manifest), axis), surface_files(task, axis))
        if changed:
            errors.append(f"{axis}: verdict is stale, {len(changed)} visible file(s) changed since review: "
                          + ", ".join(changed[:5]))
    return {"snapshot_sha256": snapshot, "report": str(report), "passed": not errors, "errors": errors}


def write_report(task: Path, adjudication: Path, output: Path) -> dict:
    """Assemble report.json from raw reviewer files and the orchestrator's
    adjudication, so no verdict, completeness flag or hash is typed by hand.

    adjudication.json:
      {"packet_manifest": <default root manifest>,
       "reviewers_dir": <default dir holding <axis>-A.json and <axis>-B.json>,
       "axes": {<axis>: {"verdict": ..., "downgrade_reason": ...,
                         "packet_manifest"?: ..., "reviewers"?: [a, b],
                         "source"?: "platform", "platform_report"?: ...}}}
    """
    data = json.loads(adjudication.read_text())
    base = adjudication.parent
    resolve = lambda value: str((base / value).resolve()) if value else value  # noqa: E731
    axes: dict[str, dict] = {}
    errors: list[str] = []
    for axis in AXIS_SURFACES:
        given = (data.get("axes") or {}).get(axis)
        if not given or "verdict" not in given:
            errors.append(f"{axis}: no adjudicated verdict")
            continue
        entry = {"verdict": given["verdict"],
                 "packet_manifest": resolve(given.get("packet_manifest") or data.get("packet_manifest"))}
        if given.get("source") == "platform":
            entry.update(source="platform", platform_report=resolve(given.get("platform_report")), complete=True)
        else:
            reviewers = given.get("reviewers") or [
                str(Path(data.get("reviewers_dir", "reviewers")) / f"{axis}-{side}.json") for side in "AB"]
            reviewers = [resolve(path) for path in reviewers]
            raws = [json.loads(Path(path).read_text()) for path in reviewers if Path(path).is_file()]
            entry["reviewers"] = reviewers
            entry["complete"] = len(raws) == 2 and all(
                (raw.get("input_completeness") or {}).get("status") == "complete" for raw in raws)
            worst = max((raw.get("severity", "None") for raw in raws), key=lambda v: SEVERITY_RANK.get(v, 3),
                        default="None")
            entry["raw_severities"] = [raw.get("severity") for raw in raws]
            if SEVERITY_RANK.get(given["verdict"], 3) < SEVERITY_RANK.get(worst, 3):
                reason = (given.get("downgrade_reason") or "").strip()
                if not reason:
                    errors.append(f"{axis}: verdict {given['verdict']!r} is below raw {worst!r} "
                                  "without a downgrade_reason citing counter-evidence")
                entry["downgrade_reason"] = reason
        axes[axis] = entry
    if errors:
        return {"passed": False, "errors": errors, "report": None}
    report = {"snapshot_sha256": sha256_tree(task), "axes": axes, "adjudication": str(adjudication.resolve())}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return check(task, output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    axes = sub.add_parser("clearance-axes", help="axes a clearance must re-run after a repair batch")
    axes.add_argument("task_dir", type=Path)
    axes.add_argument("--discovery-manifest", required=True, type=Path,
                      help="root packet-manifest.json printed by prepare_packets.py for discovery")
    axes.add_argument("--finding-axis", action="append", default=[],
                      help="axis with a retained blocking finding; repeat")
    axes.add_argument("--discovery-report", type=Path,
                      help="discovery report.json; its Unsure, incomplete or blocking axes are re-run too")
    gate = sub.add_parser("check", help="every axis cleared on files identical to the task's")
    gate.add_argument("task_dir", type=Path)
    gate.add_argument("--report", required=True, type=Path)
    write = sub.add_parser("write-report", help="build report.json from raw reviews and the adjudication")
    write.add_argument("task_dir", type=Path)
    write.add_argument("--adjudication", required=True, type=Path)
    write.add_argument("--report", required=True, type=Path, help="report.json to write")
    for command in (axes, gate, write):
        command.add_argument("--output", type=Path, help="also write the JSON receipt here")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = args.task_dir.resolve()
    try:
        if args.command == "clearance-axes":
            result = clearance_axes(task, args.discovery_manifest, args.finding_axis, args.discovery_report)
        elif args.command == "write-report":
            result = write_report(task, args.adjudication, args.report)
        else:
            result = check(task, args.report)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}") from error
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    sys.stdout.write(text)
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
