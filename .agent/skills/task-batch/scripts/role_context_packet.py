#!/usr/bin/env python3
"""Create hash-bound, role-specific context packets for review tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

POLICIES = {
    ("fairness_reviewer", "contract_review"): {
        "required": {"instruction", "task_visible_tree"},
        "allowed": {"instruction", "task_visible_tree", "evidence_manifest"},
        "max_bytes": 8_000_000,
        "max_files": 2_000,
    },
    ("fairness_reviewer", "final_review"): {
        "required": {"instruction", "task_visible_tree", "evidence_manifest"},
        "allowed": {"instruction", "task_visible_tree", "evidence_manifest", "remediation_summary"},
        "max_bytes": 8_000_000,
        "max_files": 2_000,
    },
    ("consolidated_auditor", "pre_freeze"): {
        "required": {"task_folder", "mechanical_receipts"},
        "allowed": {"task_folder", "mechanical_receipts", "semantic_manifest", "style_receipt"},
        "max_bytes": 15_000_000,
        "max_files": 4_000,
    },
    ("consolidated_auditor", "re_audit"): {
        "required": {"task_folder", "mechanical_receipts", "remediation_summary"},
        "allowed": {"task_folder", "mechanical_receipts", "semantic_manifest", "style_receipt", "remediation_summary"},
        "max_bytes": 15_000_000,
        "max_files": 4_000,
    },
    ("consolidated_auditor", "post_probe"): {
        "required": {"task_folder", "probe_report", "submission_packet"},
        "allowed": {"task_folder", "probe_report", "submission_packet", "final_zip_receipt"},
        "max_bytes": 15_000_000,
        "max_files": 4_000,
    },
}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
FAIRNESS_FORBIDDEN_PARTS = {"solution", "tests"}
COMMON_FORBIDDEN_NAMES = ("AGENTS.md", "builder-stage", "builder-critique", "prior-rejection")


def parse_input(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("input must be KIND=PATH")
    kind, raw = value.split("=", 1)
    if not kind or not raw:
        raise argparse.ArgumentTypeError("input must be KIND=PATH")
    return kind, Path(raw)


def hash_path(path: Path, *, fairness: bool) -> tuple[str, int, int]:
    if path.is_file():
        if any(token in path.name for token in COMMON_FORBIDDEN_NAMES):
            raise ValueError(f"role packet leaks campaign/builder context: {path}")
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest(), len(data), 1
    if not path.is_dir():
        raise ValueError(f"missing packet input: {path}")
    digest = hashlib.sha256()
    total = 0
    count = 0
    for child in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.parts):
        relative = child.relative_to(path)
        if SKIP_PARTS.intersection(relative.parts):
            continue
        if any(token in relative.as_posix() for token in COMMON_FORBIDDEN_NAMES):
            raise ValueError(f"role packet leaks campaign/builder context: {child}")
        if fairness and FAIRNESS_FORBIDDEN_PARTS.intersection(relative.parts):
            raise ValueError(f"fairness packet leaks verifier/oracle path: {child}")
        relative_bytes = relative.as_posix().encode()
        data = child.read_bytes()
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        total += len(data)
        count += 1
    return digest.hexdigest(), total, count


def build_packet(
    role: str, phase: str, task_slug: str, inputs: list[tuple[str, Path]]
) -> dict[str, object]:
    policy = POLICIES[(role, phase)]
    kinds = [kind for kind, _ in inputs]
    if len(kinds) != len(set(kinds)):
        raise ValueError("packet input kinds must be unique")
    missing = sorted(policy["required"] - set(kinds))
    unknown = sorted(set(kinds) - policy["allowed"])
    if missing:
        raise ValueError(f"required inputs are missing: {missing}")
    if unknown:
        raise ValueError(f"inputs are not allowed for {role}/{phase}: {unknown}")
    records = []
    total_bytes = 0
    total_files = 0
    fairness = role == "fairness_reviewer"
    for kind, raw_path in inputs:
        path = raw_path.resolve()
        if fairness and path.name in FAIRNESS_FORBIDDEN_PARTS:
            raise ValueError(f"fairness packet cannot include {path.name}")
        sha256, size, files = hash_path(path, fairness=fairness)
        total_bytes += size
        total_files += files
        records.append({
            "kind": kind,
            "path": str(path),
            "sha256": sha256,
            "bytes": size,
            "file_count": files,
        })
    if total_bytes > policy["max_bytes"] or total_files > policy["max_files"]:
        raise ValueError(
            f"packet exceeds {role}/{phase} budget: {total_bytes} bytes, {total_files} files"
        )
    return {
        "schema_version": 1,
        "role": role,
        "phase": phase,
        "task_slug": task_slug,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_bytes": total_bytes,
        "total_files": total_files,
        "max_bytes": policy["max_bytes"],
        "max_files": policy["max_files"],
        "inputs": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=("fairness_reviewer", "consolidated_auditor"))
    parser.add_argument("--phase", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--input", action="append", default=[], type=parse_input)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if (args.role, args.phase) not in POLICIES:
        parser.error(f"invalid phase {args.phase} for {args.role}")
    try:
        packet = build_packet(args.role, args.phase, args.task, args.input)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "bytes": packet["total_bytes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
