#!/usr/bin/env python3
"""Prepare and summarize isolated local solve probes for Terminus tasks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "reports",
    "solution",
    "submissions",
    "tests",
}
EXCLUDE_PREFIXES = ("rubric",)
EXCLUDE_SUFFIXES = ("_rubric.md", "_rubric.txt", "-rubric.md", "-rubric.txt", ".zip")
VALID_RESULTS = {"pass", "fail"}
VALID_TYPES = {"semantic", "compile", "setup", "timeout", "unknown"}


def should_ignore(path: Path) -> bool:
    name = path.name
    if path.is_dir() and name in EXCLUDE_DIRS:
        return True
    if name.startswith(EXCLUDE_PREFIXES):
        return True
    return name.endswith(EXCLUDE_SUFFIXES)


def copy_task(src: Path, dst: Path, *, sanitized: bool) -> None:
    if dst.exists():
        raise SystemExit(f"Refusing to overwrite existing directory: {dst}")

    def ignore(directory: str, names: list[str]) -> set[str]:
        if not sanitized:
            return set()
        base = Path(directory)
        return {name for name in names if should_ignore(base / name)}

    shutil.copytree(src, dst, ignore=ignore)


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def prepare(args: argparse.Namespace) -> None:
    task = Path(args.task).resolve()
    if not task.exists() or not task.is_dir():
        raise SystemExit(f"Task folder not found: {task}")
    slug = task.name
    out = Path(args.output or Path("workspace/local-solve-probes") / slug).resolve()
    out.mkdir(parents=True, exist_ok=True)

    for idx in range(1, args.runs + 1):
        run_dir = out / f"run_{idx}"
        run_dir.mkdir(exist_ok=False)
        copy_task(task, run_dir / "solve", sanitized=True)
        copy_task(task, run_dir / "verify", sanitized=False)
        prompt = run_dir / "solve_prompt.md"
        prompt.write_text(
            "You are solving a Terminus Regular task locally. Work only inside "
            "this copied task folder. Do not search for solution, tests, rubrics, "
            "reports, or platform feedback. Read instruction.md and the codebase, "
            "make the fix, and run whatever local checks are available inside the "
            "copied environment. Stop when you have a candidate patch. This is a "
            "one-shot attempt: after your final answer, you will not receive "
            "verifier feedback for another try.\n",
            encoding="utf-8",
        )
        (run_dir / "result.json").write_text(
            json.dumps(
                {
                    "task": slug,
                    "run": idx,
                    "result": None,
                    "failure_type": None,
                    "notes": "",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(out)


def diff_run(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    solve = run_dir / "solve"
    verify = run_dir / "verify"
    if not solve.exists() or not verify.exists():
        raise SystemExit("run_dir must contain solve/ and verify/")
    proc = run(["diff", "-ruN", "--exclude", ".git", str(verify), str(solve)])
    patch = run_dir / "solve.diff"
    patch.write_text(proc.stdout, encoding="utf-8")
    print(patch)


def apply_run(args: argparse.Namespace) -> None:
    # WARNING: do NOT use `apply` when the solve copy was sanitized (the
    # default from `prepare`): the `diff -ruN` in `diff` records the
    # sanitized-away solution/ and tests/ as deletions, so applying it
    # corrupts verify/. Copy the solver's changed source file(s) into
    # verify/ manually instead (see SKILL.md, fair-probe section).
    print(
        "WARNING: `apply` corrupts verify/ when the solve copy was sanitized "
        "(diff records solution/ and tests/ as deletions). Prefer manually "
        "copying the changed source files into verify/ (see SKILL.md).",
        file=sys.stderr,
    )
    run_dir = Path(args.run_dir).resolve()
    patch = run_dir / "solve.diff"
    verify = run_dir / "verify"
    if not patch.exists():
        raise SystemExit(f"Missing patch: {patch}")
    if not verify.exists():
        raise SystemExit(f"Missing verify copy: {verify}")
    proc = run(["patch", "-p1", "-i", str(patch)], cwd=verify)
    (run_dir / "apply.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"Patch apply failed; see {run_dir / 'apply.log'}")
    print(run_dir / "apply.log")


def record(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    if args.result not in VALID_RESULTS:
        raise SystemExit(f"--result must be one of: {', '.join(sorted(VALID_RESULTS))}")
    if args.type not in VALID_TYPES:
        raise SystemExit(f"--type must be one of: {', '.join(sorted(VALID_TYPES))}")
    result_path = run_dir / "result.json"
    data = {}
    if result_path.exists():
        data = json.loads(result_path.read_text(encoding="utf-8"))
    data.update({"result": args.result, "failure_type": args.type, "notes": args.notes})
    result_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(result_path)


def summarize(args: argparse.Namespace) -> None:
    probe_dir = Path(args.probe_dir).resolve()
    records = []
    for result_path in sorted(probe_dir.glob("run_*/result.json")):
        records.append(json.loads(result_path.read_text(encoding="utf-8")))
    if not records:
        raise SystemExit(f"No result.json files found under {probe_dir}")
    total = len(records)
    passed = sum(1 for item in records if item.get("result") == "pass")
    failures: dict[str, int] = {}
    for item in records:
        if item.get("result") != "pass":
            failures[item.get("failure_type") or "unknown"] = failures.get(item.get("failure_type") or "unknown", 0) + 1
    # Thresholds are proportional to the actual run count; labels match the
    # SKILL.md Reporting vocabulary (submit_ready / gray_zone_review /
    # rework_or_replace / fix_task_first).
    semantic_like = set(failures) & {"semantic", "compile", "unknown"}
    if passed == 0:
        if failures and not semantic_like:
            recommendation = "fix_task_first"
        else:
            recommendation = "submit_ready"
    elif total <= 3:
        # Default regime: 2 runs, 3rd only on a 1-1 split.
        if total == 2 and passed == 1:
            recommendation = "gray_zone_review"  # 1-1 split: run the tie-break 3rd
        elif passed == 1:
            recommendation = "submit_ready"  # 1/3 after tie-break = hold
        else:
            recommendation = "rework_or_replace"  # 2/2 or 2/3+ = collapse
    else:
        # Escalated same-engine pooling (N>=4).
        rate = passed / total
        if rate >= 0.8:
            recommendation = "rework_or_replace"
        elif rate >= 0.4:
            recommendation = "gray_zone_review"
        else:
            recommendation = "submit_ready"
    summary = {
        "probe_dir": os.path.relpath(probe_dir),
        "runs": total,
        "passed": passed,
        "failed": total - passed,
        "failure_types": failures,
        "recommendation": recommendation,
    }
    out = probe_dir / "summary.md"
    out.write_text(
        "# Local Solve Probe Summary\n\n"
        f"- Runs: {total}\n"
        f"- Passed: {passed}\n"
        f"- Failed: {total - passed}\n"
        f"- Failure types: {json.dumps(failures, sort_keys=True)}\n"
        f"- Recommendation: `{recommendation}`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("task")
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--output")
    p.set_defaults(func=prepare)

    p = sub.add_parser("diff")
    p.add_argument("run_dir")
    p.set_defaults(func=diff_run)

    p = sub.add_parser("apply")
    p.add_argument("run_dir")
    p.set_defaults(func=apply_run)

    p = sub.add_parser("record")
    p.add_argument("run_dir")
    p.add_argument("--result", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--notes", default="")
    p.set_defaults(func=record)

    p = sub.add_parser("summarize")
    p.add_argument("probe_dir")
    p.set_defaults(func=summarize)

    args = parser.parse_args()
    if getattr(args, "runs", 1) < 1 or getattr(args, "runs", 1) > 5:
        raise SystemExit("--runs must be between 1 and 5")
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
