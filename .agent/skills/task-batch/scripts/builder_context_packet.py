#!/usr/bin/env python3
"""Create a small, hash-bound context receipt for one builder stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

STAGE_POLICY = {
    "candidate_gate": {
        "required": {"durable_memory", "pattern_catalog", "batch_portfolio"},
        "allowed": {"durable_memory", "pattern_catalog", "batch_portfolio", "prior_rejection", "miner_skill"},
        "max_bytes": 350_000,
    },
    "scaffold": {
        "required": {"mined_candidate", "source_smoke_receipt", "clone_skill"},
        "allowed": {"mined_candidate", "source_smoke_receipt", "clone_skill", "language_skill", "sanitizer_skill"},
        "max_bytes": 250_000,
    },
    "oracle_verifier": {
        "required": {"task_snapshot", "authoring_skill", "verifier_skill"},
        "allowed": {"task_snapshot", "authoring_skill", "verifier_skill", "source_smoke_receipt"},
        "max_bytes": 400_000,
    },
    "remediation": {
        "required": {"task_snapshot", "critique_receipt"},
        "allowed": {"task_snapshot", "critique_receipt", "reviewer_feedback", "auditor_feedback"},
        "max_bytes": 300_000,
    },
}


def parse_input(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("input must be KIND=PATH")
    kind, raw_path = value.split("=", 1)
    if not kind or not raw_path:
        raise argparse.ArgumentTypeError("input must be KIND=PATH")
    return kind, Path(raw_path)


def hash_path(path: Path) -> tuple[str, int, int]:
    if path.is_file():
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest(), len(data), 1
    if not path.is_dir():
        raise ValueError(f"missing input: {path}")
    digest = hashlib.sha256()
    total = 0
    count = 0
    for child in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.parts):
        relative = child.relative_to(path).as_posix().encode()
        data = child.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        total += len(data)
        count += 1
    return digest.hexdigest(), total, count


def build_receipt(stage: str, candidate: str, inputs: list[tuple[str, Path]]) -> dict[str, object]:
    policy = STAGE_POLICY[stage]
    kinds = [kind for kind, _ in inputs]
    duplicate = sorted({kind for kind in kinds if kinds.count(kind) > 1})
    if duplicate:
        raise ValueError(f"duplicate input kinds: {duplicate}")
    unknown = sorted(set(kinds) - policy["allowed"])
    missing = sorted(policy["required"] - set(kinds))
    if unknown:
        raise ValueError(f"inputs are not allowed for {stage}: {unknown}")
    if missing:
        raise ValueError(f"required inputs are missing for {stage}: {missing}")

    records = []
    total_bytes = 0
    for kind, path in inputs:
        resolved = path.resolve()
        sha256, size, file_count = hash_path(resolved)
        total_bytes += size
        records.append({
            "kind": kind,
            "path": str(resolved),
            "sha256": sha256,
            "bytes": size,
            "file_count": file_count,
        })
    if total_bytes > policy["max_bytes"]:
        raise ValueError(
            f"context packet is {total_bytes} bytes; {stage} limit is {policy['max_bytes']}"
        )
    return {
        "schema_version": 1,
        "candidate_slug": candidate,
        "stage": stage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_bytes": total_bytes,
        "max_bytes": policy["max_bytes"],
        "inputs": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_POLICY))
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--input", action="append", default=[], type=parse_input)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = build_receipt(args.stage, args.candidate, args.input)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "total_bytes": receipt["total_bytes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
