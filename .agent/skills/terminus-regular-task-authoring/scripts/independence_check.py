#!/usr/bin/env python3
"""Check that the verifier's expected values do not come from the code under repair.

The usual chain is circular: the reference defines the behaviour, the verifier records
what the reference does, and the reference then passes. Oracle=1 proves nothing under
that arrangement, which is why a reference reviewer normally has to read the patch.

A task that re-derives its expected answers from the visible authority breaks the
circle: Oracle=1 becomes two independent derivations of one authority agreeing. This
script checks the derivation really is independent, i.e. that the module holding the
expectations never imports, loads or executes the package being repaired.

Usage:
    independence_check.py <task-folder> --model tests/model.py [--model ...]
        [--package <name>] [--report-json <path>]

Exit 0 = independent. Exit 1 = the expectation model can reach the implementation.
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        help="task-relative path of a module holding expected values, repeatable",
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
    if not forbidden:
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
        blocking += len(hard)
        models.append(
            {
                "path": rel,
                "status": "independent" if not hard else "contaminated",
                "findings": findings,
            }
        )

    report = {
        "schema_version": 1,
        "check": "independence",
        "task_slug": task_dir.name,
        "task_snapshot_sha256": tree_hash(task_dir),
        "forbidden_names": sorted(forbidden),
        "models": models,
        "status": "pass" if blocking == 0 else "fail",
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for model in models:
        print(f"{model['status']:12} | {model['path']}")
        for finding in model["findings"]:
            print(f"             | line {finding['line']}: {finding['kind']} — {finding['detail']}")
    if blocking:
        print(
            f"\n{blocking} way(s) for the expectation model to reach the implementation. "
            "Re-derive the expected values from the authority instead; an expectation "
            "taken from the reference cannot disagree with it."
        )
        return 1
    print("\nOK: expected values are derived independently of the code under repair")
    return 0


if __name__ == "__main__":
    sys.exit(main())
