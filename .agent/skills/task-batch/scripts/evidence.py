#!/usr/bin/env python3
"""Create hash-bound receipts used by the task-batch handover gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_handover():
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "scripts" / "batch-handover.py"
    spec = importlib.util.spec_from_file_location("batch_handover", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def style_receipt(args: argparse.Namespace) -> int:
    """Bind a post-probe audit to the external submission prose only."""
    handover = load_handover()
    task_dir = args.task_dir.resolve()
    submission = args.submission.resolve()
    transcript = args.transcript.resolve()
    output = args.output.resolve()
    if not task_dir.is_dir():
        raise SystemExit(f"task folder not found: {task_dir}")
    for path, label in ((submission, "submission"), (transcript, "transcript")):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"{label} missing or empty: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    task_style = output.parent / "task-style-preflight.json"
    if not task_style.is_file():
        raise SystemExit(f"pre-freeze task style receipt is missing: {task_style}")
    try:
        transcript_rel = transcript.relative_to(output.parent)
    except ValueError as exc:
        raise SystemExit("transcript must be stored beside or below the report directory") from exc
    payload = {
        "schema_version": 2,
        "task_slug": task_dir.name,
        "status": "pass",
        "task_snapshot_sha256": handover.tree_hash(task_dir, sanitized=False),
        "task_style_preflight_sha256": handover.sha256(task_style),
        "submission_sha256": handover.sha256(submission),
        "auditor": {
            "status": "pass",
            "runtime": args.runtime,
            "model": args.model,
            "session_id": args.session_id,
            "transcript": transcript_rel.as_posix(),
            "transcript_sha256": handover.sha256(transcript),
        },
        "submission_surface": {
            "path": str(submission),
            "sha256": handover.sha256(submission),
            "status": "verified",
        },
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE: {output} (submission-only audit, task audit reused by hash)")
    return 0


def task_style_receipt(args: argparse.Namespace) -> int:
    """Bind a real pre-freeze audit to every task-visible prose surface."""
    handover = load_handover()
    task_dir = args.task_dir.resolve()
    transcript = args.transcript.resolve()
    output = args.output.resolve()
    if not task_dir.is_dir():
        raise SystemExit(f"task folder not found: {task_dir}")
    if not transcript.is_file() or transcript.stat().st_size == 0:
        raise SystemExit(f"transcript missing or empty: {transcript}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        transcript_rel = transcript.relative_to(output.parent)
    except ValueError as exc:
        raise SystemExit("transcript must be stored beside or below the report directory") from exc
    surfaces = [
        {"path": path, "sha256": digest, "status": "verified"}
        for path, digest in sorted(handover.style_surface_hashes(task_dir).items())
    ]
    payload = {
        "schema_version": 1,
        "task_slug": task_dir.name,
        "status": "pass",
        "task_snapshot_sha256": handover.tree_hash(task_dir, sanitized=False),
        "auditor": {
            "status": "pass",
            "runtime": args.runtime,
            "model": args.model,
            "session_id": args.session_id,
            "transcript": transcript_rel.as_posix(),
            "transcript_sha256": handover.sha256(transcript),
        },
        "surfaces": surfaces,
        "deleted_as_leak": [],
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE: {output} ({len(surfaces)} pre-freeze surfaces)")
    return 0


def hash_task(args: argparse.Namespace) -> int:
    handover = load_handover()
    print(handover.tree_hash(args.task_dir.resolve(), sanitized=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    hash_parser = sub.add_parser("hash-task")
    hash_parser.add_argument("task_dir", type=Path)
    hash_parser.set_defaults(func=hash_task)

    style_parser = sub.add_parser("style-receipt")
    style_parser.add_argument("task_dir", type=Path)
    style_parser.add_argument("--submission", type=Path, required=True)
    style_parser.add_argument("--transcript", type=Path, required=True)
    style_parser.add_argument("--runtime", required=True)
    style_parser.add_argument("--model", required=True)
    style_parser.add_argument("--session-id", required=True)
    style_parser.add_argument("--output", type=Path, required=True)
    style_parser.set_defaults(func=style_receipt)

    task_style_parser = sub.add_parser("task-style-receipt")
    task_style_parser.add_argument("task_dir", type=Path)
    task_style_parser.add_argument("--transcript", type=Path, required=True)
    task_style_parser.add_argument("--runtime", required=True)
    task_style_parser.add_argument("--model", required=True)
    task_style_parser.add_argument("--session-id", required=True)
    task_style_parser.add_argument("--output", type=Path, required=True)
    task_style_parser.set_defaults(func=task_style_receipt)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
