#!/usr/bin/env python3
"""Shared static checks for untrusted verifier execution and prompt symmetry."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


BUILD_OR_CANDIDATE_RE = re.compile(
    r"(?i)(?:\bmake\b|\bgo\b|\bcargo\b|\brustc\b|\bgcc\b|\bg\+\+\b|"
    r"\bclang\b|\bjavac\b|\bmvn\b|\bgradle\b|\bnpm\b|\bpnpm\b|\byarn\b|"
    r"/app(?:/|\b)|\bapp_dir\b|\bcandidate\b|\bbinary\b|\bbin_name\b)"
)
UNIT_TEST_PROMISE_RE = re.compile(
    r"(?is)(?:unit|existing|repository|pre-existing)[ -]tests?.{0,100}"
    r"(?:keep|remain|continue|still|must).{0,40}(?:pass|passing|green)"
    r"|(?:keep|preserve).{0,80}(?:unit|existing|repository|pre-existing)[ -]tests?"
)
UNIT_TEST_EXECUTION_RE = re.compile(
    r"(?i)(?:\bgo\s+test\b|[\"']go[\"']\s*,\s*[\"']test[\"']|"
    r"\bmake\s+test\b|[\"']make[\"']\s*,\s*[\"']test[\"'])"
)


@dataclass(frozen=True)
class UnsafeCandidateCall:
    line: int
    function: str
    expression: str


def _call_name(node: ast.Call) -> str:
    try:
        return ast.unparse(node.func)
    except Exception:
        return ""


def _node_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _is_process_call(node: ast.Call) -> bool:
    name = _call_name(node)
    return name in {
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "os.system",
        "os.popen",
    }


def _is_candidate_controlled(node: ast.Call, function_name: str) -> bool:
    rendered = _node_text(node)
    if re.search(r"(?i)(candidate|simulator|compile|build)", function_name):
        return True
    if BUILD_OR_CANDIDATE_RE.search(rendered):
        return True
    for keyword in node.keywords:
        if keyword.arg == "cwd" and BUILD_OR_CANDIDATE_RE.search(_node_text(keyword.value)):
            return True
    return False


def _is_demoted(node: ast.Call) -> bool:
    keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg}
    if {"user", "group"}.issubset(keyword_names):
        return True
    for keyword in node.keywords:
        if keyword.arg is None:
            value = _node_text(keyword.value)
            if re.search(r"(?i)(candidate.*user|user.*kwargs|unprivileged|demot)", value):
                return True
    rendered = _node_text(node)
    return bool(re.search(r"(?i)(?:setpriv|runuser|su-exec)", rendered))


class _CandidateCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_stack: list[str] = []
        self.unsafe: list[UnsafeCandidateCall] = []
        self.candidate_call_count = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        function_name = self.function_stack[-1] if self.function_stack else "<module>"
        if _is_process_call(node) and _is_candidate_controlled(node, function_name):
            self.candidate_call_count += 1
            if not _is_demoted(node):
                expression = " ".join(_node_text(node).split())[:240]
                self.unsafe.append(
                    UnsafeCandidateCall(
                        line=getattr(node, "lineno", 0),
                        function=function_name,
                        expression=expression,
                    )
                )
        self.generic_visit(node)


def analyze_candidate_privileges(source: str) -> tuple[int, list[UnsafeCandidateCall]]:
    """Return candidate-controlled subprocess count and calls lacking demotion."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, []
    visitor = _CandidateCallVisitor()
    visitor.visit(tree)
    return visitor.candidate_call_count, visitor.unsafe


def unit_test_alignment_issue(contract_text: str, verifier_source: str) -> bool:
    """Detect an explicit unit-test preservation promise with no matching run."""
    return bool(
        UNIT_TEST_PROMISE_RE.search(contract_text)
        and not UNIT_TEST_EXECUTION_RE.search(verifier_source)
    )


def _task_sources(task_dir: Path) -> tuple[str, str]:
    verifier = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted((task_dir / "tests").glob("*.py"))
    )
    contract_paths = [task_dir / "instruction.md"]
    contract_paths.extend(
        path
        for path in sorted((task_dir / "environment").rglob("*"))
        if path.is_file() and path.suffix.lower() in {".md", ".rst", ".txt"}
    )
    contract = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in contract_paths
        if path.is_file()
    )
    return verifier, contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--check", choices=("privilege", "alignment", "all"), default="all")
    args = parser.parse_args()

    verifier, contract = _task_sources(args.task_dir)
    candidate_count, unsafe = analyze_candidate_privileges(verifier)
    alignment_issue = unit_test_alignment_issue(contract, verifier)
    payload = {
        "candidate_execution_count": candidate_count,
        "unsafe_candidate_calls": [asdict(item) for item in unsafe],
        "unit_test_alignment_issue": alignment_issue,
    }
    print(json.dumps(payload, sort_keys=True))
    if args.check in {"privilege", "all"} and unsafe:
        return 1
    if args.check in {"alignment", "all"} and alignment_issue:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
