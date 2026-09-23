#!/usr/bin/env python3
"""Run a wrong path against the verifier and write the receipt from what happened.

A wrong path is a deliberately incorrect submission. It earns its place only when the
verifier rejects it *and* the rejection lands on the witness for the rule it broke: a
mutant that fails everything shows the suite runs, not that any rule is discriminated.

The receipt exists so nobody has to take the builder's word for it. The builder chooses
which wrong paths to try; this script decides what the result was, binds it to the task
snapshot, and refuses to write a passing receipt for a mutant that survived.

Two ways to produce the variant:

    # revert one hunk of the reference fix — for a task built by seeding departures,
    # every hunk reverted on its own is a mutant, with no catalogue to write
    wrong_path_runner.py <task> --id shorter-side --revert-hunk 3 \\
        --expect-failing tests/test_outputs.py::test_depth_follows_the_shorter_side

    # or apply an explicit patch
    wrong_path_runner.py <task> --id latest-only --patch wrong-paths/latest-only.patch \\
        --expect-failing tests/test_outputs.py::test_authority_at_the_action_date

`--list-hunks` prints the reference patch's hunks so they can be reverted one at a time.

Exit 0 = the wrong path was rejected on its own witness. Exit 1 = it survived, or the
failure landed somewhere other than the witness it was supposed to expose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
HUNK_RE = re.compile(r"^@@ .* @@", re.M)


def tree_hash(root: Path) -> str:
    """The task snapshot hash the receipt is bound to.

    This must stay byte-for-byte the same function as ``panel_precheck.tree_hash``:
    the precheck rejects a receipt whose ``task_snapshot_sha256`` is not its own
    digest of the same tree, so two spellings of "the snapshot hash" make every
    wrong-path receipt unusable no matter how sound the wrong path was. The
    NUL separators below are what the precheck writes; do not drop them.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in VOLATILE_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def split_hunks(patch_text: str) -> list[dict]:
    """Split a unified diff into one entry per hunk, each carrying its file header."""
    hunks: list[dict] = []
    current_header: list[str] = []
    current_file = ""
    lines = patch_text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git ") or (line.startswith("--- ") and not current_header):
            current_header = []
            while index < len(lines) and not lines[index].startswith("@@"):
                current_header.append(lines[index])
                if lines[index].startswith("+++ "):
                    current_file = lines[index][4:].strip()
                index += 1
            continue
        if line.startswith("@@"):
            body = [line]
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@", "diff --git ")):
                body.append(lines[index])
                index += 1
            hunks.append(
                {
                    "index": len(hunks) + 1,
                    "file": current_file,
                    "header": "".join(current_header),
                    "body": "".join(body),
                    "label": line.strip(),
                }
            )
            continue
        index += 1
    return hunks


def patch_without_hunk(patch_text: str, drop: int) -> str:
    """The reference fix with one hunk left out, i.e. one departure still present."""
    kept = [hunk for hunk in split_hunks(patch_text) if hunk["index"] != drop]
    out: list[str] = []
    last_header = None
    for hunk in kept:
        if hunk["header"] != last_header:
            out.append(hunk["header"])
            last_header = hunk["header"]
        out.append(hunk["body"])
    return "".join(out)


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def failing_from_ctrf(ctrf_path: Path) -> tuple[set[str], set[str]]:
    data = json.loads(ctrf_path.read_text(encoding="utf-8"))
    tests = data.get("results", {}).get("tests", [])
    failed = {t["name"] for t in tests if t.get("status") not in {"passed", "skipped"}}
    passed = {t["name"] for t in tests if t.get("status") == "passed"}
    return failed, passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--id", help="wrong-path id, matching the manifest entry")
    parser.add_argument("--patch", type=Path, help="patch applied to create the wrong submission")
    parser.add_argument("--revert-hunk", type=int, help="apply the reference fix minus this hunk")
    parser.add_argument("--reference-patch", type=Path, default=Path("solution/fix.patch"))
    parser.add_argument("--expect-failing", action="append", default=[], help="witness that must fail, repeatable")
    parser.add_argument("--list-hunks", action="store_true")
    parser.add_argument("--verifier", default="scripts/preflight.sh", help="command run to score the variant")
    parser.add_argument("--ctrf", type=Path, help="CTRF report the verifier writes")
    parser.add_argument("--receipt", type=Path, help="where to write the receipt")
    args = parser.parse_args()

    task_dir: Path = args.task_dir.resolve()
    if not task_dir.is_dir():
        print(f"task folder not found: {task_dir}")
        return 2

    reference = task_dir / args.reference_patch
    if args.list_hunks:
        if not reference.is_file():
            print(f"reference patch not found: {reference}")
            return 2
        for hunk in split_hunks(reference.read_text(encoding="utf-8")):
            print(f"{hunk['index']:3}  {hunk['file']:40}  {hunk['label']}")
        return 0

    if not args.id:
        print("--id is required unless --list-hunks is used")
        return 2
    if bool(args.patch) == bool(args.revert_hunk):
        print("choose exactly one of --patch or --revert-hunk")
        return 2
    if not args.expect_failing:
        print(
            "--expect-failing is required: a wrong path that fails some test proves the "
            "suite runs, not that the broken rule is discriminated"
        )
        return 2

    snapshot = tree_hash(task_dir)
    work = Path(tempfile.mkdtemp(prefix=f"wrongpath-{args.id}-"))
    variant = work / task_dir.name
    shutil.copytree(task_dir, variant, symlinks=True)

    if args.revert_hunk:
        if not reference.is_file():
            print(f"reference patch not found: {reference}")
            return 2
        patch_text = patch_without_hunk(reference.read_text(encoding="utf-8"), args.revert_hunk)
        patch_path = work / "variant.patch"
        patch_path.write_text(patch_text, encoding="utf-8")
    else:
        patch_path = args.patch.resolve()

    applied = run(["git", "apply", "--unidiff-zero", str(patch_path)], cwd=variant / "environment")
    if applied.returncode != 0:
        applied = run(["git", "apply", "--unidiff-zero", str(patch_path)], cwd=variant)
    if applied.returncode != 0:
        print(f"could not apply the wrong-path patch:\n{applied.stderr.strip()}")
        return 2

    scored = run([args.verifier, str(variant)], cwd=Path.cwd())
    ctrf_path = args.ctrf if args.ctrf else None
    failed: set[str] = set()
    passed: set[str] = set()
    if ctrf_path and ctrf_path.is_file():
        failed, passed = failing_from_ctrf(ctrf_path)

    expected = set(args.expect_failing)
    missing = sorted(expected - failed)
    rejected = scored.returncode != 0 or bool(failed)
    ok = rejected and not missing

    receipt = {
        "schema_version": 1,
        "status": "pass" if ok else "fail",
        "wrong_path_id": args.id,
        "task_snapshot_sha256": snapshot,
        "reward": 0 if rejected else 1,
        "failed_test_ids": sorted(failed),
        "passed_control_ids": sorted(passed - expected),
        "expected_failing_test_ids": sorted(expected),
        "unexposed_test_ids": missing,
        "command": " ".join([args.verifier, str(variant)]),
        "exit_code": scored.returncode,
        "source": (
            f"reference patch minus hunk {args.revert_hunk}"
            if args.revert_hunk
            else str(args.patch)
        ),
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    shutil.rmtree(work, ignore_errors=True)

    if not rejected:
        print(
            f"{args.id}: the wrong submission was ACCEPTED (reward 1). The rule it breaks "
            "has no witness that can see it."
        )
        return 1
    if missing:
        print(
            f"{args.id}: rejected, but {', '.join(missing)} still passed. Something else "
            "caught it, so that witness does not discriminate this rule."
        )
        return 1
    print(f"{args.id}: rejected on its own witness ({', '.join(sorted(expected))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
