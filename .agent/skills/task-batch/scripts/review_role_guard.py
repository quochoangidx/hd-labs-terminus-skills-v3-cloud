#!/usr/bin/env python3
"""Lifecycle lease guard for reviewer and auditor tasks."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MODEL = "gpt-5.6-sol"
ROLE_POLICY = {
    "fairness_reviewer": {"effort": "medium", "minutes": 12, "tool_limit": 12, "count": 1},
    "consolidated_auditor": {"effort": "medium", "minutes": 18, "tool_limit": 20, "count": 1},
}
PHASES = {
    "fairness_reviewer": {"contract_review", "final_review"},
    "consolidated_auditor": {"pre_freeze", "re_audit", "post_probe"},
}
MUTATING_TOOLS = {"apply_patch", "Edit", "Write", "MultiEdit", "NotebookEdit"}
MUTATING_SHELL = re.compile(
    r"(?:^|[;&|]\s*)(?:cp|mv|mkdir|touch|install|rm|rmdir|tee|truncate|patch)\b"
    r"|\bsed\s+(?:-[A-Za-z]*i|--in-place)\b|(?:^|[^<])>{1,2}(?!>)"
)
FORBIDDEN_COMMON = ("AGENTS.md", "builder-stage-receipt", "builder-critique", "prior-rejection")
FORBIDDEN_FAIRNESS = ("solution/", "tests/", "\\solution\\", "\\tests\\")


def now() -> datetime:
    return datetime.now(timezone.utc)


def state_root() -> Path:
    override = os.environ.get("TERMINUS_ROLE_LEASE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".agent").is_dir():
            return candidate / ".agent/runtime/task-batch-role-leases"
    raise ValueError("cannot locate repository root")


@contextmanager
def locked(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("lease root must be an object")
    return data


def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    receipt = Path(str(data["receipt_path"]))
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt_tmp = receipt.with_suffix(".tmp")
    receipt_tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    receipt_tmp.replace(receipt)


def hash_path(path: Path, fairness: bool) -> str:
    if path.is_file():
        if any(token in path.name for token in FORBIDDEN_COMMON):
            raise ValueError(f"role packet leaked campaign/builder context: {path}")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    skip = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
    for child in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.parts):
        relative = child.relative_to(path)
        if skip.intersection(relative.parts):
            continue
        if any(token in relative.as_posix() for token in FORBIDDEN_COMMON):
            raise ValueError(f"role packet leaked campaign/builder context: {child}")
        if fairness and {"solution", "tests"}.intersection(relative.parts):
            raise ValueError(f"fairness packet leaked {child}")
        name = relative.as_posix().encode()
        content = child.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def validate_packet(path: Path, role: str, phase: str, task: str) -> dict[str, Any]:
    packet = load(path)
    if packet.get("schema_version") != 1:
        raise ValueError("role packet schema_version must equal 1")
    expected = (role, phase, task, MODEL, ROLE_POLICY[role]["effort"])
    actual = (
        packet.get("role"), packet.get("phase"), packet.get("task_slug"),
        packet.get("model"), packet.get("reasoning_effort"),
    )
    if actual != expected:
        raise ValueError("role packet routing or snapshot binding is invalid")
    for item in packet.get("inputs", []):
        source = Path(str(item.get("path", "")))
        if not source.exists() or item.get("sha256") != hash_path(
            source, role == "fairness_reviewer"
        ):
            raise ValueError(f"role packet input is stale: {source}")
    return packet


def paths(root: Path) -> list[Path]:
    return sorted(root.glob("*.json"))


def claim(root: Path, event: dict[str, Any]) -> tuple[Path, dict[str, Any]] | None:
    if event.get("model") != MODEL:
        return None
    with locked(root):
        for path in paths(root):
            lease = load(path)
            if lease.get("status") != "awaiting_session":
                continue
            lease["status"] = "active"
            lease["owner"] = {"session_id": event.get("session_id")}
            lease["claimed_at"] = now().isoformat()
            save(path, lease)
            return path, lease
    return None


def owned(root: Path, session_id: object) -> tuple[Path, dict[str, Any]] | None:
    for path in paths(root):
        lease = load(path)
        if lease.get("owner", {}).get("session_id") == session_id and lease.get("status") == "active":
            return path, lease
    return None


def mutating(event: dict[str, Any]) -> bool:
    tool = str(event.get("tool_name", ""))
    if tool in MUTATING_TOOLS:
        return True
    if tool == "Bash":
        return bool(MUTATING_SHELL.search(str((event.get("tool_input") or {}).get("command", ""))))
    return tool.startswith("mcp__") and any(
        token in tool.lower() for token in ("write", "create", "update", "delete", "move", "edit")
    )


def pretool(path: Path, lease: dict[str, Any], event: dict[str, Any]) -> str | None:
    if now() > datetime.fromisoformat(lease["deadline_at"]):
        lease["status"] = "expired"
        save(path, lease)
        return "role deadline expired; the orchestrator must stop this Codex task"
    if mutating(event):
        return f"{lease['role']} is review-only and cannot mutate repository or external state"
    text = json.dumps(event.get("tool_input", {}), sort_keys=True)
    forbidden = FORBIDDEN_COMMON + (FORBIDDEN_FAIRNESS if lease["role"] == "fairness_reviewer" else ())
    if any(token in text for token in forbidden):
        return "tool input requests context forbidden for this independent review role"
    lease["tool_calls"] = int(lease.get("tool_calls", 0)) + 1
    if lease["tool_calls"] > lease["tool_limit"]:
        save(path, lease)
        return f"{lease['role']} exceeded its {lease['tool_limit']}-tool phase budget"
    turn = str(event.get("turn_id") or "")
    if lease.get("bound_turn_id") and turn and lease["bound_turn_id"] != turn:
        return "a new role turn requires an explicit lease transition"
    if turn and not lease.get("bound_turn_id"):
        lease["bound_turn_id"] = turn
    save(path, lease)
    return None


def hook(root: Path) -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("invalid role-hook JSON", file=sys.stderr)
        return 2
    event_name = event.get("hook_event_name")
    if event_name == "SessionStart":
        result = claim(root, event)
        if result:
            _, lease = result
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"Quota lease active: {lease['role']} {lease['phase']} for {lease['task_slug']}; "
                    f"deadline {lease['deadline_at']}, tool cap {lease['tool_limit']}."
                ),
            }}))
        return 0
    result = owned(root, event.get("session_id"))
    if not result:
        return 0
    path, lease = result
    if event_name == "PreToolUse":
        reason = pretool(path, lease, event)
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}))
            return 2
    elif event_name == "Stop":
        try:
            validate_packet(Path(lease["packet_path"]), lease["role"], lease["phase"], lease["task_slug"])
            lease["status"] = "complete" if lease["phase"] in {"final_review", "post_probe"} else "phase_complete"
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            lease["status"] = "invalid_snapshot"
            lease["snapshot_error"] = str(exc)
        lease["ended_at"] = now().isoformat()
        save(path, lease)
        print(json.dumps({"systemMessage": f"{lease['role']} lease ended with {lease['status']}."}))
    return 0


def open_leases(args: argparse.Namespace, root: Path) -> int:
    policy = ROLE_POLICY[args.role]
    expected_count = policy["count"]
    if args.count != expected_count:
        raise ValueError(f"{args.role} requires exactly {expected_count} lease(s)")
    validate_packet(args.packet.resolve(), args.role, args.phase, args.task)
    created = []
    with locked(root):
        existing = [load(path) for path in paths(root)]
        active = [
            lease
            for lease in existing
            if lease.get("status") in {"awaiting_session", "active"}
        ]
        if active:
            raise ValueError(
                "another unclaimed or active review cohort exists in this worktree; "
                "finish it or use a separate worktree and lease directory"
            )
        for slot in range(1, args.count + 1):
            lease_id = f"{args.task}-{args.role}-{slot}"
            path = root / f"{lease_id}.json"
            started = now()
            lease = {
                "schema_version": 1,
                "lease_id": lease_id,
                "task_slug": args.task,
                "role": args.role,
                "phase": args.phase,
                "model": MODEL,
                "reasoning_effort": policy["effort"],
                "status": "awaiting_session",
                "owner": {},
                "packet_path": str(args.packet.resolve()),
                "started_at": started.isoformat(),
                "deadline_at": (started + timedelta(minutes=args.deadline_minutes or policy["minutes"])).isoformat(),
                "tool_limit": policy["tool_limit"],
                "tool_calls": 0,
                "bound_turn_id": None,
                "remediation_cycles": 0,
                "receipt_path": str(args.packet.resolve().parent / "role-leases" / f"{lease_id}.json"),
                "history": [],
            }
            save(path, lease)
            created.append(str(path))
    print(json.dumps({"status": "pass", "leases": created}, indent=2))
    return 0


def transition(args: argparse.Namespace, root: Path) -> int:
    path = root / f"{args.lease}.json"
    lease = load(path)
    if lease.get("status") != "phase_complete":
        raise ValueError("lease must finish its current phase before transition")
    role = lease["role"]
    allowed = {
        ("fairness_reviewer", "contract_review"): {"final_review"},
        ("consolidated_auditor", "pre_freeze"): {"re_audit", "post_probe"},
        ("consolidated_auditor", "re_audit"): {"post_probe"},
    }.get((role, lease["phase"]), set())
    if args.phase not in allowed:
        raise ValueError(f"invalid transition {lease['phase']} -> {args.phase}")
    if args.phase in {"final_review", "re_audit"}:
        if lease.get("remediation_cycles", 0) >= 1:
            raise ValueError("role remediation cycle already consumed")
        lease["remediation_cycles"] = 1
    validate_packet(args.packet.resolve(), role, args.phase, lease["task_slug"])
    lease.setdefault("history", []).append({
        "phase": lease["phase"], "turn_id": lease.get("bound_turn_id"),
        "started_at": lease["started_at"], "ended_at": lease.get("ended_at"),
        "tool_calls": lease["tool_calls"],
    })
    started = now()
    lease.update({
        "phase": args.phase,
        "status": "active",
        "packet_path": str(args.packet.resolve()),
        "started_at": started.isoformat(),
        "deadline_at": (started + timedelta(minutes=args.deadline_minutes or ROLE_POLICY[role]["minutes"])).isoformat(),
        "tool_calls": 0,
        "bound_turn_id": None,
        "ended_at": None,
    })
    save(path, lease)
    print(json.dumps(lease, indent=2))
    return 0


def reconcile_completed(args: argparse.Namespace, root: Path) -> int:
    """Bind a completed Codex turn when project hooks failed to load.

    This is an explicit, auditable recovery path.  It does not claim that the
    hook enforced the tool-call cap; the receipt records that limitation.
    """
    path = root / f"{args.lease}.json"
    lease = load(path)
    if lease.get("status") not in {"awaiting_session", "active"}:
        raise ValueError("only an awaiting_session or active lease can be reconciled")
    existing_owner = lease.get("owner", {}).get("session_id")
    if existing_owner and existing_owner != args.session_id:
        raise ValueError("observed session does not own the active lease")
    if args.model != lease.get("model") or args.reasoning_effort != lease.get("reasoning_effort"):
        raise ValueError("observed model/reasoning routing does not match the lease")
    started = datetime.fromisoformat(args.started_at)
    ended = datetime.fromisoformat(args.ended_at)
    if started.tzinfo is None or ended.tzinfo is None or ended < started:
        raise ValueError("observed timestamps must be ordered and timezone-aware")
    if ended > datetime.fromisoformat(lease["deadline_at"]):
        raise ValueError("completed turn exceeded the lease deadline")
    evidence = args.evidence.resolve()
    if not evidence.is_file():
        raise ValueError("reconciliation evidence is missing")
    validate_packet(
        Path(lease["packet_path"]), lease["role"], lease["phase"], lease["task_slug"]
    )
    lease.update({
        "status": "phase_complete",
        "owner": {"session_id": args.session_id},
        "bound_turn_id": args.turn_id,
        "claimed_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "enforcement_mode": "orchestrator_reconciled_after_hook_load_failure",
        "hook_enforced": False,
        "tool_call_accounting": "unavailable; transcript and wall-clock reviewed by orchestrator",
        "reconciliation_evidence": {
            "path": str(evidence),
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        },
    })
    save(path, lease)
    print(json.dumps(lease, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    open_parser = commands.add_parser("open")
    open_parser.add_argument("--role", required=True, choices=sorted(ROLE_POLICY))
    open_parser.add_argument("--phase", required=True)
    open_parser.add_argument("--task", required=True)
    open_parser.add_argument("--packet", required=True, type=Path)
    open_parser.add_argument("--count", required=True, type=int)
    open_parser.add_argument("--deadline-minutes", type=int)
    transition_parser = commands.add_parser("transition")
    transition_parser.add_argument("--lease", required=True)
    transition_parser.add_argument("--phase", required=True)
    transition_parser.add_argument("--packet", required=True, type=Path)
    transition_parser.add_argument("--deadline-minutes", type=int)
    reconcile_parser = commands.add_parser("reconcile-completed")
    reconcile_parser.add_argument("--lease", required=True)
    reconcile_parser.add_argument("--session-id", required=True)
    reconcile_parser.add_argument("--turn-id", required=True)
    reconcile_parser.add_argument("--started-at", required=True)
    reconcile_parser.add_argument("--ended-at", required=True)
    reconcile_parser.add_argument("--model", required=True)
    reconcile_parser.add_argument("--reasoning-effort", required=True)
    reconcile_parser.add_argument("--evidence", required=True, type=Path)
    close_parser = commands.add_parser("close")
    close_parser.add_argument("--lease", required=True)
    commands.add_parser("check")
    commands.add_parser("hook")
    args = parser.parse_args()
    root = (args.state_dir or state_root()).resolve()
    try:
        if args.command == "hook":
            return hook(root)
        if args.command == "open":
            if args.phase not in PHASES[args.role]:
                raise ValueError(f"invalid phase {args.phase} for {args.role}")
            return open_leases(args, root)
        if args.command == "transition":
            return transition(args, root)
        if args.command == "reconcile-completed":
            return reconcile_completed(args, root)
        if args.command == "close":
            path = root / f"{args.lease}.json"
            lease = load(path)
            if lease.get("status") != "phase_complete":
                raise ValueError("only a completed phase can be closed")
            lease["status"] = "complete"
            save(path, lease)
            print(json.dumps(lease, indent=2))
            return 0
        expired = []
        for path in paths(root):
            lease = load(path)
            if lease.get("status") in {"awaiting_session", "active"} and now() > datetime.fromisoformat(lease["deadline_at"]):
                expired.append(lease["lease_id"])
                lease["status"] = "expired"
                lease["ended_at"] = now().isoformat()
                save(path, lease)
        print(json.dumps({"status": "fail" if expired else "pass", "expired": expired}))
        return 1 if expired else 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"review-role-guard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
