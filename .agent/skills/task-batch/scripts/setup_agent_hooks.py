#!/usr/bin/env python3
"""Validate the repository-local Codex and Claude task-batch hook setup."""

from __future__ import annotations

import argparse
import json
import os
import re
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


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def ensure_skill_links(repo: Path) -> None:
    target = Path("../.agent/skills")
    for relative in (Path(".agents/skills"), Path(".codex/skills"), Path(".claude/skills")):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            if Path(os.readlink(path)) != target:
                raise ValueError(f"{relative}: unexpected symlink target")
        elif path.exists():
            raise ValueError(f"{relative}: expected a symlink, found an existing path")
        else:
            path.symlink_to(target)


def trust_codex(repo: Path, path: Path | None = None) -> None:
    path = path or Path.home() / ".codex/config.toml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    quoted = json.dumps(str(repo))
    header = f"[projects.{quoted}]"
    pattern = re.compile(
        rf"(?ms)^(?P<header>{re.escape(header)})\n(?P<body>.*?)(?=^\[|\Z)"
    )
    match = pattern.search(text)
    if match:
        body = match.group("body")
        if re.search(r"(?m)^trust_level\s*=", body):
            body = re.sub(
                r'(?m)^trust_level\s*=.*$', 'trust_level = "trusted"', body
            )
        else:
            body = 'trust_level = "trusted"\n' + body
        text = text[: match.start()] + header + "\n" + body + text[match.end() :]
    else:
        text = text.rstrip() + f"\n\n{header}\ntrust_level = \"trusted\"\n"
    atomic_write(path, text)


def trust_claude(repo: Path, path: Path | None = None) -> None:
    path = path or Path.home() / ".claude.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict):
        raise TypeError(f"{path}: root must be an object")
    projects = data.setdefault("projects", {})
    if not isinstance(projects, dict):
        raise TypeError(f"{path}: projects must be an object")
    project = projects.setdefault(str(repo), {})
    if not isinstance(project, dict):
        raise TypeError(f"{path}: project entry must be an object")
    project["hasTrustDialogAccepted"] = True
    project.setdefault("projectOnboardingSeenCount", 0)
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=("all", "codex", "claude"), default="all")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--trust", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    repo = root()
    guard = repo / ".agent/skills/task-batch/scripts/builder_stage_guard.py"
    review_guard = repo / ".agent/skills/task-batch/scripts/review_role_guard.py"
    checked = []
    try:
        if args.install:
            ensure_skill_links(repo)
        if args.trust:
            if args.agent in {"all", "codex"}:
                trust_codex(repo)
            if args.agent in {"all", "claude"}:
                trust_claude(repo)
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
        "installed": args.install,
        "trusted": args.trust,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
