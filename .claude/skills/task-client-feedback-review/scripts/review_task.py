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
RUBRIC_HEADER_RE = re.compile(r"^#\s*Rubric\s+(\d+)\s*$", re.IGNORECASE)
RUBRIC_CRITERION_RE = re.compile(r"^Agent\b.*,\s*([+-])([1235])\s*$")
RUBRIC_BAD_SCORE_RE = re.compile(r",\s*[+-]?4\s*$")


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


def review_rubric_format(
    text: str,
    is_milestone: bool,
    findings: list[Finding],
    path: str,
) -> None:
    headers: list[int] = []
    positives: list[int] = []
    negatives: list[int] = []
    by_header: dict[int, dict[str, list[int]]] = {}
    current_header: int | None = None
    invalid_lines = 0

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        header_match = RUBRIC_HEADER_RE.match(line)
        if header_match:
            current_header = int(header_match.group(1))
            headers.append(current_header)
            by_header.setdefault(current_header, {"positive": [], "negative": []})
            continue
        criterion_match = RUBRIC_CRITERION_RE.match(line)
        if criterion_match:
            score = int(criterion_match.group(2))
            if criterion_match.group(1) == "-":
                negatives.append(score)
                if current_header is not None:
                    by_header.setdefault(current_header, {"positive": [], "negative": []})["negative"].append(score)
            else:
                positives.append(score)
                if current_header is not None:
                    by_header.setdefault(current_header, {"positive": [], "negative": []})["positive"].append(score)
            continue
        if RUBRIC_BAD_SCORE_RE.search(line) or line.startswith("Agent") or line.startswith("# Rubric"):
            invalid_lines += 1

    if invalid_lines:
        add(findings, "blocker", "rubric-format", f"{invalid_lines} rubric line(s) do not match `Agent ..., +/-N` with allowed values 1, 2, 3, or 5.", path, "terminus-regular-task-authoring")

    if is_milestone:
        if not headers:
            add(findings, "blocker", "rubric-headers", "Milestone rubric should use `# Rubric 1`, `# Rubric 2`, etc. blocks.", path, "terminus-regular-task-authoring")
        if len(negatives) < 3:
            add(findings, "should_fix", "rubric-negatives", "Rubric should include at least three negative criteria overall.", path, "terminus-regular-task-authoring")
        for header, scores in sorted(by_header.items()):
            positive_total = sum(scores["positive"])
            if scores["positive"] and not 10 <= positive_total <= 40:
                add(findings, "should_fix", "rubric-points", f"Rubric {header} positive total is {positive_total}; target range is 10-40 per milestone.", path, "terminus-regular-task-authoring")
            if not scores["negative"]:
                add(findings, "should_fix", "rubric-negatives", f"Rubric {header} should include at least one negative criterion.", path, "terminus-regular-task-authoring")
    elif any(n > 1 for n in headers):
        add(findings, "blocker", "rubric-headers", "Non-milestone rubric should be a flat list; `# Rubric 2+` is reserved for milestone tasks.", path, "terminus-regular-task-authoring")

    if positives:
        positive_total = sum(positives)
        if not is_milestone and not 10 <= positive_total <= 40:
            add(findings, "should_fix", "rubric-points", f"Non-milestone positive rubric total is {positive_total}; target range is 10-40.", path, "terminus-regular-task-authoring")
    if not is_milestone and len(negatives) < 3:
        add(findings, "should_fix", "rubric-negatives", "Non-milestone rubric should include at least three negative criteria.", path, "terminus-regular-task-authoring")
    try:
        return tomllib.loads(view.read_text("task.toml"))
    except Exception as exc:
        add(findings, "blocker", "metadata", f"task.toml does not parse: {exc}", "task.toml", "terminus-regular-task-authoring")
        return {}


def root_entries(files: Iterable[str]) -> set[str]:
    out = set()
    for name in files:
        first = name.split("/", 1)[0]
        out.add(first if "/" not in name else first + "/")
    return out


def review(path: Path) -> dict:
    view = TaskView(path)
    findings: list[Finding] = []
    files = view.files()
    file_set = set(files)

    try:
        if view.parent_prefix:
            add(findings, "blocker", "zip-structure", "ZIP contains an extra top-level task folder.", view.parent_prefix.rstrip("/"), "task-zip-submit")

        required = {"instruction.md", "task.toml", "environment/", "solution/", "tests/"}
        roots = root_entries(files)
        missing = [r for r in required if r.endswith("/") and r not in roots]
        missing += [r for r in required if not r.endswith("/") and r not in file_set]
        for item in missing:
            add(findings, "blocker", "layout", f"Missing required Regular task entry: {item}", item, "terminus-regular-task-authoring")

        allowed_roots = {"instruction.md", "task.toml", "environment/", "solution/", "tests/"}
        for item in sorted(roots):
            if item not in allowed_roots:
                add(findings, "should_fix", "zip-allowlist", f"Unexpected root entry: {item}", item, "task-zip-submit")

        task = parse_task_toml(view, findings)
        metadata = task.get("metadata", {}) if isinstance(task, dict) else {}
        codebase_size = metadata.get("codebase_size")
        languages = metadata.get("languages", [])

        if "pyproject.toml" in file_set:
            add(findings, "blocker", "root-pyproject", "Root-level pyproject.toml should not be submitted.", "pyproject.toml", "task-zip-submit")

        wheels = [n for n in files if n.startswith("tests/") and n.endswith(".whl")]
        for name in wheels[:10]:
            add(findings, "blocker", "tests-wheels", "Dependency wheel is under tests/.", name, "terminus-regular-task-authoring")
        if len(wheels) > 10:
            add(findings, "blocker", "tests-wheels", f"{len(wheels) - 10} additional wheels under tests/.", "tests/", "terminus-regular-task-authoring")

        if any(n.startswith("environment/data/") for n in files):
            add(findings, "blocker", "environment-data", "environment/data is present; verify it is not an oversized prompt/spec extension.", "environment/data", "upstream-repo-sanitizer")

        if codebase_size in {"minimal", "small"}:
            for name in files:
                if name.startswith("environment/") and LICENSE_RE.search(name):
                    add(findings, "blocker", "license-small", f"License/notice file appears in {codebase_size} codebase.", name, "upstream-repo-sanitizer")
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
            mkdir_pos = test_sh.find("mkdir -p /logs/verifier")
            pwd_pos = test_sh.find('if [ "$PWD" = "/" ]')
            if mkdir_pos == -1 or (pwd_pos != -1 and mkdir_pos > pwd_pos):
                add(findings, "blocker", "test-sh-logs", "tests/test.sh must create /logs/verifier before the PWD guard or other early exits.", "tests/test.sh", "terminus-regular-task-authoring")
            if re.search(r"fi\s*\n\s*exit\b|exit \$\?", test_sh):
                add(findings, "should_fix", "test-sh-exit", "tests/test.sh has a trailing exit; current template ends at the reward block.", "tests/test.sh", "terminus-regular-task-authoring")

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

        env_size = view.environment_size()
        if env_size > 100 * 1024 * 1024:
            add(findings, "blocker", "environment-size", f"environment/ is {env_size / (1024 * 1024):.1f} MiB, above 100 MiB.", "environment/", "upstream-repo-sanitizer")
        for name in files:
            if name.startswith("environment/") and view.file_size(name) > 50 * 1024 * 1024:
                add(findings, "blocker", "large-file", "File under environment/ exceeds 50 MiB.", name, "upstream-repo-sanitizer")

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
        is_milestone = "steps/" in roots and "instruction.md" not in file_set
        for name in rubric_files:
            rubric_text = view.read_text(name)
            if EVAL_REF_RE.search(rubric_text):
                add(findings, "blocker", "rubric-eval-ref", "Rubric references tests/verifier/evaluation language.", name, "terminus-regular-task-authoring")
            review_rubric_format(rubric_text, is_milestone, findings, name)

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
