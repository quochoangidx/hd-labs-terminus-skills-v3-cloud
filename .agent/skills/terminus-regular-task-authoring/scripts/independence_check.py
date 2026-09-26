#!/usr/bin/env python3
"""Check that the verifier's expected values do not come from the code under repair.

The usual chain is circular: the reference defines the behaviour, the verifier records
what the reference does, and the reference then passes. Oracle=1 proves nothing under
that arrangement, which is why a reference reviewer normally has to read the patch.

A task that re-derives its expected answers from the visible authority breaks the
circle: Oracle=1 becomes two independent derivations of one authority agreeing. This
script checks the derivation really is independent, i.e. that the module holding the
expectations never imports, loads or executes the package being repaired.

The model itself belongs in solution/, never in tests/. docs/creating-tasks/
writing-tests.md ("Reimplementing the Solution in Tests") forbids a callable in the
test tree that maps task inputs to the complete expected artifact, and human review
returned crop-water v3 and royalty v3 for exactly that ("no end-to-end solver in
tests"). The pattern is a solution/model.py whose ``__main__`` seals its answers into
tests/expected/ with a SHA-256 manifest, and tests that only load those files. So a
``--model`` under tests/ is a blocking ``model_in_tests`` finding, and every run also
scans tests/ for an undeclared model and reports it as an advisory.

Usage:
    independence_check.py <task-folder> --model solution/model.py [--model ...]
        [--package <name>] [--report-json <path>]

Exit 0 = independent. Exit 1 = the expectation model can reach the implementation,
or it sits under tests/.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
# Running the implementation is the same contamination as importing it, just spelled
# differently, so the process and dynamic-import surface counts too.
DYNAMIC_ENTRY = {
    "__import__",
    "importlib.import_module",
    "importlib.util.spec_from_file_location",
    "exec",
    "eval",
    "subprocess.run",
    "subprocess.check_output",
    "subprocess.check_call",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "runpy.run_path",
    "runpy.run_module",
}
# Stems that name a whole-answer module. Only a hint: the auto-scan also needs the test
# files to import the module before it says anything, and even then it only advises.
MODEL_STEMS = {
    "model",
    "models",
    "reference",
    "reference_model",
    "ref_model",
    "oracle",
    "expected_model",
    "solver",
    "solution",
}


def tree_hash(root: Path) -> str:
    """The task snapshot hash every receipt in this repo is bound to.

    Must stay byte-for-byte identical to ``panel_precheck.tree_hash``. A receipt
    carrying a differently-computed digest binds to a snapshot no other gate
    recognises, so it can never be reconciled no matter how sound the check was.
    The NUL separators are part of that contract: without them a path ending and
    the file bytes that follow are indistinguishable from a longer path.
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


def package_names(task_dir: Path) -> set[str]:
    """Top-level module and package names that live under environment/."""
    names: set[str] = set()
    env = task_dir / "environment"
    if not env.is_dir():
        return names
    for path in env.rglob("*"):
        if any(part in VOLATILE_DIRS for part in path.relative_to(env).parts):
            continue
        if path.is_dir() and (path / "__init__.py").is_file():
            names.add(path.name)
        elif path.is_file() and path.suffix in {".py", ".java", ".go", ".rs"}:
            names.add(path.stem)
    names.discard("__init__")
    return names


def _dotted(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def scan_model(path: Path, forbidden: set[str]) -> list[dict]:
    """Report every way this module could reach the implementation."""
    findings: list[dict] = []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [{"line": 0, "kind": "unreadable", "detail": str(exc)}]
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [{"line": exc.lineno or 0, "kind": "syntax", "detail": str(exc)}]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden:
                    findings.append({"line": node.lineno, "kind": "import", "detail": alias.name})
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in forbidden or node.level:
                findings.append(
                    {
                        "line": node.lineno,
                        "kind": "import",
                        "detail": ("." * node.level) + (node.module or ""),
                    }
                )
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            if name in DYNAMIC_ENTRY:
                rendered = " ".join(ast.unparse(node).split())[:200]
                # A dynamic entry point that provably cannot name the implementation is
                # still worth seeing, but only one that can is a defect.
                reaches = any(re.search(rf"\b{re.escape(pkg)}\b", rendered) for pkg in forbidden)
                findings.append(
                    {
                        "line": node.lineno,
                        "kind": "dynamic_entry" if reaches else "dynamic_entry_unresolved",
                        "detail": rendered,
                    }
                )
    return findings


def under_tests(task_dir: Path, rel: str) -> bool:
    """True when a task-relative path resolves inside the task's tests/ tree."""
    try:
        (task_dir / rel).resolve().relative_to((task_dir / "tests").resolve())
    except ValueError:
        return False
    return True


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def _loads_saved_expectations(tree: ast.AST) -> bool:
    """A module naming an expected/ directory or a manifest reads sealed answers."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.lower()
            if value == "expected" or "expected/" in value or "manifest" in value:
                return True
    return False


def _parse(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None


def scan_tests_for_models(task_dir: Path) -> list[dict]:
    """Advisory: helper modules in tests/ that look like an end-to-end expectation model.

    Conservative on purpose. Only top-level tests/*.py helpers are considered, and one is
    reported only when a test file imports it and either its name says it is the model
    or it defines an ``*expected*`` function without reading any sealed expectations.
    """
    tests = task_dir / "tests"
    if not tests.is_dir():
        return []
    helpers: dict[str, Path] = {}
    imported: set[str] = set()
    for path in sorted(tests.glob("*.py")):
        stem = path.stem
        if stem.startswith("test_") or stem.endswith("_test"):
            tree = _parse(path)
            if tree is not None:
                imported |= _imported_names(tree)
        elif stem != "conftest":
            helpers[stem] = path

    findings: list[dict] = []
    for stem, path in helpers.items():
        if stem not in imported:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        rel = path.relative_to(task_dir).as_posix()
        if stem.lower() in MODEL_STEMS:
            reason = f"test files import a helper named '{stem}'"
        else:
            makers = [
                node.name
                for node in getattr(tree, "body", [])
                if isinstance(node, ast.FunctionDef) and "expected" in node.name.lower()
            ]
            if not makers or _loads_saved_expectations(tree):
                continue
            reason = f"test files import it and it computes {', '.join(makers)}() without loading saved expectations"
        findings.append({"path": rel, "kind": "model_in_tests_suspected", "detail": reason})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="task-relative path of a module holding expected values, repeatable "
        "(normally solution/model.py; a path under tests/ is a blocking finding)",
    )
    parser.add_argument(
        "--package",
        action="append",
        default=[],
        help="extra implementation name to forbid; defaults are read from environment/",
    )
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()

    task_dir: Path = args.task_dir
    if not task_dir.is_dir():
        print(f"task folder not found: {task_dir}")
        return 2

    forbidden = package_names(task_dir) | set(args.package)
    if args.model and not forbidden:
        print("no implementation names found under environment/ — pass --package explicitly")
        return 2

    models: list[dict] = []
    blocking = 0
    for rel in args.model:
        path = task_dir / rel
        if not path.is_file():
            models.append({"path": rel, "status": "missing", "findings": []})
            blocking += 1
            continue
        findings = scan_model(path, forbidden)
        hard = [f for f in findings if f["kind"] != "dynamic_entry_unresolved"]
        status = "independent" if not hard else "contaminated"
        if under_tests(task_dir, rel):
            # Independent or not, a model under tests/ is an end-to-end solver shipped
            # with the verifier (writing-tests.md; crop-water v3 and royalty v3 returns).
            findings.insert(
                0,
                {
                    "line": 0,
                    "kind": "model_in_tests",
                    "detail": "move it to solution/ and seal its output into tests/expected/ "
                    "with a SHA-256 manifest; tests load the saved files",
                },
            )
            hard.append(findings[0])
            status = "model_in_tests" if status == "independent" else status
        blocking += len(hard)
        models.append({"path": rel, "status": status, "findings": findings})

    declared = {(task_dir / rel).resolve() for rel in args.model}
    advisories = [
        f
        for f in scan_tests_for_models(task_dir)
        if (task_dir / f["path"]).resolve() not in declared
    ]

    report = {
        "schema_version": 1,
        "check": "independence",
        "task_slug": task_dir.name,
        "task_snapshot_sha256": tree_hash(task_dir),
        "forbidden_names": sorted(forbidden),
        "models": models,
        "advisories": advisories,
        "status": "pass" if blocking == 0 else "fail",
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for model in models:
        print(f"{model['status']:14} | {model['path']}")
        for finding in model["findings"]:
            print(f"               | line {finding['line']}: {finding['kind']} — {finding['detail']}")
    for advisory in advisories:
        print(f"{'advisory':14} | {advisory['path']}")
        print(f"               | {advisory['kind']} — {advisory['detail']}")
    if advisories:
        print(
            "\nAdvisory: tests/ appears to hold an end-to-end expectation model. "
            "writing-tests.md forbids one; confirm by reading it, and if it maps inputs to "
            "the whole expected artifact move it to solution/ and seal its output."
        )
    if blocking:
        print(
            f"\n{blocking} blocking finding(s). An import or dynamic entry means the model can "
            "reach the implementation: re-derive the expected values from the authority, "
            "since an expectation taken from the reference cannot disagree with it. "
            "model_in_tests means the model ships with the verifier: move it to solution/."
        )
        return 1
    if not models:
        print("\nno --model given: only the tests/ auto-scan ran, independence was not checked")
        return 0
    print("\nOK: expected values are derived independently of the code under repair")
    return 0


if __name__ == "__main__":
    sys.exit(main())
