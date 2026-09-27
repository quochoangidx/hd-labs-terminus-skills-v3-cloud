#!/usr/bin/env python3
"""Executable policy checks shared by task generators and validators."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import ast
import hashlib
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
COPY_FROM_RE = re.compile(r"(?i)(?:^|\s)--from=([^\s]+)")
PIP_INSTALL_RE = re.compile(r"\bpip3?\b.*\binstall\b")
VERIFIER_DEP_RE = re.compile(r"(?<![\w-])(pytest(?:-json-ctrf)?)(?![\w-])")


AGENT_TEXT_SUFFIXES = {".md", ".rst", ".txt", ".py", ".toml", ".cfg", ".ini"}
PYTEST_WORD_RE = re.compile(r"(?i)\bpytest\b")


def agent_uses_pytest(task_dir: Path) -> bool:
    """True when the agent-facing task itself has the agent run pytest.

    The instruction, or a shipped README/test suite/config under environment/, counts.
    A shipped `python3 -m pytest tests` suite in an offline image needs pytest there.
    """
    candidates = [task_dir / "instruction.md"]
    env = task_dir / "environment"
    if env.is_dir():
        candidates += [
            path
            for path in env.rglob("*")
            if path.is_file() and path.suffix.lower() in AGENT_TEXT_SUFFIXES
        ]
    for path in candidates:
        try:
            if path.stat().st_size <= 1_000_000 and PYTEST_WORD_RE.search(path.read_text(errors="replace")):
                return True
        except OSError:
            continue
    return False


def verifier_deps_installed(dockerfile: str) -> list[str]:
    """Names of verifier-only packages a Dockerfile installs with pip.

    Continuation lines are joined first, so a multi-line RUN counts as one line.
    """
    logical = re.sub(r"\\\n", " ", dockerfile)
    found: set[str] = set()
    for line in logical.splitlines():
        if line.lstrip().startswith("#"):
            continue
        install = PIP_INSTALL_RE.search(line)
        if install:
            found.update(VERIFIER_DEP_RE.findall(line[install.end():]))
    return sorted(found)


def result(check: str, ok: bool, detail: str) -> dict[str, object]:
    return {"check": check, "status": "pass" if ok else "fail", "detail": detail}


def advisory(check: str, ok: bool, detail: str) -> dict[str, object]:
    """A check that is stricter than the documented platform contract.

    Hardening we want but the portal template does not require belongs here. Failing
    such a check would reject a task built exactly to the published template, and with
    no reviewer above the gate an author would then "fix" correct work.
    """
    return {"check": check, "status": "pass" if ok else "warn", "detail": detail}


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


def cloud_builder_copy_errors(text: str) -> list[str]:
    """Return COPY option forms accepted locally but rejected by the cloud builder."""
    aliases = {
        alias.lower()
        for _, _, alias, _ in docker_stages(text)
        if alias
    }
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not re.match(r"(?i)^\s*COPY\b", line):
            continue
        # --chown= takes named users/groups or numeric IDs: the cloud builder has
        # resolved names through /etc/passwd since 2026-09-17.
        source = COPY_FROM_RE.search(line)
        if not source:
            continue
        image = source.group(1)
        if image.lower() in aliases or image.isdigit():
            continue
        digest = DIGEST_RE.search(image)
        image_name = image[: digest.start()] if digest else image
        leaf = image_name.rsplit("/", 1)[-1]
        if digest is None or ":" in leaf:
            errors.append(
                f"line {line_number}: COPY --from={image} must use a digest-only image ref"
            )
    return errors


# Tools the agent harness runs inside the task container.
HARNESS_BINARIES = ("sed", "grep", "tail", "awk", "cut", "tr", "bash")


def validate_dockerfile(
    path: Path,
    role: str,
    artifacts: list[str] | None = None,
    agent_uses_pytest: bool = False,
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

    modal_errors = cloud_builder_copy_errors(text)
    checks.append(
        result(
            f"{role}-dockerfile:modal-syntax",
            not modal_errors,
            "COPY options are cloud-builder compatible" if not modal_errors else "; ".join(modal_errors),
        )
    )

    # docs/testing-and-validation/ci-checks-reference.md: "No platform pinning",
    # apt installs must not be version-pinned, and bare `nproc` is listed (severity
    # not stated, so it warns).
    logical = [line for line in re.sub(r"\\\n", " ", text).splitlines() if not line.lstrip().startswith("#")]
    platform_pinned = [line.strip() for line in logical if re.match(r"(?i)^\s*FROM\s+--platform=", line)]
    checks.append(
        result(
            f"{role}-dockerfile:no-platform-pin",
            not platform_pinned,
            "no FROM --platform=" if not platform_pinned else "; ".join(platform_pinned),
        )
    )
    apt_pinned = sorted({
        token
        for line in logical
        for segment in re.findall(r"\bapt(?:-get)?\s+install\b([^;&|]*)", line)
        for token in re.findall(r"(?<![\w=-])([a-z0-9][a-z0-9.+-]*=(?!=)[^\s;&|=]+)", segment)
    })
    checks.append(
        result(
            f"{role}-dockerfile:apt-unpinned",
            not apt_pinned,
            "apt packages are not version-pinned" if not apt_pinned else "apt versions must not be pinned: " + ", ".join(apt_pinned),
        )
    )
    bare_nproc = [line.strip() for line in logical if re.search(r"(?<![\w-])nproc(?![\w-])", line)]
    checks.append(
        advisory(
            f"{role}-dockerfile:no-bare-nproc",
            not bare_nproc,
            "no bare nproc" if not bare_nproc else "bare nproc: " + "; ".join(bare_nproc)[:200],
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
        # The agent harness shells out inside the task container (Terminus's
        # get-asciinema-timestamp.sh runs grep | tail | sed; Harbor's node bootstrap
        # pipes `node --version` through sed). Deleting one of these tools, e.g. for a
        # "reimplement sed" premise, killed every trial of tbrain-gnu-sed-reimplementation
        # v7 with NonZeroAgentExitCodeError while oracle and NOP still passed.
        removed = sorted(
            {
                tool
                for line in logical
                for tool in HARNESS_BINARIES
                if re.search(rf"(?:\brm\b[^;&|]*/{tool}\b|\bapt-get\s+(?:-\S+\s+)*(?:remove|purge)\b[^;&|]*\b{tool}\b)", line)
            }
        )
        checks.append(
            result(
                "agent-dockerfile:harness-binaries-kept",
                not removed,
                "no harness-used binary is removed" if not removed else f"removes {removed}; the agent harness calls them",
            )
        )
        # Quality panel `environment_hygiene` blocks on this: under a separate
        # verifier, pytest and its CTRF plugin belong to tests/Dockerfile only, unless
        # the agent-facing task itself has the agent run pytest.
        leaked = verifier_deps_installed(text)
        checks.append(
            result(
                "agent-dockerfile:no-verifier-deps",
                not leaked or agent_uses_pytest,
                (
                    "no verifier-only packages in the agent image"
                    if not leaked
                    else f"installs {leaked}; "
                    + (
                        "allowed, the agent-facing task has the agent run pytest"
                        if agent_uses_pytest
                        else "move them to tests/Dockerfile only"
                    )
                ),
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
        # Any COPY whose destination is /tests satisfies this: `COPY . /tests/` and an
        # explicit `COPY test.sh probe.py ... /tests/` file list are equally correct.
        copy_tests = re.search(r"(?im)^\s*COPY\s+(?:--\S+\s+)*\S.*?\s+/tests/?\s*$", text)
        checks.append(
            result(
                "verifier-dockerfile:copy-tests",
                copy_tests is not None,
                copy_tests.group(0).strip() if copy_tests else "no COPY lands in /tests/",
            )
        )
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


def platform_compose_files(task_dir: Path) -> list[Path]:
    """Compose files the platform's check_compose_networks actually scans."""
    return sorted(
        path
        for pattern in ("docker-compose*.yml", "docker-compose*.yaml")
        for path in (task_dir / "environment").glob(pattern)
    )


def compose_network_errors(text: str) -> list[str]:
    """Return Compose networking keys that collide with the Terminus 3 runner."""
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"^networks\s*:", line):
            errors.append(f"line {line_number}: top-level 'networks:' block")
        elif re.match(r"^\s+networks\s*:", line):
            errors.append(f"line {line_number}: per-service 'networks:' list")
        elif re.match(r"^\s+network_mode\s*:", line):
            errors.append(f"line {line_number}: per-service 'network_mode:'")
    return errors


def graded_disclosed_fixtures(task_dir: Path) -> list[str]:
    """Fixtures under tests/ that also ship to the agent and are named by a test function.

    A test whose expected bytes ship under environment/ is satisfiable by replaying the
    shipped file, so the panel reads it as an answer-replay channel (tbrain-cobol-
    statement-port v4, Protected Ground Truth Major). The build stage may still use
    such a file to prove the shipped sample is genuine; the test functions may not
    name it. Only string constants inside test_* bodies count, so a module docstring
    that mentions a shared source file, or a build-stage COPY, does not trip this.
    """
    environment = task_dir / "environment"
    tests = task_dir / "tests"
    if not environment.is_dir() or not tests.is_dir():
        return []

    def digest(path: Path) -> str | None:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return None

    shipped = {digest(path) for path in environment.rglob("*") if path.is_file() and path.name != ".dockerignore"}
    shipped.discard(None)
    shared: dict[str, Path] = {}
    for path in tests.rglob("*"):
        if not path.is_file() or path.suffix == ".py" or path.name in ("Dockerfile", "test.sh"):
            continue
        if path.stat().st_size and digest(path) in shipped:
            shared[path.name] = path
    if not shared:
        return []

    hits: list[str] = []
    for source in tests.rglob("*.py"):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                    for name, path in shared.items():
                        if name in inner.value:
                            hits.append(f"{source.relative_to(task_dir)}::{node.name} names {path.relative_to(task_dir)}")
    return sorted(set(hits))


SIZE_DISCLOSURE_RE = re.compile(r"\b(?:bytes?|[kKmMgG]i?B|kilobytes?|megabytes?|file size|size limit)\b")


def undisclosed_size_caps(task_dir: Path) -> list[str]:
    """Upper bounds on a candidate file's byte size that no agent-visible text states.

    The platform panel returned this shape as a Major coherent_contract finding twice in
    one assignment (tbrain-press-shop-scheduling v1, 2 MB; tbrain-bakery-fleet-dispatch
    v6, 5 MB): padding a valid artifact with whitespace or an ignored key past a cap the
    verifier added "for safety" flips a passing test. The verifier timeout already bounds
    pathological inputs. Only upper bounds count, so a non-empty check (size > 0) passes.
    """
    tests = task_dir / "tests"
    if not tests.is_dir():
        return []

    def is_size(node: ast.AST) -> bool:
        for inner in ast.walk(node):
            if isinstance(inner, ast.Attribute) and inner.attr in ("getsize", "st_size"):
                return True
        return False

    hits: list[str] = []
    for source in sorted(tests.rglob("*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            for index, op in enumerate(node.ops):
                left, right = operands[index], operands[index + 1]
                upper = (isinstance(op, (ast.Lt, ast.LtE)) and is_size(left)) or (
                    isinstance(op, (ast.Gt, ast.GtE)) and is_size(right)
                )
                if upper:
                    hits.append(f"{source.relative_to(task_dir)}:{node.lineno}")
    if not hits:
        return []
    visible = []
    for path in [task_dir / "instruction.md", *sorted((task_dir / "environment").rglob("*"))]:
        if path.is_file() and path.suffix in (".md", ".txt", ".rst", ""):
            try:
                visible.append(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
    if any(SIZE_DISCLOSURE_RE.search(text) for text in visible):
        return []
    return sorted(set(hits))


PROCESS_EVENT_RE = re.compile(r"subprocess|os\.exec|os\.fork|os\.system|os\.posix_spawn|os\.spawn")


def audit_hook_process_gaps(task_dir: Path) -> list[str]:
    """In-process launchers that try to stop process creation with an audit hook but leave
    a route open.

    Two routes, both proven by execution on tbrain-gnu-ed-reimplementation (v6 panel
    return, finding 28): ``_posixsubprocess.fork_exec``, the C helper behind subprocess,
    forks and executes without raising any audit event, so a hook that watches
    ``subprocess.*`` / ``os.exec*`` never sees it; and a hook defined at module level reads
    its policy from module globals the candidate can rebind (the panel's route was
    ``sys.modules['__main__']``), after which ``os.execv`` of a staged binary passes. A file
    that installs such a hook must mention ``fork_exec`` (it replaces or blocks the helper)
    and must build the hook inside a function, so its policy lives in a closure. A hook
    that also claims to stop native code (it names ``ctypes``) must name
    ``load_extension``: ``sqlite3.Connection.enable_load_extension`` loads a native
    library with no ctypes and no import (v8 panel return, finding 14).
    """
    tests = task_dir / "tests"
    if not tests.is_dir():
        return []
    hits: list[str] = []
    for source in sorted(tests.rglob("*.py")):
        try:
            text = source.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        hooks = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "addaudithook" and node.args):
                hooks.append(node.args[0])
        if not hooks or not PROCESS_EVENT_RE.search(text):
            continue
        rel = source.relative_to(task_dir)
        if "fork_exec" not in text:
            hits.append(f"{rel}: the hook never sees _posixsubprocess.fork_exec, which raises no audit event")
        if "ctypes" in text and "load_extension" not in text:
            hits.append(f"{rel}: the hook stops ctypes but not sqlite3 extension loading, which loads native "
                        "code without ctypes or an import")
        top_level = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for hook in hooks:
            if isinstance(hook, ast.Name) and hook.id in top_level:
                hits.append(f"{rel}: the hook {hook.id}() is a module-level function, so its policy is "
                            "module state the candidate can rebind; build it in a closure")
    return hits


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
    # The platform's automated `solvable` check reads this estimate against "a few hours at
    # most": on tbrain-gnu-sed-reimplementation a 12-hour estimate with a 1,400-line reference
    # passed that check three times and was returned on the fourth as an unreasonable amount
    # of work. Above eight hours the estimate itself argues the task is too large; cut breadth
    # and keep the hard thing before uploading.
    checks.append(advisory(
        "task.toml:expert-hours-bound",
        not isinstance(hours, (int, float)) or hours <= 8,
        f"value={hours!r}; the platform solvable check reads more than 8 hours as an unreasonable amount of work",
    ))

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
    environment_network_mode = manifest.get("environment", {}).get("network_mode")
    checks.append(
        result(
            "task.toml:environment-network-mode",
            environment_network_mode == "public",
            f"network_mode={environment_network_mode!r}; expected 'public'",
        )
    )
    # A Compose environment shares one network namespace, so the runner cannot
    # apply separate phase policies: check_compose_networks requires all three
    # phases to be "public" (portal 2026-09-18).
    is_compose = bool(platform_compose_files(task_dir))
    for phase in ("agent", "verifier"):
        phase_network_mode = manifest.get(phase, {}).get("network_mode")
        allowed = {"public"} if is_compose else {"public", "no-network"}
        checks.append(
            result(
                f"task.toml:{phase}-network-mode",
                phase_network_mode in allowed,
                f"network_mode={phase_network_mode!r}; expected "
                + ("'public' (compose task)" if is_compose else "'public' or 'no-network'"),
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
    checks.extend(
        validate_dockerfile(
            task_dir / "environment" / "Dockerfile",
            "agent",
            agent_uses_pytest=agent_uses_pytest(task_dir),
        )
    )
    checks.extend(
        validate_dockerfile(
            task_dir / "tests" / "Dockerfile",
            "verifier",
            artifact_paths,
        )
    )

    all_modal_errors: list[str] = []
    for dockerfile in sorted(task_dir.rglob("Dockerfile")):
        try:
            dockerfile_text = dockerfile.read_text(errors="replace")
        except OSError as exc:
            all_modal_errors.append(f"{dockerfile.relative_to(task_dir)}: {exc}")
            continue
        all_modal_errors.extend(
            f"{dockerfile.relative_to(task_dir)}: {error}"
            for error in cloud_builder_copy_errors(dockerfile_text)
        )
    checks.append(
        result(
            "dockerfiles:modal-syntax",
            not all_modal_errors,
            (
                "every submitted Dockerfile is cloud-builder compatible"
                if not all_modal_errors
                else "; ".join(all_modal_errors)
            ),
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

    network_errors = [
        f"{compose_file.name}: {error}"
        for compose_file in platform_compose_files(task_dir)
        for error in compose_network_errors(compose_file.read_text(errors="replace"))
    ]
    checks.append(
        result(
            "environment:compose-networks",
            not network_errors,
            "no compose-declared networks or per-service network_mode"
            if not network_errors
            else "; ".join(network_errors),
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
    # Advisory: docs/ never require the bit, and two platform-accepted ZIPs
    # (crop-water-balance, mechanical-royalty, 2026-09-26) shipped test.sh as 0600.
    checks.append(
        advisory(
            "test.sh:mode",
            os.access(test_sh, os.X_OK),
            "executable"
            if os.access(test_sh, os.X_OK)
            else "missing executable bit (stricter than docs/; accepted tasks shipped without it)",
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
    # Comments describe intent and routinely quote the very construct a check forbids
    # ("Deliberately NOT `set -e`: ..."). Judge the executable lines only.
    code_lines = [re.sub(r"(?<!\$)#.*$", "", line).rstrip() for line in text.splitlines()]
    code_lines = [line for line in code_lines if line.strip()]
    code = "\n".join(code_lines)

    # The property is that a failing step still reaches the reward write, so `set -e`
    # must be absent from the executable lines. How the rest of the flags are spelled
    # does not matter.
    aborts_early = re.search(r"^\s*set\s+-\S*e", code, re.M) is not None
    checks.append(
        result(
            "test.sh:no-errexit",
            not aborts_early,
            "a failing step still reaches the reward write"
            if not aborts_early
            else "set -e aborts before the reward write",
        )
    )
    # The property is a deterministic, explicitly versioned interpreter: `python3`, or
    # an absolute path such as a pinned venv (`/venv/bin/python`). Bare `python` on
    # PATH is what must not happen.
    bare_python = re.search(r"(?:^|[|&;(]\s*)python(?![0-9./\w-])", code, re.M) is not None
    explicit_python = (
        re.search(r"(?:^|[\s|&;(])(?:/\S+/)?python3(?![\w.-])", code, re.M) is not None
        or re.search(r"(?:^|[\s|&;(])/\S+/python(?![\w.-])", code, re.M) is not None
    )
    checks.append(
        result(
            "test.sh:python3",
            explicit_python and not bare_python,
            "explicit interpreter (python3 or an absolute/venv path)"
            if explicit_python and not bare_python
            else "resolve the interpreter explicitly: python3 or an absolute path, never bare python",
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

    # The property is that a killed or crashed verifier still leaves reward 0 behind, so
    # a default 0 must be written before the first step that can fail or hang. Any
    # spelling of the directory creation and the write is fine.
    def first_index(pattern: str) -> int | None:
        for index, line in enumerate(code_lines):
            if re.search(pattern, line):
                return index
        return None

    # The published portal template creates /logs/verifier and writes the reward only in
    # the two branches at the end; it does NOT pre-write a default 0. Blocking on the
    # early write would reject a task built exactly to the documented shape.
    #
    # What must hold is that both outcomes record a reward, so Harbor never hits
    # RewardNotFoundError. The early default is extra insurance against the verifier
    # being killed mid-run — worth suggesting, never worth failing.
    logdir_index = first_index(r"\b(?:install\s+-d|mkdir)\b.*\B/logs/verifier\b")
    checks.append(
        result(
            "test.sh:reward-dir",
            logdir_index is not None,
            "/logs/verifier is created before the reward is written"
            if logdir_index is not None
            else "create /logs/verifier before writing the reward",
        )
    )
    default_index = first_index(r"\b0\b.*>\s*/logs/verifier/reward\.txt")
    risky_index = first_index(r"\b(?:pytest|javac|go\s+test|cargo|npm|mvn|gradle|timeout)\b")
    early_default = (
        default_index is not None and (risky_index is None or default_index < risky_index)
    )
    checks.append(
        advisory(
            "test.sh:default-reward",
            early_default,
            "a default reward 0 is in place before the first step that can fail"
            if early_default
            else "optional hardening beyond the portal template: writing a default 0 before "
            "the first risky step leaves a reward behind even if the verifier is killed",
        )
    )
    # The property is that the exit status decides the reward: 1 on success, 0 otherwise.
    # Indentation, quoting and `[`/`[[` are the author's choice.
    tail = "\n".join(code_lines[-12:])
    footer_ok = (
        re.search(r"^\s*\w+=\$\?", tail, re.M) is not None
        and re.search(r"\b1\b.*>\s*/logs/verifier/reward\.txt", tail) is not None
        and re.search(r"\b0\b.*>\s*/logs/verifier/reward\.txt", tail) is not None
    )
    checks.append(
        result(
            "test.sh:reward-footer",
            footer_ok,
            (
                "the captured exit status decides reward 1 or 0"
                if footer_ok
                else "end test.sh by capturing the exit status and writing reward 1 on success, 0 otherwise"
            ),
        )
    )
    disclosed = graded_disclosed_fixtures(task_dir)
    checks.append(
        result(
            "tests:graded-disclosed-fixture",
            not disclosed,
            "no test function grades a fixture that also ships under environment/"
            if not disclosed
            else "a test grades a fixture the agent can read, so its expected bytes can be replayed: "
            + "; ".join(disclosed[:4]),
        )
    )
    hook_gaps = audit_hook_process_gaps(task_dir)
    checks.append(
        result(
            "tests:audit-hook-process-gap",
            not hook_gaps,
            "no in-process launcher leaves fork_exec or a rebindable module-level hook open"
            if not hook_gaps
            else "an audit-hook launcher can be bypassed by the program it runs: " + "; ".join(hook_gaps[:4]),
        )
    )
    size_caps = undisclosed_size_caps(task_dir)
    checks.append(
        result(
            "tests:undisclosed-size-cap",
            not size_caps,
            "no verifier caps a candidate file's size without an agent-visible limit"
            if not size_caps
            else "the verifier bounds a candidate file's byte size but no agent-visible text states a limit; "
            "drop the cap (the verifier timeout bounds pathological input) or state it: " + "; ".join(size_caps[:4]),
        )
    )
    return checks


def emit(checks: list[dict[str, object]], json_out: Path | None) -> int:
    status = "pass" if all(check["status"] != "fail" for check in checks) else "fail"
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
