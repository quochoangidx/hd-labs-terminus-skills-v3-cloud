#!/usr/bin/env python3
"""Builder lease state machine and Claude/Codex lifecycle-hook adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
STAGES = {"candidate_gate", "scaffold", "oracle_verifier", "remediation"}
DEFAULT_MINUTES = {
    "candidate_gate": 25,
    "scaffold": 30,
    "oracle_verifier": 40,
    "remediation": 25,
}
MUTATING_TOOLS = {"apply_patch", "Edit", "Write", "MultiEdit", "NotebookEdit"}
MUTATING_SHELL = re.compile(
    r"(?:^|[;&|]\s*)(?:cp|mv|mkdir|touch|install|rm|rmdir|tee|truncate|patch)\b"
    r"|\bsed\s+(?:-[A-Za-z]*i|--in-place)\b|(?:^|[^<])>{1,2}(?!>)"
)
TASK_SLUG = re.compile(r"\btbrain-[a-z0-9][a-z0-9-]*\b")
PROTECTED = (
    ".agent/skills/task-batch/scripts/builder_stage_guard.py",
    ".codex/hooks.json",
    ".codex/config.toml",
    ".claude/settings.json",
    ".agent/runtime/task-batch-builder-lease.json",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat()


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".agent").is_dir():
            return candidate
    raise ValueError("cannot locate repository root")


def default_state() -> Path:
    override = os.environ.get("TERMINUS_BUILDER_LEASE")
    return Path(override).expanduser().resolve() if override else repo_root() / ".agent/runtime/task-batch-builder-lease.json"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return data


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    receipt_value = state.get("receipt_path")
    if receipt_value:
        receipt = Path(str(receipt_value))
        if receipt.resolve() != path.resolve():
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt_tmp = receipt.with_suffix(receipt.suffix + ".tmp")
            receipt_tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            receipt_tmp.replace(receipt)


def hash_path(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    files = (item for item in path.rglob("*") if item.is_file())
    for child in sorted(files, key=lambda item: item.parts):
        relative = child.relative_to(path).as_posix().encode()
        data = child.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def validate_context_receipt(path: Path, candidate: str, stage: str) -> None:
    receipt = read_json(path)
    if receipt.get("schema_version") != 1:
        raise ValueError("context receipt schema_version must equal 1")
    if receipt.get("candidate_slug") != candidate or receipt.get("stage") != stage:
        raise ValueError("context receipt is bound to a different candidate or stage")
    for item in receipt.get("inputs", []):
        source = Path(str(item.get("path", "")))
        if not source.exists():
            raise ValueError(f"context input disappeared: {source}")
        if item.get("sha256") != hash_path(source):
            raise ValueError(f"context input changed after packet creation: {source}")


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


def validate_smoke_receipt(path: Path, candidate: str) -> None:
    receipt = read_json(path)
    if receipt.get("schema_version") != 1 or receipt.get("status") != "pass":
        raise ValueError("canonical source-smoke receipt must pass")
    if receipt.get("candidate_slug") != candidate:
        raise ValueError("source-smoke receipt belongs to another candidate")
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", str(receipt.get("image", ""))):
        raise ValueError("source-smoke receipt is not digest-pinned")
    source_dir = Path(str(receipt.get("source_dir", "")))
    if not source_dir.is_dir() or receipt.get("source_tree_sha256") != hash_tree(source_dir):
        raise ValueError("source tree changed after canonical source smoke")


def owner_matches(state: dict[str, Any], event: dict[str, Any]) -> bool:
    owner = state.get("owner", {})
    if owner.get("agent_id"):
        return event.get("agent_id") == owner["agent_id"]
    return False


def event_turn_id(event: dict[str, Any]) -> str | None:
    value = event.get("turn_id") or event.get("prompt_id")
    return str(value) if value else None


def bind_subagent(state: dict[str, Any], event: dict[str, Any], runtime: str) -> str | None:
    if state.get("runtime") != runtime or state.get("status") != "active":
        return None
    agent_type = str(event.get("agent_type", ""))
    pattern = str(state.get("agent_type_pattern", ""))
    if not agent_type or not pattern or re.search(pattern, agent_type) is None:
        return None
    owner = state.setdefault("owner", {})
    if owner.get("agent_id") and owner["agent_id"] != event.get("agent_id"):
        return None
    owner.update({
        "session_id": event.get("session_id"),
        "agent_id": event.get("agent_id"),
        "agent_type": agent_type,
    })
    state["bound_at"] = iso(utcnow())
    return (
        f"Terminus builder lease active for {state['candidate_slug']} stage "
        f"{state['stage']}; do not roll into another candidate or stage."
    )


def is_mutating(event: dict[str, Any]) -> bool:
    tool = str(event.get("tool_name", ""))
    if tool in MUTATING_TOOLS:
        return True
    if tool == "Bash":
        command = str((event.get("tool_input") or {}).get("command", ""))
        return bool(MUTATING_SHELL.search(command))
    return tool.startswith("mcp__") and any(
        token in tool.lower() for token in ("write", "create", "update", "delete", "move", "edit")
    )


def event_text(event: dict[str, Any]) -> str:
    value = event.get("tool_input", {})
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def violation(state: dict[str, Any], event: dict[str, Any]) -> str | None:
    if not is_mutating(event):
        return None
    now = utcnow()
    try:
        deadline = datetime.fromisoformat(str(state["deadline_at"]))
    except (KeyError, ValueError):
        return "builder lease has no valid deadline"
    if now > deadline:
        return "builder stage deadline expired; stop this turn and let the orchestrator close it"
    turn = event_turn_id(event)
    bound_turn = state.get("bound_turn_id")
    if bound_turn and turn and bound_turn != turn:
        return "this lease is bound to the previous model turn; transition the stage before continuing"
    if not bound_turn and turn:
        state["bound_turn_id"] = turn

    text = event_text(event)
    normalized = text.replace("\\", "/")
    if any(path in normalized for path in PROTECTED):
        return "the builder may not modify its own lifecycle hooks or active lease"
    slugs = set(TASK_SLUG.findall(text))
    foreign = sorted(slugs - {str(state.get("candidate_slug"))})
    if foreign:
        return f"one builder turn may mutate only {state.get('candidate_slug')}; found {foreign}"

    stage = state.get("stage")
    if stage == "candidate_gate" and "workspace/tasks/" in normalized:
        return "Stage A cannot scaffold under workspace/tasks; pass canonical source smoke and start Stage B"
    if stage == "candidate_gate" and "docker" in normalized.lower() and "canonical_source_smoke.py" not in normalized:
        return "Stage A Docker builds must run through canonical_source_smoke.py"
    if stage in {"scaffold", "oracle_verifier", "remediation"}:
        receipt = state.get("source_smoke_receipt")
        if not receipt:
            return "scaffolding is locked until the canonical source smoke passes"
        try:
            validate_smoke_receipt(Path(receipt), str(state.get("candidate_slug")))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return f"source-smoke gate is stale or invalid: {exc}"
    return None


def hook(runtime: str, state_path: Path) -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("invalid hook JSON", file=sys.stderr)
        return 2
    if not state_path.is_file():
        return 0
    try:
        state = read_json(state_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"invalid builder lease: {exc}", file=sys.stderr)
        return 2
    event_name = event.get("hook_event_name")
    if event_name == "SubagentStart":
        message = bind_subagent(state, event, runtime)
        if message:
            write_state(state_path, state)
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": message}}))
        return 0
    if not owner_matches(state, event):
        return 0
    if event_name == "PreToolUse":
        reason = violation(state, event)
        write_state(state_path, state)
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}))
            return 2
        return 0
    if event_name in {"Stop", "SubagentStop"}:
        state.setdefault("stop_events", []).append({"event": event_name, "at": iso(utcnow())})
        write_state(state_path, state)
        print(json.dumps({"systemMessage": (
            f"Builder lease for {state['candidate_slug']} remains {state['status']} at "
            f"stage {state['stage']}; the orchestrator must transition, complete, or reject it."
        )}))
    return 0


def start(args: argparse.Namespace) -> int:
    path = args.state
    if path.exists():
        old = read_json(path)
        if old.get("status") == "active":
            raise ValueError(f"an active builder lease already exists for {old.get('candidate_slug')}")
    validate_context_receipt(args.context_receipt.resolve(), args.candidate, args.stage)
    now = utcnow()
    minutes = args.deadline_minutes or DEFAULT_MINUTES[args.stage]
    state = {
        "schema_version": SCHEMA_VERSION,
        "status": "active",
        "runtime": args.runtime,
        "batch_id": args.batch_id,
        "candidate_slug": args.candidate,
        "stage": args.stage,
        "agent_type_pattern": args.agent_type_pattern,
        "owner": {},
        "bound_turn_id": None,
        "started_at": iso(now),
        "deadline_at": iso(now + timedelta(minutes=minutes)),
        "infrastructure_repairs": 0,
        "context_receipt": str(args.context_receipt.resolve()),
        "source_smoke_receipt": None,
        "receipt_path": str(args.context_receipt.resolve().parent / "builder-stage-receipt.json"),
        "history": [],
    }
    write_state(path, state)
    print(json.dumps(state, indent=2))
    return 0


def transition(args: argparse.Namespace) -> int:
    state = read_json(args.state)
    if state.get("status") != "active":
        raise ValueError("builder lease is not active")
    if args.stage == "candidate_gate":
        raise ValueError("cannot transition backward to candidate_gate")
    validate_context_receipt(args.context_receipt.resolve(), state["candidate_slug"], args.stage)
    if args.source_smoke_receipt:
        validate_smoke_receipt(args.source_smoke_receipt.resolve(), state["candidate_slug"])
        state["source_smoke_receipt"] = str(args.source_smoke_receipt.resolve())
    if not state.get("source_smoke_receipt"):
        raise ValueError("a passing source-smoke receipt is required before Stage B")
    state.setdefault("history", []).append({
        "stage": state["stage"], "started_at": state["started_at"], "ended_at": iso(utcnow()),
        "turn_id": state.get("bound_turn_id"),
    })
    now = utcnow()
    state.update({
        "stage": args.stage,
        "bound_turn_id": None,
        "started_at": iso(now),
        "deadline_at": iso(now + timedelta(minutes=args.deadline_minutes or DEFAULT_MINUTES[args.stage])),
        "context_receipt": str(args.context_receipt.resolve()),
    })
    write_state(args.state, state)
    print(json.dumps(state, indent=2))
    return 0


def mutate_state(args: argparse.Namespace) -> int:
    state = read_json(args.state)
    if args.command == "repair":
        state["infrastructure_repairs"] = int(state.get("infrastructure_repairs", 0)) + 1
    elif args.command == "close":
        state.setdefault("history", []).append({
            "stage": state["stage"],
            "started_at": state["started_at"],
            "ended_at": iso(utcnow()),
            "turn_id": state.get("bound_turn_id"),
        })
        state["status"] = args.outcome
        state["outcome_reason"] = args.reason
        state["closed_at"] = iso(utcnow())
    write_state(args.state, state)
    print(json.dumps(state, indent=2))
    return 0 if state.get("status") != "rejected" else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("--state", type=Path, default=None)
    commands = root.add_subparsers(dest="command", required=True)
    open_parser = commands.add_parser("start")
    open_parser.add_argument("--runtime", required=True, choices=("codex", "claude"))
    open_parser.add_argument("--batch-id", required=True)
    open_parser.add_argument("--candidate", required=True)
    open_parser.add_argument("--stage", default="candidate_gate", choices=sorted(STAGES))
    open_parser.add_argument("--agent-type-pattern", required=True)
    open_parser.add_argument("--context-receipt", required=True, type=Path)
    open_parser.add_argument("--deadline-minutes", type=int)
    next_parser = commands.add_parser("transition")
    next_parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    next_parser.add_argument("--context-receipt", required=True, type=Path)
    next_parser.add_argument("--source-smoke-receipt", type=Path)
    next_parser.add_argument("--deadline-minutes", type=int)
    commands.add_parser("repair")
    close_parser = commands.add_parser("close")
    close_parser.add_argument("--outcome", required=True, choices=("complete", "rejected"))
    close_parser.add_argument("--reason", required=True)
    check_parser = commands.add_parser("check")
    check_parser.add_argument("--require-stage", choices=sorted(STAGES))
    hook_parser = commands.add_parser("hook")
    hook_parser.add_argument("--runtime", required=True, choices=("codex", "claude"))
    return root


def main() -> int:
    args = parser().parse_args()
    args.state = (args.state or default_state()).resolve()
    try:
        if args.command == "hook":
            return hook(args.runtime, args.state)
        if args.command == "start":
            return start(args)
        if args.command == "transition":
            return transition(args)
        if args.command in {"repair", "close"}:
            return mutate_state(args)
        state = read_json(args.state)
        if args.require_stage and state.get("stage") != args.require_stage:
            raise ValueError(f"expected stage {args.require_stage}, found {state.get('stage')}")
        print(json.dumps(state, indent=2))
        return 0 if state.get("status") == "active" else 1
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"builder-stage-guard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
