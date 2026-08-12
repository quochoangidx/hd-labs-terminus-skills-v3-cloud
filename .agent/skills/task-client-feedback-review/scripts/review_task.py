#!/usr/bin/env python3
"""Review Terminus task folders or ZIPs against client feedback gates."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {
    "",
    ".bash",
    ".cfg",
    ".css",
    ".csv",
    ".dockerfile",
    ".h",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".lock",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

EVAL_REF_RE = re.compile(
    r"(?i)(\bverifier\b|\bhidden tests?\b|\btest_outputs\.py\b|\btest\.sh\b|"
    r"/tests/|\btests/|\brubrics?\b|\breward\.txt\b|\bpytest\b|"
    r"\bfinal test results?\b|\bCI\b)"
)
RUNTIME_SETUP_RE = re.compile(r"(?i)\b(pip install|apt-get|npm install|curl|wget)\b")
ENV_HINT_RE = re.compile(
    r"(?i)(step[- ]by[- ]step|solution|hint|TODO|walkthrough|implement by|"
    r"fix by|hidden tests|verifier|oracle)"
)
DOC_HINT_RE = re.compile(
    r"(?i)(step[- ]by[- ]step|solution|hint|walkthrough|implement by|fix by|"
    r"hidden tests|verifier|oracle)"
)
LICENSE_RE = re.compile(r"(?i)(^|/)(LICENSE|COPYING|NOTICE)(\..*)?$")
CANARY_RE = re.compile(r"CANARY-")
# CI's commercial-DB blacklist; 'maxscale' (MariaDB MaxScale) is the
# empirically-confirmed token (it substring-matches a decimal `MaxScale`
# identifier and still blocks). The full CI term list is unknown — bare
# oracle/mysql/postgres/mariadb/mssql/snowflake were observed NOT flagged.
COMMERCIAL_DB_RE = re.compile(r"(?i)maxscale")
BLACKLIST_SCAN_SUFFIXES = TEXT_SUFFIXES | {
    ".go", ".c", ".cc", ".cpp", ".cxx", ".hpp", ".java", ".ex", ".exs",
    ".sql", ".kt", ".scala", ".rb", ".pl",
}
RUBRIC_HEADER_RE = re.compile(r"^#\s*Rubric\s+(\d+)\s*$", re.IGNORECASE)
RUBRIC_CRITERION_RE = re.compile(r"^Agent\b.*,\s*([+-])([1235])\s*$")
RUBRIC_BAD_SCORE_RE = re.compile(r",\s*[+-]?4\s*$")
SUBMISSION_EXPLANATION_NAMES = {
    "submission-explanations.md",
    "submission-explanations-source.md",
}
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
REMOVED_METADATA_FIELDS = {
    "codebase_size",
    "number_of_milestones",
    "subcategories",
    "junior_time_estimate_min",
    "expert_time_estimate_min",
}


@dataclass
class Finding:
    severity: str
    check: str
    message: str
    path: str | None
    skill: str


class TaskView:
    def __init__(self, path: Path):
        self.path = path
        self.is_zip = path.suffix == ".zip"
        self._zip: zipfile.ZipFile | None = None
        self.parent_prefix = ""
        if self.is_zip:
            self._zip = zipfile.ZipFile(path)
            raw_names = [i.filename for i in self._zip.infolist()]
            roots = {
                n.split("/")[0]
                for n in raw_names
                if n and not n.endswith("/") and "/" in n
            }
            root_files = {n for n in raw_names if n and "/" not in n}
            if len(roots) == 1 and not root_files:
                only = next(iter(roots))
                if only.startswith("tbrain-"):
                    self.parent_prefix = only + "/"

    def close(self) -> None:
        if self._zip:
            self._zip.close()

    @property
    def name(self) -> str:
        if self.path.suffix == ".zip":
            return self.path.stem
        return self.path.name

    def files(self) -> list[str]:
        if self._zip:
            out = []
            for info in self._zip.infolist():
                n = info.filename
                if n.endswith("/"):
                    continue
                if self.parent_prefix and n.startswith(self.parent_prefix):
                    n = n[len(self.parent_prefix) :]
                out.append(n)
            return out
        return [
            str(p.relative_to(self.path))
            for p in self.path.rglob("*")
            if p.is_file()
        ]

    def exists(self, rel: str) -> bool:
        if self._zip:
            name = self.parent_prefix + rel
            return name in self._zip.namelist()
        return (self.path / rel).exists()

    def read_bytes(self, rel: str) -> bytes:
        if self._zip:
            return self._zip.read(self.parent_prefix + rel)
        return (self.path / rel).read_bytes()

    def read_text(self, rel: str, limit: int = 500_000) -> str:
        try:
            data = self.read_bytes(rel)
        except Exception:
            return ""
        return data[:limit].decode("utf-8", "replace")

    def file_size(self, rel: str) -> int:
        if self._zip:
            info = self._zip.getinfo(self.parent_prefix + rel)
            return info.file_size
        return (self.path / rel).stat().st_size

    def environment_size(self) -> int:
        return sum(self.file_size(n) for n in self.files() if n.startswith("environment/"))


def add(
    findings: list[Finding],
    severity: str,
    check: str,
    message: str,
    path: str | None,
    skill: str,
) -> None:
    findings.append(Finding(severity, check, message, path, skill))


def is_text_file(name: str) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in {".whl", ".zip", ".gz", ".tar", ".png", ".jpg", ".jpeg", ".gif"}:
        return False
    if suffix in {".so", ".dylib", ".rlib", ".a", ".o", ".bin"}:
        return False
    return suffix in TEXT_SUFFIXES


def parse_task_toml(view: TaskView, findings: list[Finding]) -> dict:
    if not view.exists("task.toml"):
        add(findings, "blocker", "layout", "Missing task.toml.", "task.toml", "terminus-regular-task-authoring")
        return {}
    try:
        return tomllib.loads(view.read_text("task.toml"))
    except Exception as exc:
        add(findings, "blocker", "metadata", f"task.toml does not parse: {exc}", "task.toml", "terminus-regular-task-authoring")
        return {}


def review_rubric_format(
    text: str,
    findings: list[Finding],
    path: str,
) -> None:
    headers: list[int] = []
    positives: list[int] = []
    negatives: list[int] = []
    invalid_lines = 0

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        header_match = RUBRIC_HEADER_RE.match(line)
        if header_match:
            headers.append(int(header_match.group(1)))
            continue
        criterion_match = RUBRIC_CRITERION_RE.match(line)
        if criterion_match:
            score = int(criterion_match.group(2))
            if criterion_match.group(1) == "-":
                negatives.append(score)
            else:
                positives.append(score)
            continue
        if RUBRIC_BAD_SCORE_RE.search(line) or line.startswith("Agent") or line.startswith("# Rubric"):
            invalid_lines += 1

    if invalid_lines:
        add(findings, "blocker", "rubric-format", f"{invalid_lines} rubric line(s) do not match `Agent ..., +/-N` with allowed values 1, 2, 3, or 5.", path, "terminus-regular-task-authoring")

    if headers:
        add(findings, "should_fix", "rubric-headers", "Terminus 3 rubrics should be a flat list of criterion lines.", path, "terminus-regular-task-authoring")

    if positives:
        positive_total = sum(positives)
        if not 10 <= positive_total <= 40:
            add(findings, "should_fix", "rubric-points", f"Positive rubric total is {positive_total}; target range is 10-40.", path, "terminus-regular-task-authoring")
    if not negatives:
        add(findings, "should_fix", "rubric-negatives", "Rubric should include at least one negative criterion.", path, "terminus-regular-task-authoring")


def root_entries(files: Iterable[str]) -> set[str]:
    out = set()
    for name in files:
        first = name.split("/", 1)[0]
        out.add(first if "/" not in name else first + "/")
    return out


def run_ruff(view: TaskView, findings: list[Finding]) -> None:
    """Mirror the platform CI ruff gate, which lints the WHOLE task tree
    (default E4/E7/E9/F rules) INCLUDING upstream .py under environment/repo."""
    import shutil
    import subprocess
    import tempfile

    py_files = [n for n in view.files() if n.endswith((".py", ".pyi"))]
    if not py_files:
        return
    ruff = shutil.which("ruff")
    if not ruff:
        cand = os.path.expanduser("~/.local/share/uv/tools/harbor/bin/ruff")
        ruff = cand if os.path.exists(cand) else None
    if not ruff:
        add(findings, "should_fix", "ruff-unavailable", f"Could not run ruff locally; {len(py_files)} .py file(s) (incl. environment/repo) are unverified. CI lints the whole task tree (default E4/E7/E9/F); ensure all .py are clean.", None, "upstream-repo-sanitizer")
        return
    if view.is_zip:
        target = tempfile.mkdtemp(prefix="ruff_review_")
        for rel in py_files:
            dest = os.path.join(target, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(view.read_bytes(rel))
    else:
        target = str(view.path)
    try:
        proc = subprocess.run([ruff, "check", "--output-format", "concise", target], capture_output=True, text=True, timeout=120)
    except Exception as exc:
        add(findings, "should_fix", "ruff-error", f"ruff could not run: {exc}", None, "upstream-repo-sanitizer")
        return
    out = proc.stdout + "\n" + proc.stderr
    err_lines = [ln.strip() for ln in out.splitlines() if re.search(r":\d+:\d+:", ln)]
    for ln in err_lines[:10]:
        msg = ln.replace(target.rstrip("/") + "/", "")
        add(findings, "blocker", "ruff", f"ruff: {msg}", None, "upstream-repo-sanitizer")
    if len(err_lines) > 10:
        add(findings, "blocker", "ruff", f"... and {len(err_lines) - 10} more ruff error(s).", None, "upstream-repo-sanitizer")


def check_blacklisted_db(view: TaskView, findings: list[Finding]) -> None:
    """CI blocks commercial-DB references; the confirmed token is 'maxscale'."""
    hits = []
    for name in view.files():
        if Path(name).suffix.lower() not in BLACKLIST_SCAN_SUFFIXES:
            continue
        if COMMERCIAL_DB_RE.search(view.read_text(name, limit=200_000)):
            hits.append(name)
    for name in hits[:8]:
        add(findings, "blocker", "blacklisted-db", "Contains 'maxscale' — CI blocks this as MariaDB MaxScale (often a false match on a decimal `MaxScale` identifier; rename to break the substring or remove the file if it is not build-required).", name, "upstream-repo-sanitizer")
    if len(hits) > 8:
        add(findings, "blocker", "blacklisted-db", f"... and {len(hits) - 8} more file(s) containing 'maxscale'.", None, "upstream-repo-sanitizer")


def review(path: Path) -> dict:
    view = TaskView(path)
    findings: list[Finding] = []
    files = view.files()
    file_set = set(files)

    try:
        if view.parent_prefix:
            add(findings, "blocker", "zip-structure", "ZIP contains an extra top-level task folder.", view.parent_prefix.rstrip("/"), "task-zip-submit")

        required = {
            "instruction.md",
            "task.toml",
            "environment/",
            "solution/",
            "tests/",
            "environment/Dockerfile",
            "solution/solve.sh",
            "tests/Dockerfile",
            "tests/test.sh",
            "tests/test_outputs.py",
        }
        roots = root_entries(files)
        missing = [r for r in required if r.endswith("/") and r not in roots]
        missing += [r for r in required if not r.endswith("/") and r not in file_set]
        for item in missing:
            add(findings, "blocker", "layout", f"Missing required Regular task entry: {item}", item, "terminus-regular-task-authoring")

        allowed_roots = {"instruction.md", "task.toml", "environment/", "solution/", "tests/"}
        for item in sorted(roots):
            if item not in allowed_roots:
                add(findings, "should_fix", "zip-allowlist", f"Unexpected root entry: {item}", item, "task-zip-submit")

        explanation_files = [
            name for name in files
            if Path(name).name.lower() in SUBMISSION_EXPLANATION_NAMES
        ]
        for name in explanation_files:
            add(
                findings,
                "blocker",
                "submission-explanations-in-task",
                "Reviewer-facing submission explanations must stay outside the task folder and ZIP.",
                name,
                "task-zip-submit",
            )

        task = parse_task_toml(view, findings)
        metadata = task.get("metadata", {}) if isinstance(task, dict) else {}
        languages = metadata.get("languages", [])

        artifacts = task.get("artifacts") if isinstance(task, dict) else None
        if not isinstance(artifacts, list) or not artifacts:
            add(findings, "blocker", "artifacts", "task.toml must declare a non-empty top-level artifacts array.", "task.toml", "terminus-regular-task-authoring")
            artifacts = []
        elif any(not isinstance(item, str) or not item.startswith("/") for item in artifacts):
            add(findings, "blocker", "artifacts", "Every artifact path must be an absolute string.", "task.toml", "terminus-regular-task-authoring")

        required_metadata = {
            "author_name",
            "author_email",
            "category",
            "subcategory",
            "tags",
            "languages",
            "difficulty",
            "expert_time_estimate_hours",
            "difficulty_explanation",
            "solution_explanation",
            "verification_explanation",
            "relevant_experience",
        }
        for field in sorted(required_metadata - set(metadata)):
            add(findings, "blocker", "metadata", f"Missing [metadata].{field}.", "task.toml", "terminus-regular-task-authoring")

        removed = sorted(REMOVED_METADATA_FIELDS & set(metadata))
        if isinstance(task, dict) and "version" in task:
            removed.append("version")
        environment = task.get("environment", {}) if isinstance(task, dict) else {}
        if isinstance(environment, dict) and "allow_internet" in environment:
            removed.append("allow_internet")
        if removed:
            add(findings, "blocker", "terminus2-metadata", f"Remove obsolete Terminus 2 field(s): {', '.join(removed)}.", "task.toml", "terminus-regular-task-authoring")

        difficulty = metadata.get("difficulty")
        if difficulty not in DIFFICULTIES:
            add(findings, "blocker", "difficulty", "difficulty must be frontier, advanced, core, or base.", "task.toml", "terminus-regular-task-authoring")
        category = metadata.get("category")
        subcategory = metadata.get("subcategory")
        if category not in TAXONOMY or subcategory not in TAXONOMY.get(category, set()):
            add(findings, "blocker", "taxonomy", "category/subcategory must be one exact Terminus 3 Title Case pair.", "task.toml", "task-miner")
        tags = metadata.get("tags")
        if not isinstance(tags, list) or not 3 <= len(tags) <= 6:
            add(findings, "blocker", "tags", "[metadata].tags must contain 3-6 values.", "task.toml", "terminus-regular-task-authoring")

        verifier = task.get("verifier", {}) if isinstance(task, dict) else {}
        if not isinstance(verifier, dict) or verifier.get("environment_mode") != "separate":
            add(findings, "blocker", "verifier-mode", "[verifier].environment_mode must be 'separate'.", "task.toml", "terminus-regular-task-authoring")
        network_mode = environment.get("network_mode") if isinstance(environment, dict) else None
        if network_mode not in {"public", "no-network"}:
            add(findings, "blocker", "network-mode", "[environment].network_mode must be 'public' or 'no-network'.", "task.toml", "terminus-regular-task-authoring")

        if "pyproject.toml" in file_set:
            add(findings, "blocker", "root-pyproject", "Root-level pyproject.toml should not be submitted.", "pyproject.toml", "task-zip-submit")

        wheels = [n for n in files if n.startswith("tests/") and n.endswith(".whl")]
        for name in wheels[:10]:
            add(findings, "blocker", "tests-wheels", "Dependency wheel is under tests/.", name, "terminus-regular-task-authoring")
        if len(wheels) > 10:
            add(findings, "blocker", "tests-wheels", f"{len(wheels) - 10} additional wheels under tests/.", "tests/", "terminus-regular-task-authoring")

        # Terminus 3 agent timeout is 1800-18000 seconds.
        agent_timeout = (task.get("agent") or {}).get("timeout_sec") if isinstance(task, dict) else None
        if not isinstance(agent_timeout, (int, float)) or not (1800 <= agent_timeout <= 18000):
            add(findings, "blocker", "agent-timeout", f"agent.timeout_sec is {agent_timeout!r}; Terminus 3 requires 1800-18000 seconds.", "task.toml", "terminus-regular-task-authoring")
        if isinstance(languages, list) and any(str(x).lower() == "python" for x in languages):
            env_py = [
                n for n in files
                if n.startswith("environment/") and n.endswith(".py")
                and "/tests/" not in n and "/test/" not in n
            ]
            if not env_py:
                add(findings, "should_fix", "languages", "Python appears to be verifier-only; remove it from metadata languages if the task implementation is not Python.", "task.toml", "terminus-regular-task-authoring")

        instruction = view.read_text("instruction.md")
        if instruction and EVAL_REF_RE.search(instruction):
            add(findings, "blocker", "instruction-eval-ref", "instruction.md references tests/verifier/rubric/evaluation language.", "instruction.md", "terminus-regular-task-authoring")

        test_sh = view.read_text("tests/test.sh")
        if not test_sh:
            add(findings, "blocker", "test-sh", "Missing tests/test.sh.", "tests/test.sh", "terminus-regular-task-authoring")
        else:
            if RUNTIME_SETUP_RE.search(test_sh):
                add(findings, "blocker", "test-sh-runtime-setup", "tests/test.sh installs packages or downloads at verifier runtime.", "tests/test.sh", "terminus-regular-task-authoring")
            if "mkdir -p /logs/verifier" not in test_sh:
                add(findings, "blocker", "test-sh-logs", "tests/test.sh must create /logs/verifier before pytest.", "tests/test.sh", "terminus-regular-task-authoring")
            if re.search(r"(?m)^\s*set\s+-[A-Za-z]*e[A-Za-z]*\b", test_sh):
                add(findings, "blocker", "test-sh-set-e", "tests/test.sh must not use set -e; pytest failures must reach the reward block.", "tests/test.sh", "terminus-regular-task-authoring")
            if "--ctrf /logs/verifier/ctrf.json" not in test_sh:
                add(findings, "blocker", "test-sh-ctrf", "pytest must write /logs/verifier/ctrf.json with --ctrf.", "tests/test.sh", "terminus-regular-task-authoring")
            if not re.search(r"(?m)^\s*exit\s+0\s*$", test_sh) or not test_sh.rstrip().endswith("exit 0"):
                add(findings, "blocker", "test-sh-exit", "Terminus 3 tests/test.sh must end with exit 0 after writing reward.txt.", "tests/test.sh", "terminus-regular-task-authoring")

        dockerfile = view.read_text("environment/Dockerfile")
        if dockerfile:
            if re.search(r"(?im)^\s*FROM\s+[^@\n]+$", dockerfile):
                add(findings, "blocker", "dockerfile-digest", "Dockerfile FROM line appears to lack a sha256 digest.", "environment/Dockerfile", "terminus-regular-task-authoring")
            if "tmux" not in dockerfile or "asciinema" not in dockerfile:
                add(findings, "blocker", "dockerfile-agent-deps", "Dockerfile should install tmux and asciinema.", "environment/Dockerfile", "terminus-regular-task-authoring")
            if re.search(r"(?im)^\s*COPY\s+.*\b(tests|solution)\b", dockerfile):
                add(findings, "blocker", "dockerfile-copy", "Dockerfile copies tests/ or solution/ into the image.", "environment/Dockerfile", "terminus-regular-task-authoring")
            if re.search(r"(?im)\bmkdir\b.*(/tests|/solution|/oracle|/logs/verifier)", dockerfile):
                add(findings, "blocker", "dockerfile-hidden-paths", "Dockerfile creates benchmark runtime paths.", "environment/Dockerfile", "terminus-regular-task-authoring")
        else:
            add(findings, "blocker", "dockerfile", "Missing environment/Dockerfile.", "environment/Dockerfile", "terminus-regular-task-authoring")

        verifier_dockerfile = view.read_text("tests/Dockerfile")
        if verifier_dockerfile:
            if re.search(r"(?im)^\s*FROM\s+[^@\n]+$", verifier_dockerfile):
                add(findings, "blocker", "verifier-digest", "tests/Dockerfile FROM line appears to lack a sha256 digest.", "tests/Dockerfile", "terminus-regular-task-authoring")
            for dep in ("pytest", "pytest-json-ctrf"):
                if dep not in verifier_dockerfile:
                    add(findings, "blocker", "verifier-deps", f"tests/Dockerfile does not bake in {dep}.", "tests/Dockerfile", "terminus-regular-task-authoring")
            if not re.search(r"(?im)^\s*COPY\s+\.\s+/tests/?\s*$", verifier_dockerfile):
                add(findings, "blocker", "verifier-copy", "tests/Dockerfile should copy its build context with `COPY . /tests/`.", "tests/Dockerfile", "terminus-regular-task-authoring")
            for artifact in artifacts:
                if not isinstance(artifact, str) or not artifact.startswith("/"):
                    continue
                landing = artifact.rstrip("/") if artifact.endswith("/") else str(Path(artifact).parent)
                if landing != "/" and landing not in verifier_dockerfile:
                    add(findings, "blocker", "artifact-landing-dir", f"tests/Dockerfile does not visibly create artifact landing directory {landing}.", "tests/Dockerfile", "terminus-regular-task-authoring")
        else:
            add(findings, "blocker", "verifier-dockerfile", "Missing tests/Dockerfile.", "tests/Dockerfile", "terminus-regular-task-authoring")

        env_size = view.environment_size()
        if env_size > 100 * 1024 * 1024:
            add(findings, "blocker", "environment-size", f"environment/ is {env_size / (1024 * 1024):.1f} MiB, above 100 MiB.", "environment/", "upstream-repo-sanitizer")
        for name in files:
            if name.startswith("environment/") and view.file_size(name) > 50 * 1024 * 1024:
                add(findings, "blocker", "large-file", "File under environment/ exceeds 50 MiB.", name, "upstream-repo-sanitizer")

        run_ruff(view, findings)
        check_blacklisted_db(view, findings)

        for name in files:
            if re.search(r"(^|/)(\.DS_Store|__MACOSX|__pycache__|\.ruff_cache|\.pytest_cache|\.mypy_cache)(/|$)", name) or name.endswith(".pyc") or "/._" in name or name.startswith("._"):
                add(findings, "blocker", "junk", "Cache or macOS resource file present.", name, "task-zip-submit")

        text_files = [n for n in files if is_text_file(n)]
        for name in text_files:
            text = view.read_text(name, limit=80_000)
            if CANARY_RE.search(text):
                add(findings, "blocker", "canary", "CANARY-* string present.", name, "task-zip-submit")
                break

        rubric_files = [n for n in files if "rubric" in Path(n).name.lower()]
        for name in rubric_files:
            rubric_text = view.read_text(name)
            if EVAL_REF_RE.search(rubric_text):
                add(findings, "blocker", "rubric-eval-ref", "Rubric references tests/verifier/evaluation language.", name, "terminus-regular-task-authoring")
            review_rubric_format(rubric_text, findings, name)

        env_hits = []
        for name in text_files:
            if not name.startswith("environment/"):
                continue
            if Path(name).name in {".dockerignore", "Dockerfile"}:
                continue
            text = view.read_text(name, limit=60_000)
            suffix = Path(name).suffix.lower()
            is_doc = suffix in {".md", ".txt", ".rst"} or re.search(
                r"(?i)(README|spec|architecture|design|guide)", Path(name).name
            )
            for idx, line in enumerate(text.splitlines(), 1):
                if is_doc:
                    match = DOC_HINT_RE.search(line)
                else:
                    stripped = line.lstrip()
                    is_comment = stripped.startswith(("#", "//", "/*", "*", "<!--"))
                    match = ENV_HINT_RE.search(line) if is_comment else None
                if match:
                    env_hits.append(f"{name}:{idx}")
                    break
        for sample in env_hits[:8]:
            add(findings, "should_fix", "environment-hint", "Environment file may contain hint/solution/evaluation language; inspect for false positives.", sample, "upstream-repo-sanitizer")
        if len(env_hits) > 8:
            add(findings, "should_fix", "environment-hint", f"{len(env_hits) - 8} additional environment hint hits.", "environment/", "upstream-repo-sanitizer")

        status = "ready"
        if any(f.severity == "blocker" for f in findings):
            status = "needs cleanup"
        if any(f.check in {"instruction-eval-ref", "rubric-eval-ref"} for f in findings):
            status = "needs prompt/rubric review"
        return {
            "task": view.name,
            "path": str(path),
            "status": status,
            "counts": {
                "blocker": sum(f.severity == "blocker" for f in findings),
                "should_fix": sum(f.severity == "should_fix" for f in findings),
                "polish": sum(f.severity == "polish" for f in findings),
            },
            "findings": [asdict(f) for f in findings],
        }
    finally:
        view.close()


def render_markdown(results: list[dict]) -> str:
    parts = []
    for result in results:
        parts.append(f"## {result['task']}")
        parts.append(f"Status: `{result['status']}`")
        findings = result["findings"]
        if not findings:
            parts.append("No automated client-feedback blockers found.")
            parts.append("")
            continue
        for severity in ("blocker", "should_fix", "polish"):
            group = [f for f in findings if f["severity"] == severity]
            if not group:
                continue
            title = {"blocker": "Blockers", "should_fix": "Should Fix", "polish": "Polish"}[severity]
            parts.append(f"{title}:")
            for f in group:
                where = f" `{f['path']}`" if f.get("path") else ""
                parts.append(f"- `{f['check']}`{where}: {f['message']} Skill: `{f['skill']}`.")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Task folders or submission ZIPs")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args(argv)

    results = [review(Path(p)) for p in args.paths]
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        print(render_markdown(results))
    return 1 if any(r["counts"]["blocker"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
