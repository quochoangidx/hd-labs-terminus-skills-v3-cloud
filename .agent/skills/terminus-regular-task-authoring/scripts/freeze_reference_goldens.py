#!/usr/bin/env python3
"""Freeze a reimplementation task's expected results from the reference program.

Human review treats a callable end-to-end solver in tests/ as a High finding
(docs/creating-tasks/writing-tests.md: "don't put a callable end-to-end solver in
tests/"), and a verifier that runs the real GNU binary on every case at grading time is
exactly that: the reference maps each input to the complete expected result. The same
docs list "precomputed golden fixtures or hashes for exact-match or byte-exact tasks" as
legitimate, so this script runs the reference once, at authoring time, inside the task's
own verifier image, and writes one short digest per case to tests/expected.json. The
verifier then compares the candidate's result digest with the frozen one and never runs
the reference.

The task's tests/test_outputs.py must expose:
    CASES                    list of case dicts, each with a "family" key, in check order
    run(command, case)       the exact runner check() uses for the candidate
    result_digest(result)    the digest check() compares
    inputs_digest(cases)     the digest that binds a family's frozen results to its cases

Host mode (default) builds the verifier image from tests/, adds the reference package
when the verifier image no longer ships it (--apt), and runs this script inside it:

    freeze_reference_goldens.py <task-dir> --reference /usr/bin/ed --apt ed \
        --version-arg=--version

Inner mode (--inner) is what runs in the container; it is not meant to be run by hand.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = 1


def inner(tests: Path, reference: list[str], version_arg: str | None, out: Path) -> int:
    sys.path.insert(0, str(tests))
    spec = importlib.util.spec_from_file_location("test_outputs", tests / "test_outputs.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("CASES", "run", "result_digest", "inputs_digest"):
        if not hasattr(module, name):
            print(f"tests/test_outputs.py does not define {name}")
            return 2

    version = ""
    if version_arg:
        proc = subprocess.run(reference + [version_arg], capture_output=True, text=True)
        version = (proc.stdout or proc.stderr).splitlines()[0].strip()

    families: dict[str, list] = {}
    for case in module.CASES:
        families.setdefault(case["family"], []).append(case)
    frozen = {}
    for family, cases in sorted(families.items()):
        results = [module.result_digest(module.run(list(reference), case)) for case in cases]
        frozen[family] = {"inputs": module.inputs_digest(cases), "results": results}
        print(f"{family:24} {len(results):5} cases")

    payload = {
        "schema": SCHEMA,
        "reference": " ".join(reference),
        "reference_version": version,
        "families": frozen,
    }
    # one family per line, no padding: the file counts against the panel's reading
    # budget (about 150 KB of text under tests/), so it stays as small as it can
    lines = ["{"]
    for key in ("schema", "reference", "reference_version"):
        lines.append(f"{json.dumps(key)}:{json.dumps(payload[key])},")
    lines.append('"families":{')
    items = sorted(frozen.items())
    for index, (family, entry) in enumerate(items):
        comma = "," if index < len(items) - 1 else ""
        lines.append(f"{json.dumps(family)}:{json.dumps(entry, sort_keys=True, separators=(',', ':'))}{comma}")
    lines.append("}}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json.loads(out.read_text(encoding="utf-8"))
    print(f"wrote {out} ({sum(len(f['results']) for f in frozen.values())} cases, {version or 'no version'})")
    return 0


def host(task: Path, reference: list[str], apt: list[str], version_arg: str | None) -> int:
    tests = task / "tests"
    tag = f"freeze-goldens-{task.name}".lower()
    subprocess.run(["docker", "build", "-q", "-t", tag, str(tests)], check=True)
    image = tag
    if apt:
        with tempfile.TemporaryDirectory() as ctx:
            Path(ctx, "Dockerfile").write_text(
                f"FROM {tag}\nRUN apt-get update && apt-get install -y --no-install-recommends "
                f"{' '.join(apt)} && rm -rf /var/lib/apt/lists/*\n",
                encoding="utf-8",
            )
            image = tag + "-ref"
            subprocess.run(["docker", "build", "-q", "-t", image, ctx], check=True)
    with tempfile.TemporaryDirectory() as work:
        # a private copy, so nothing the import leaves behind lands in the task tree
        shutil.copytree(tests, Path(work, "tests"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(__file__, Path(work, "freeze.py"))
        cmd = ["docker", "run", "--rm", "--network", "none", "-v", f"{work}:/work",
               "-e", "PYTHONDONTWRITEBYTECODE=1", image, "python3", "-I", "/work/freeze.py",
               "--inner", "--tests", "/work/tests", "--out", "/work/expected.json",
               "--reference", *reference]
        if version_arg:
            cmd.append(f"--version-arg={version_arg}")
        status = subprocess.run(cmd).returncode
        if status:
            return status
        shutil.copy(Path(work, "expected.json"), tests / "expected.json")
    print(f"frozen into {tests / 'expected.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", nargs="?", type=Path)
    parser.add_argument("--reference", nargs="+", required=True, help="reference command, e.g. /usr/bin/ed")
    parser.add_argument("--apt", action="append", default=[], help="Debian package holding the reference")
    parser.add_argument("--version-arg", help="argument that makes the reference print its version")
    parser.add_argument("--inner", action="store_true")
    parser.add_argument("--tests", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.inner:
        return inner(args.tests, args.reference, args.version_arg, args.out)
    if not args.task or not (args.task / "tests" / "test_outputs.py").is_file():
        parser.error("give a task folder with tests/test_outputs.py")
    return host(args.task.resolve(), args.reference, args.apt, args.version_arg)


if __name__ == "__main__":
    sys.exit(main())
