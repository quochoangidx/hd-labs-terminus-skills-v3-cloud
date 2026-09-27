#!/usr/bin/env python3
"""Check that the sealed fixtures reach both ends of every range the authority states.

The Sound Verifier panel climbs one ring of range edges per round: a floor or cap that
sits below or above every graded fixture scores reward 1 (icpms v9: five findings; v10:
seven more on ends the SOP had left open). Listing the ranges by hand missed them twice;
this lists them from a declared spec and reports the extremes the fixtures really reach.

Usage:
    fixture_bounds_check.py <task-dir> --spec <ranges.json> --adapter <observe.py> [--output receipt.json]

ranges.json is a list of rows, one per stated range:
    {"name": "mdl", "key": "mdl", "low": 0.0001, "high": 100}
    {"name": "CCV reading / true", "key": "ccv_ratio", "low": 0.5, "high": 1.5, "open": "both"}
    {"name": "intercept below nought", "key": "intercept", "must_reach_negative": true}
A closed end must be reached exactly (to 1e-9 relative); an open end ("low", "high" or
"both", for a strict "between") within 0.1% of it. Omit an end the authority does not
bound. A range with neither end is itself the defect: close it in the authority.
A quantity bounded relative to another ("at least ten times the loq") needs two rows: the
ratio, and its absolute extremes, which are products of the other range's ends (loq down
to 0.0001 makes the smallest CCV true 0.001). icpms v13 declared only the ratio, and a
max(1, true) denominator guard passed every fixture. Add a row for every value the package
divides by or compares against a limit.

observe.py defines observe(rows) -> {key: [values]}, where rows are every sealed row of
tests/expected (each JSON line of a .jsonl, or a whole .json). The adapter computes
derived quantities (readings, slopes, ratios) with the task's own independent model.

Exit 0 when every end is reached, 1 on a gap or a key the adapter did not report.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path


def load_rows(task: Path) -> list:
    rows = []
    expected = task / "tests" / "expected"
    for path in sorted(expected.rglob("*")) if expected.is_dir() else []:
        if path.suffix == ".jsonl":
            rows += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        elif path.suffix == ".json":
            rows.append(json.loads(path.read_text()))
    return rows


def reached(value, end, open_end: bool) -> bool:
    value, end = Fraction(value), Fraction(end)
    scale = max(abs(end), Fraction(1, 10**12))
    return abs(value - end) <= (Fraction(1, 1000) if open_end else Fraction(1, 10**9)) * scale


def check(spec: list[dict], seen: dict) -> tuple[list[dict], int]:
    rows, gaps = [], 0
    for item in spec:
        name, key = item["name"], item["key"]
        values = seen.get(key) or []
        open_ = item.get("open", "none")
        row = {"name": name, "key": key, "stated": [item.get("low"), item.get("high")]}
        if not values:
            row.update(status="GAP", reason="the adapter reported no value for this key")
            gaps += 1
            rows.append(row)
            continue
        lo, hi = min(values), max(values)
        row["reached"] = [float(lo), float(hi)]
        ok = True
        if "low" in item and not reached(lo, item["low"], open_ in ("low", "both")):
            ok = False
        if "high" in item and not reached(hi, item["high"], open_ in ("high", "both")):
            ok = False
        if item.get("must_reach_negative") and not lo < 0:
            ok = False
        if not any(k in item for k in ("low", "high", "must_reach_negative")):
            ok = False
            row["reason"] = "no end declared: an unbounded range cannot be reached; close it in the authority"
        row["status"] = "OK" if ok else "GAP"
        gaps += not ok
        rows.append(row)
    return rows, gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    loader = importlib.util.spec_from_file_location("bounds_adapter", args.adapter)
    module = importlib.util.module_from_spec(loader)
    sys.path.insert(0, str(args.adapter.resolve().parent))
    loader.loader.exec_module(module)
    seen = module.observe(load_rows(args.task_dir))
    rows, gaps = check(spec, seen)
    for row in rows:
        print(f"{row['status']:3s} {row['name']:30s} stated {row['stated']} reached {row.get('reached')} {row.get('reason', '')}")
    receipt = {"schema_version": 1, "task": args.task_dir.name, "ranges": rows, "gaps": gaps, "status": "pass" if gaps == 0 else "fail"}
    if args.output:
        args.output.write_text(json.dumps(receipt, indent=1) + "\n")
    return 0 if gaps == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
