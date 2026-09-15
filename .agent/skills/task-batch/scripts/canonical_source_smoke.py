#!/usr/bin/env python3
"""Run one exact source-build smoke in a digest-pinned canonical image."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIGEST_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    files = (
        item
        for item in path.rglob("*")
        if item.is_file() and ".git" not in item.relative_to(path).parts
    )
    for child in sorted(files, key=lambda item: item.parts):
        relative = child.relative_to(path).as_posix().encode()
        data = child.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def load_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("plan schema_version must equal 1")
    if not re.fullmatch(r"tbrain-[a-z0-9][a-z0-9-]*", str(data.get("candidate_slug", ""))):
        raise ValueError("candidate_slug must be a canonical tbrain slug")
    if not isinstance(data.get("source_revision"), str) or not data["source_revision"].strip():
        raise ValueError("source_revision is required")
    if not DIGEST_IMAGE.fullmatch(str(data.get("image", ""))):
        raise ValueError("image must be pinned by a full sha256 digest")
    command = data.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise ValueError("command must be a non-empty string array")
    timeout = data.get("timeout_seconds", 900)
    if not isinstance(timeout, int) or not 1 <= timeout <= 1800:
        raise ValueError("timeout_seconds must be between 1 and 1800")
    source = Path(str(data.get("source_dir", ""))).resolve()
    if not source.is_dir():
        raise ValueError(f"source_dir is missing: {source}")
    data["source_dir"] = str(source)
    return data


def execute(plan: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str] | None, bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="terminus-source-smoke-") as temporary:
        staged = Path(temporary) / "source"
        shutil.copytree(
            plan["source_dir"],
            staged,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".ruff_cache"),
        )
        docker_command = [
            "docker", "run", "--rm", "--network", "none",
            "--mount", f"type=bind,src={staged},dst=/src",
            "--workdir", "/src", str(plan["image"]), *plan["command"],
        ]
        try:
            result = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                timeout=plan.get("timeout_seconds", 900),
                check=False,
            )
            return result, False, docker_command
        except subprocess.TimeoutExpired as exc:
            result = subprocess.CompletedProcess(
                docker_command,
                124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "source smoke timed out",
            )
            return result, True, docker_command


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        plan = load_plan(args.plan)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    result, timed_out, docker_command = execute(plan)
    assert result is not None
    stdout = result.stdout if isinstance(result.stdout, str) else result.stdout.decode(errors="replace")
    stderr = result.stderr if isinstance(result.stderr, str) else result.stderr.decode(errors="replace")
    receipt = {
        "schema_version": 1,
        "candidate_slug": plan.get("candidate_slug"),
        "status": "pass" if result.returncode == 0 and not timed_out else "fail",
        "image": plan["image"],
        "source_dir": plan["source_dir"],
        "source_tree_sha256": hash_tree(Path(plan["source_dir"])),
        "source_revision": plan.get("source_revision"),
        "command": plan["command"],
        "docker_command": docker_command,
        "timeout_seconds": plan.get("timeout_seconds", 900),
        "timed_out": timed_out,
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "output": str(args.output), "exit_code": result.returncode}))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
