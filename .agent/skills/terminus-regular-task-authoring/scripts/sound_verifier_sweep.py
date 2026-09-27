#!/usr/bin/env python3
"""Run the pre-upload Sound Verifier sweep (accepted-task blueprint §5, C1-C18).

The sweep is a set of Oracle mutants: the reference fix plus one plausible slip each
(a cap on a list, a clamp at nought, half-away rounding, a reordered key), every one
of which must fail its own named test, plus one or two contract-valid alternatives
that must still score reward 1. Builders were writing this harness per task
(trace-metal's `sweep/build.py` + `score_all.sh`); this script is that harness once.

A catalog (JSON) declares the mutants; paths are relative to the task's
`environment/` directory, and each edit's `old` text must occur exactly once in the
reference-fixed file:

    {
      "reference_patch": "solution/fix.patch",
      "mutants": {
        "c5-runs-capped-64": {
          "class": "C5",
          "edits": [{"file": "app/src/pkg/report.py",
                     "old": "runs = batch[\\"runs\\"]",
                     "new": "runs = batch[\\"runs\\"][:64]"}],
          "expect_failing": ["test_capacity_batch"],
          "rationale": "section 1: up to eighty runs"
        }
      },
      "alternatives": {
        "alt-fsum": {"edits": [...], "rationale": "exact-sum rewrite the contract allows"}
      }
    }

Usage:
    sound_verifier_sweep.py <task> --catalog sweep.json --out workspace/reports/<slug>/sweep \\
        --verifier workspace/tools/score.sh [--jobs 4] [--build-only]

Each mutant is scored by `wrong_path_runner.py`, so every result is a snapshot-bound
receipt. `summary.json` lists each mutant's outcome and the C-classes the catalog
does not touch; an untouched class is not a failure, but the builder must say why it
does not apply. Exit 0 only when every mutant is rejected on its own witness and
every alternative scores reward 1.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "wrong_path_runner.py"
CLASSES = [f"C{n}" for n in range(1, 19)]
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", ".ruff_cache"}


def text_files(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir() or any(part in SKIP_DIRS for part in rel.parts):
            continue
        try:
            files[rel.as_posix()] = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return files


def apply_reference(task: Path, env_copy: Path, reference_patch: str) -> None:
    patch = (task / reference_patch).resolve()
    if not patch.is_file():
        raise SystemExit(f"reference patch not found: {patch}")
    for cwd in (env_copy, env_copy.parent):
        done = subprocess.run(["git", "apply", "--unidiff-zero", str(patch)], cwd=cwd,
                              capture_output=True, text=True)
        if done.returncode == 0:
            return
    raise SystemExit(f"reference patch does not apply to environment/: {done.stderr.strip()}")


def apply_edits(root: Path, edits: list[dict], label: str) -> None:
    for edit in edits:
        path = root / edit["file"]
        if not path.is_file():
            raise SystemExit(f"{label}: {edit['file']} does not exist under environment/")
        text = path.read_text(encoding="utf-8")
        count = text.count(edit["old"])
        if count != 1:
            raise SystemExit(f"{label}: 'old' text occurs {count} times in {edit['file']}, need exactly 1")
        path.write_text(text.replace(edit["old"], edit["new"]), encoding="utf-8")


def unified_patch(before: dict[str, str], after: dict[str, str]) -> str:
    """A patch against the shipped environment, in the a/ b/ form git apply takes."""
    chunks = []
    for rel in sorted(set(before) | set(after)):
        old, new = before.get(rel), after.get(rel)
        if old == new:
            continue
        chunks.append(f"diff --git a/{rel} b/{rel}\n")
        chunks.extend(difflib.unified_diff(
            (old or "").splitlines(keepends=True), (new or "").splitlines(keepends=True),
            fromfile=f"a/{rel}" if old is not None else "/dev/null",
            tofile=f"b/{rel}" if new is not None else "/dev/null"))
        if chunks and not chunks[-1].endswith("\n"):
            chunks[-1] += "\n\\ No newline at end of file\n"
    return "".join(chunks)


def build(task: Path, catalog: dict, out: Path) -> dict[str, Path]:
    shipped = task / "environment"
    before = text_files(shipped)
    patches: dict[str, Path] = {}
    with tempfile.TemporaryDirectory() as tmp:
        fixed = Path(tmp) / "environment"
        shutil.copytree(shipped, fixed, symlinks=True,
                        ignore=shutil.ignore_patterns(*SKIP_DIRS))
        apply_reference(task, fixed, catalog.get("reference_patch", "solution/fix.patch"))
        entries = [(k, v) for k, v in catalog.get("mutants", {}).items()]
        entries += [(k, v) for k, v in catalog.get("alternatives", {}).items()]
        for ident, entry in entries:
            variant = Path(tmp) / f"v-{ident}" / "environment"
            shutil.copytree(fixed, variant, symlinks=True)
            apply_edits(variant, entry.get("edits", []), ident)
            patch = out / f"{ident}.patch"
            patch.write_text(unified_patch(before, text_files(variant)), encoding="utf-8")
            patches[ident] = patch
    return patches


def score(task: Path, ident: str, patch: Path, witnesses: list[str], verifier: str, out: Path) -> dict:
    receipt = out / f"{ident}.json"
    env = dict(os.environ, CTRF_OUT=str(out / f".{ident}.ctrf.json"))
    cmd = [sys.executable, str(RUNNER), str(task), "--id", ident, "--patch", str(patch),
           "--verifier", verifier, "--ctrf", env["CTRF_OUT"], "--receipt", str(receipt)]
    for witness in witnesses or ["test_outputs.py::__alternative_expects_no_failure__"]:
        cmd += ["--expect-failing", witness if "::" in witness else f"test_outputs.py::{witness}"]
    done = subprocess.run(cmd, capture_output=True, text=True, env=env)
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"id": ident, "reward": None, "error": (done.stdout + done.stderr).strip()[-400:]}
    return {"id": ident, "reward": data["reward"], "status": data["status"],
            "failed": data["failed_test_ids"], "unexposed": data["unexposed_test_ids"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verifier", default="scripts/preflight.sh",
                        help="command wrong_path_runner.py runs on each variant task dir")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--build-only", action="store_true", help="write the patches, do not score")
    args = parser.parse_args()

    task = args.task.resolve()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out.resolve()
    mutants = catalog.get("mutants", {})
    alternatives = catalog.get("alternatives", {})
    bad = [k for k, v in mutants.items() if v.get("class") not in CLASSES or not v.get("expect_failing")]
    if bad:
        print(f"mutants need a class C1-C18 and at least one expect_failing test: {', '.join(bad)}")
        return 2

    patches = build(task, catalog, out)
    covered = sorted({v["class"] for v in mutants.values()}, key=lambda c: int(c[1:]))
    missing = [c for c in CLASSES if c not in covered]
    if args.build_only:
        print(f"wrote {len(patches)} patches to {out}; classes covered {covered}; untouched {missing}")
        return 0

    jobs = [(k, v.get("expect_failing", [])) for k, v in mutants.items()] + [(k, []) for k in alternatives]
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(lambda job: score(task, job[0], patches[job[0]], job[1], args.verifier, out), jobs))

    rows, ok = [], True
    for result in results:
        ident = result["id"]
        if ident in alternatives:
            passed = result.get("reward") == 1
            verdict = "accepted (alternative)" if passed else "REJECTED a contract-valid alternative"
        else:
            passed = result.get("status") == "pass"
            verdict = ("rejected on its own witness" if passed else
                       "SURVIVED (reward 1)" if result.get("reward") == 1 else
                       f"rejected elsewhere, witness still passed: {result.get('unexposed')}")
        ok = ok and passed
        rows.append({**result, "class": mutants.get(ident, {}).get("class", "alternative"),
                     "rationale": (mutants.get(ident) or alternatives.get(ident) or {}).get("rationale", ""),
                     "verdict": verdict})
        print(f"{'ok ' if passed else 'BAD'} {rows[-1]['class']:<11} {ident:<40} {verdict}")
    summary = {"schema_version": 1, "task": task.name, "classes_covered": covered,
               "classes_untouched": missing, "status": "pass" if ok else "fail", "results": rows}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\n{sum(r['verdict'].startswith(('rejected on', 'accepted')) for r in rows)}/{len(rows)} as expected; "
          f"classes untouched (say why each does not apply): {', '.join(missing) or 'none'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
