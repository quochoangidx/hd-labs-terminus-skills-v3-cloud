#!/usr/bin/env python3
"""Executable policy checks shared by task generators and validators."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


OPEN_CATEGORIES = {
    "games",
    "machine-learning",
    "system-administration",
}
VALID_LANGUAGES = {
    "bash",
    "c",
    "c++",
    "go",
    "java",
    "javascript",
    "node",
    "php",
    "python",
    "ruby",
    "rust",
    "typescript",
}
CANONICAL_REWARD_FOOTER = [
    "rc=$?",
    'if [ "$rc" -eq 0 ]; then',
    "    echo 1 > /logs/verifier/reward.txt",
    "else",
    "    echo 0 > /logs/verifier/reward.txt",
    "fi",
]


def result(check: str, ok: bool, detail: str) -> dict[str, object]:
    return {"check": check, "status": "pass" if ok else "fail", "detail": detail}


def validate_category(category: str) -> list[dict[str, object]]:
    return [
        result(
            "category:open",
            category in OPEN_CATEGORIES,
            (
                f"{category} is open for net-new submissions"
                if category in OPEN_CATEGORIES
                else f"{category!r} is not in the net-new allowlist: "
                + ", ".join(sorted(OPEN_CATEGORIES))
            ),
        )
    ]


def validate_task(task_dir: Path) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    task_toml = task_dir / "task.toml"
    test_sh = task_dir / "tests" / "test.sh"

    try:
        metadata = tomllib.loads(task_toml.read_text()).get("metadata", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        checks.append(result("task.toml:parse", False, str(exc)))
        metadata = {}
    else:
        checks.append(result("task.toml:parse", True, "valid TOML"))

    category = metadata.get("category")
    checks.extend(validate_category(category if isinstance(category, str) else ""))

    languages = metadata.get("languages")
    language_ok = (
        isinstance(languages, list)
        and bool(languages)
        and all(
            isinstance(language, str)
            and language == language.lower()
            and language in VALID_LANGUAGES
            for language in languages
        )
    )
    checks.append(
        result(
            "task.toml:languages",
            language_ok,
            (
                f"lowercase language slugs: {languages}"
                if language_ok
                else f"expected non-empty lowercase slugs, got {languages!r}"
            ),
        )
    )

    try:
        raw = test_sh.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        checks.append(result("test.sh:read", False, str(exc)))
        return checks

    checks.append(result("test.sh:read", True, "UTF-8"))
    checks.append(
        result(
            "test.sh:line-endings",
            b"\r\n" not in raw,
            "LF only" if b"\r\n" not in raw else "CRLF is not accepted",
        )
    )
    checks.append(
        result(
            "test.sh:mode",
            os.access(test_sh, os.X_OK),
            "executable" if os.access(test_sh, os.X_OK) else "missing executable bit",
        )
    )
    syntax = subprocess.run(
        ["bash", "-n", str(test_sh)],
        capture_output=True,
        text=True,
        check=False,
    )
    checks.append(
        result(
            "test.sh:bash-n",
            syntax.returncode == 0,
            "valid shell syntax" if syntax.returncode == 0 else syntax.stderr.strip(),
        )
    )
    checks.append(
        result(
            "test.sh:pipefail",
            "set -uo pipefail" in text and "set -e" not in text,
            "uses set -uo pipefail without -e",
        )
    )
    checks.append(
        result(
            "test.sh:python3",
            "python3" in text and "\npython " not in text,
            "uses python3, not bare python",
        )
    )

    nonempty_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    try:
        mkdir_index = nonempty_lines.index("mkdir -p /logs/verifier")
    except ValueError:
        default_reward_ok = False
    else:
        default_reward_ok = (
            len(nonempty_lines) > mkdir_index + 1
            and nonempty_lines[mkdir_index + 1] == "echo 0 > /logs/verifier/reward.txt"
        )
    checks.append(
        result(
            "test.sh:default-reward",
            default_reward_ok,
            (
                "default reward is initialized before risky verifier work"
                if default_reward_ok
                else "echo 0 must immediately follow mkdir -p /logs/verifier"
            ),
        )
    )
    footer_ok = nonempty_lines[-len(CANONICAL_REWARD_FOOTER) :] == CANONICAL_REWARD_FOOTER
    checks.append(
        result(
            "test.sh:reward-footer",
            footer_ok,
            (
                "canonical multiline reward footer"
                if footer_ok
                else "test.sh must end with the canonical multiline rc/if/else/fi block"
            ),
        )
    )
    return checks


def emit(checks: list[dict[str, object]], json_out: Path | None) -> int:
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    payload = {"status": status, "checks": checks}
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for check in checks:
        print(f"{str(check['status']).upper():4} | {check['check']} | {check['detail']}")
    return 0 if status == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    category_parser = subparsers.add_parser("category")
    category_parser.add_argument("category")

    task_parser = subparsers.add_parser("validate-task")
    task_parser.add_argument("task_dir", type=Path)
    task_parser.add_argument("--json-out", type=Path)

    args = parser.parse_args()
    if args.command == "category":
        return emit(validate_category(args.category), None)
    return emit(validate_task(args.task_dir.resolve()), args.json_out)


if __name__ == "__main__":
    sys.exit(main())
