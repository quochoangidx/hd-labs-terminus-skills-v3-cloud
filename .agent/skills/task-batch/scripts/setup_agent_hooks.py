#!/usr/bin/env python3
"""Validate the repository-local Codex and Claude task-batch hook setup."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def root() -> Path:
    return Path(__file__).resolve().parents[4]


def validate_json(path: Path, *, require_session_start: bool = False) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        raise TypeError(f"{path}: hooks object is required")
    for event in ("SubagentStart", "PreToolUse", "SubagentStop", "Stop"):
        if not hooks.get(event):
            raise ValueError(f"{path}: missing {event}")
    if require_session_start and not hooks.get("SessionStart"):
        raise ValueError(f"{path}: missing SessionStart")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=("all", "codex", "claude"), default="all")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    repo = root()
    guard = repo / ".agent/skills/task-batch/scripts/builder_stage_guard.py"
    review_guard = repo / ".agent/skills/task-batch/scripts/review_role_guard.py"
    checked = []
    try:
        if args.agent in {"all", "codex"}:
            validate_json(repo / ".codex/hooks.json", require_session_start=True)
            config = (repo / ".codex/config.toml").read_text(encoding="utf-8")
            if "hooks = true" not in config:
                raise ValueError(".codex/config.toml must enable features.hooks")
            checked.append("codex")
        if args.agent in {"all", "claude"}:
            validate_json(repo / ".claude/settings.json")
            checked.append("claude")
        if args.self_test:
            event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "pwd"}})
            for runtime in checked:
                result = subprocess.run(
                    [sys.executable, str(guard), "hook", "--runtime", runtime],
                    input=event, text=True, capture_output=True, check=False,
                )
                if result.returncode != 0:
                    raise ValueError(f"{runtime} no-lease self-test failed: {result.stderr}")
            if "codex" in checked:
                with tempfile.TemporaryDirectory() as temporary:
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(review_guard),
                            "--state-dir",
                            temporary,
                            "hook",
                        ],
                        input=event,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    if result.returncode != 0:
                        raise ValueError(f"codex role no-lease self-test failed: {result.stderr}")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"hook setup invalid: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "pass",
        "agents": checked,
        "note": "Codex requires one-time review/trust through /hooks after hook changes.",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
