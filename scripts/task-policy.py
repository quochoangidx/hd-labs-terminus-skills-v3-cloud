#!/usr/bin/env python3
"""Executable policy checks shared by task generators and validators."""

from __future__ import annotations

import argparse
import json
import os
import re
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
CANONICAL_IMAGES = {
    "public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb",
    "public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383",
    "public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac",
    "public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36",
    "public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14",
    "public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c",
    "public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df",
    "public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e",
    "public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d",
    "public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932",
}
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
FROM_RE = re.compile(
    r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+([A-Za-z0-9_.-]+))?\s*(?:#.*)?$",
    re.IGNORECASE,
)
DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$", re.IGNORECASE)
RUNTIME_SETUP_RE = re.compile(
    r"\b(?:uvx|pip(?:3)?\s+install|apt-get|npm\s+install|curl|wget|git\s+clone)\b",
    re.IGNORECASE,
)


def result(check: str, ok: bool, detail: str) -> dict[str, object]:
    return {"check": check, "status": "pass" if ok else "fail", "detail": detail}


def docker_stages(text: str) -> list[tuple[int, str, str | None, bool]]:
    """Return FROM entries and mark references to earlier stage aliases."""
    aliases: set[str] = set()
    stages: list[tuple[int, str, str | None, bool]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = FROM_RE.match(line)
        if not match:
            continue
        source, alias = match.groups()
        internal = source.lower() in aliases
        stages.append((line_number, source, alias, internal))
        if alias:
            aliases.add(alias.lower())
    return stages


def resolved_final_image(stages: list[tuple[int, str, str | None, bool]]) -> str:
    aliases = {alias.lower(): source for _, source, alias, _ in stages if alias}
    source = stages[-1][1]
    seen: set[str] = set()
    while source.lower() in aliases and source.lower() not in seen:
        seen.add(source.lower())
        source = aliases[source.lower()]
    return source


def has_base_justification(text: str) -> bool:
    comments = " ".join(
        line.lstrip()[1:].strip()
        for line in text.splitlines()
        if line.lstrip().startswith("#")
    ).lower()
    reason_terms = ("because", "requires", "not cover", "specific", "targeting", "unsupported")
    return len(comments.split()) >= 8 and any(term in comments for term in reason_terms)


def validate_dockerfile(
    path: Path,
    role: str,
    artifacts: list[str] | None = None,
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    try:
        text = path.read_text()
    except OSError as exc:
        return [result(f"{role}-dockerfile:read", False, str(exc))]

    stages = docker_stages(text)
    checks.append(result(f"{role}-dockerfile:from", bool(stages), f"{len(stages)} stage(s)"))
    if not stages:
        return checks

    unpinned = [
        f"line {line_number}: {source}"
        for line_number, source, _, internal in stages
        if not internal and not DIGEST_RE.search(source)
    ]
    checks.append(
        result(
            f"{role}-dockerfile:digests",
            not unpinned,
            "all external FROM images are digest-pinned" if not unpinned else "; ".join(unpinned),
        )
    )

    final_image = resolved_final_image(stages)
    canonical = final_image in CANONICAL_IMAGES
    justified = has_base_justification(text)
    checks.append(
        result(
            f"{role}-dockerfile:final-base",
            canonical or justified,
            (
                f"canonical image: {final_image}"
                if canonical
                else (
                    f"non-canonical image with reviewer-visible justification: {final_image}"
                    if justified
                    else f"non-canonical image lacks a credible Dockerfile comment: {final_image}"
                )
            ),
        )
    )

    if role == "agent":
        missing = [tool for tool in ("tmux", "asciinema") if not re.search(rf"\b{tool}\b", text)]
        checks.append(
            result(
                "agent-dockerfile:harness-tools",
                not missing,
                "tmux and asciinema present" if not missing else f"missing={missing}",
            )
        )
        hidden_copy = re.search(r"(?im)^\s*COPY\s+.*(?:tests|solution)(?:/|\s|$)", text)
        checks.append(
            result(
                "agent-dockerfile:no-hidden-copy",
                hidden_copy is None,
                "tests/ and solution/ are not copied" if hidden_copy is None else hidden_copy.group(0).strip(),
            )
        )
    else:
        pinned_deps = {
            "pytest": re.search(r"(?<![\w-])pytest==[0-9][A-Za-z0-9_.+-]*", text),
            "pytest-json-ctrf": re.search(r"pytest-json-ctrf==[0-9][A-Za-z0-9_.+-]*", text),
        }
        missing_deps = [name for name, match in pinned_deps.items() if match is None]
        checks.append(
            result(
                "verifier-dockerfile:pinned-deps",
                not missing_deps,
                "pytest and pytest-json-ctrf exactly pinned" if not missing_deps else f"missing={missing_deps}",
            )
        )
        copied = re.search(r"(?im)^\s*COPY\s+\.\s+/tests/?\s*$", text) is not None
        checks.append(result("verifier-dockerfile:copy-tests", copied, "COPY . /tests/" if copied else "missing"))
        missing_landing: list[str] = []
        for artifact in artifacts or []:
            landing = artifact.rstrip("/") if artifact.endswith("/") else str(Path(artifact).parent)
            if landing != "/" and landing not in text:
                missing_landing.append(landing)
        checks.append(
            result(
                "verifier-dockerfile:artifact-landing",
                not missing_landing,
                "all artifact landing directories present" if not missing_landing else f"missing={missing_landing}",
            )
        )
    return checks


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

    artifact_paths = [path for path in artifacts or [] if isinstance(path, str) and path.startswith("/")]
    checks.extend(validate_dockerfile(task_dir / "environment" / "Dockerfile", "agent"))
    checks.extend(
        validate_dockerfile(
            task_dir / "tests" / "Dockerfile",
            "verifier",
            artifact_paths,
        )
    )

    environment_files = [path for path in (task_dir / "environment").rglob("*") if path.is_file()]
    environment_size = sum(path.stat().st_size for path in environment_files)
    oversized = [
        str(path.relative_to(task_dir))
        for path in environment_files
        if path.stat().st_size > 50 * 1024 * 1024
    ]
    checks.append(
        result(
            "environment:size",
            environment_size <= 100 * 1024 * 1024 and not oversized,
            (
                f"{environment_size / (1024 * 1024):.1f} MiB; no file above 50 MiB"
                if not oversized
                else f"files above 50 MiB: {oversized}"
            ),
        )
    )

    compose_files = [
        path
        for pattern in ("docker-compose*.yml", "docker-compose*.yaml", "compose*.yml", "compose*.yaml")
        for path in (task_dir / "environment").glob(pattern)
    ]
    dangerous_compose: list[str] = []
    for compose_file in compose_files:
        compose_text = compose_file.read_text(errors="replace")
        if re.search(r"(?im)^\s*privileged\s*:\s*true\s*$", compose_text):
            dangerous_compose.append(f"{compose_file.name}: privileged")
        for token in ("SYS_ADMIN", "NET_ADMIN", "SYS_MODULE", "/var/run/docker.sock"):
            if token in compose_text:
                dangerous_compose.append(f"{compose_file.name}: {token}")
        for reserved in ("/logs/artifacts", "/logs/verifier", "/tests", "/solution"):
            if re.search(rf":\s*{re.escape(reserved)}(?:\s|$)", compose_text):
                dangerous_compose.append(f"{compose_file.name}: shadows {reserved}")
    checks.append(
        result(
            "environment:compose-safety",
            not dangerous_compose,
            "no dangerous compose privileges, capabilities, sockets, or mounts"
            if not dangerous_compose
            else "; ".join(dangerous_compose),
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
    checks.append(
        result(
            "test.sh:no-runtime-setup",
            RUNTIME_SETUP_RE.search(text) is None,
            "no package install or network fetch" if RUNTIME_SETUP_RE.search(text) is None else "runtime setup found",
        )
    )
    checks.append(
        result(
            "test.sh:ctrf",
            "--ctrf /logs/verifier/ctrf.json" in text,
            "writes CTRF report" if "--ctrf /logs/verifier/ctrf.json" in text else "required flag missing",
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
