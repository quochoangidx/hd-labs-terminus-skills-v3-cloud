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


TAXONOMY = {
    "Science": {"Biology", "Chemistry", "Physics", "Earth", "Robotics", "Math", "Linguistics"},
    "Software": {"Algorithms", "Systems", "Databases", "Data engineering", "Frontend", "Languages"},
    "ML": {"Training", "Inference", "Evaluation", "Kernels"},
    "Operations": {"Finance", "Logistics", "Supply chain", "Claims", "Compliance", "Marketing"},
    "Security": {"Cryptography", "Reverse engineering", "Forensics", "AppSec"},
    "Hardware": {"CAD", "RTL"},
    "Media": {"Music", "Design"},
}
DIFFICULTIES = {"frontier", "advanced", "core", "base"}
REMOVED_FIELDS = {
    "version",
    "codebase_size",
    "number_of_milestones",
    "subcategories",
    "allow_internet",
    "expert_time_estimate_min",
    "junior_time_estimate_min",
}
CANONICAL_REWARD_FOOTER = [
    "rc=$?",
    'if [ "$rc" -eq 0 ]; then',
    "    echo 1 > /logs/verifier/reward.txt",
    "else",
    "    echo 0 > /logs/verifier/reward.txt",
    "fi",
    "exit 0",
]


def result(check: str, ok: bool, detail: str) -> dict[str, object]:
    return {"check": check, "status": "pass" if ok else "fail", "detail": detail}


def validate_category(category: str, subcategory: str) -> list[dict[str, object]]:
    pair_ok = category in TAXONOMY and subcategory in TAXONOMY.get(category, set())
    return [
        result(
            "taxonomy:pair",
            pair_ok,
            (
                f"{category} / {subcategory} is a valid Terminus 3 pair"
                if pair_ok
                else f"invalid Terminus 3 category/subcategory pair: {category!r} / {subcategory!r}"
            ),
        )
    ]


def validate_task(task_dir: Path) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    task_toml = task_dir / "task.toml"
    test_sh = task_dir / "tests" / "test.sh"

    try:
        manifest = tomllib.loads(task_toml.read_text())
        metadata = manifest.get("metadata", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        checks.append(result("task.toml:parse", False, str(exc)))
        manifest = {}
        metadata = {}
    else:
        checks.append(result("task.toml:parse", True, "valid TOML"))

    category = metadata.get("category")
    subcategory = metadata.get("subcategory")
    checks.extend(
        validate_category(
            category if isinstance(category, str) else "",
            subcategory if isinstance(subcategory, str) else "",
        )
    )

    name = manifest.get("name", metadata.get("name"))
    checks.append(result("task.toml:name", isinstance(name, str) and bool(name.strip()), f"name={name!r}"))

    artifacts = manifest.get("artifacts")
    artifacts_ok = (
        isinstance(artifacts, list)
        and bool(artifacts)
        and all(isinstance(path, str) and path.startswith("/") for path in artifacts)
    )
    checks.append(result("task.toml:artifacts", artifacts_ok, f"top-level artifacts={artifacts!r}"))

    difficulty = metadata.get("difficulty")
    checks.append(
        result(
            "task.toml:difficulty",
            difficulty in DIFFICULTIES,
            f"difficulty={difficulty!r}; expected one of {sorted(DIFFICULTIES)}",
        )
    )

    tags = metadata.get("tags")
    tags_ok = isinstance(tags, list) and 3 <= len(tags) <= 6 and all(isinstance(tag, str) and tag.strip() for tag in tags)
    checks.append(result("task.toml:tags", tags_ok, f"expected 3-6 non-empty tags, got {tags!r}"))

    required_text = (
        "difficulty_explanation",
        "solution_explanation",
        "verification_explanation",
        "relevant_experience",
    )
    missing_text = [key for key in required_text if not isinstance(metadata.get(key), str) or not metadata[key].strip()]
    checks.append(result("task.toml:explanations", not missing_text, f"missing={missing_text}"))

    hours = metadata.get("expert_time_estimate_hours")
    checks.append(result("task.toml:expert-hours", isinstance(hours, (int, float)) and hours > 0, f"value={hours!r}"))

    removed = sorted((set(manifest) | set(metadata) | set(manifest.get("environment", {}))) & REMOVED_FIELDS)
    checks.append(result("task.toml:no-terminus2-fields", not removed, f"obsolete fields={removed}"))

    verifier = manifest.get("verifier", {})
    checks.append(
        result(
            "task.toml:separate-verifier",
            verifier.get("environment_mode") == "separate",
            f"environment_mode={verifier.get('environment_mode')!r}",
        )
    )
    agent_timeout = manifest.get("agent", {}).get("timeout_sec")
    checks.append(
        result(
            "task.toml:agent-timeout",
            isinstance(agent_timeout, (int, float)) and 1800 <= agent_timeout <= 18000,
            f"timeout_sec={agent_timeout!r}; expected 1800-18000",
        )
    )
    network_mode = manifest.get("environment", {}).get("network_mode")
    checks.append(
        result(
            "task.toml:network-mode",
            network_mode in {"public", "no-network"},
            f"network_mode={network_mode!r}",
        )
    )

    languages = metadata.get("languages")
    language_ok = (
        isinstance(languages, list)
        and bool(languages)
        and all(
            isinstance(language, str)
            and bool(language.strip())
            and language == language.lower()
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
                else f"expected non-empty lowercase language names, got {languages!r}"
            ),
        )
    )

    tests_dockerfile = task_dir / "tests" / "Dockerfile"
    checks.append(
        result(
            "tests:Dockerfile",
            tests_dockerfile.is_file(),
            "present" if tests_dockerfile.is_file() else "required for the separate verifier",
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
    category_parser.add_argument("subcategory")

    task_parser = subparsers.add_parser("validate-task")
    task_parser.add_argument("task_dir", type=Path)
    task_parser.add_argument("--json-out", type=Path)

    args = parser.parse_args()
    if args.command == "category":
        return emit(validate_category(args.category, args.subcategory), None)
    return emit(validate_task(args.task_dir.resolve()), args.json_out)


if __name__ == "__main__":
    sys.exit(main())
