#!/usr/bin/env python3
"""Prepare and summarize isolated local solve probes for Terminus tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


GLOBAL_EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
TOP_LEVEL_EXCLUDE_DIRS = {
    "reports",
    "solution",
    "submissions",
    "tests",
}
EXCLUDE_PREFIXES = ("rubric",)
EXCLUDE_SUFFIXES = ("_rubric.md", "_rubric.txt", "-rubric.md", "-rubric.txt", ".zip")
EXCLUDE_FILES = {"task.toml"}
VALID_RESULTS = {"pass", "fail"}
VALID_TYPES = {"semantic", "compile", "setup", "timeout", "unknown"}
VALID_RUNNERS = {"codex-subagent", "claude-agent"}
VALID_RUNTIMES = {"codex", "claude-code"}
# Claude probes must run on the platform's difficulty model (user decision,
# 2026-09-26). The `opus` alias resolves to Opus 5.5, which is stronger than the
# platform's Opus 5 and read silence clauses differently, so the model a run was
# actually served is read from the subagent's JSONL transcript, not trusted from a flag.
PLATFORM_CLAUDE_PROBE_MODEL = "claude-opus-5"
PLATFORM_CLAUDE_PROBE_MODEL_RE = re.compile(r"^claude-opus-5(?:-\d{8})?$")


def should_ignore(path: Path, root: Path | None = None) -> bool:
    name = path.name
    if name in EXCLUDE_FILES:
        return True
    # Finder writes .DS_Store and ._* whenever a folder is browsed; one appearing after
    # prepare made a finished pair unrecordable (trace-metal cycle 3, 2026-09-26)
    if name == ".DS_Store" or name.startswith("._"):
        return True
    if path.is_dir():
        if name in GLOBAL_EXCLUDE_DIRS:
            return True
        if root is not None and path.parent.resolve() == root.resolve() and name in TOP_LEVEL_EXCLUDE_DIRS:
            return True
    if name.startswith(EXCLUDE_PREFIXES):
        return True
    return name.endswith(EXCLUDE_SUFFIXES)


def copy_task(src: Path, dst: Path, *, sanitized: bool) -> None:
    if dst.exists():
        raise SystemExit(f"Refusing to overwrite existing directory: {dst}")

    def ignore(directory: str, names: list[str]) -> set[str]:
        if not sanitized:
            return set()
        base = Path(directory)
        return {name for name in names if should_ignore(base / name, src)}

    # Keep upstream repository symlinks as symlinks. Dereferencing them changes
    # the sanitized tree shape and makes an otherwise unchanged baseline fail
    # the frozen solver-contract hash check.
    shutil.copytree(src, dst, ignore=ignore, symlinks=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path, *, sanitized: bool) -> str:
    digest = hashlib.sha256()
    volatile_dirs = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in volatile_dirs for part in rel.parts):
            continue
        if sanitized and any(part in GLOBAL_EXCLUDE_DIRS for part in rel.parts):
            continue
        if sanitized and rel.parts and rel.parts[0] in TOP_LEVEL_EXCLUDE_DIRS:
            continue
        if sanitized and should_ignore(path, root):
            continue
        # Hash symlink targets by content so source and symlink-preserving probe
        # copies share the same frozen contract representation.
        if path.is_dir():
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def file_hash_map(root: Path, *, sanitized: bool) -> dict[str, str]:
    files: dict[str, str] = {}
    volatile_dirs = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in volatile_dirs for part in rel.parts):
            continue
        if sanitized and any(part in GLOBAL_EXCLUDE_DIRS for part in rel.parts):
            continue
        if sanitized and rel.parts and rel.parts[0] in TOP_LEVEL_EXCLUDE_DIRS:
            continue
        if sanitized and should_ignore(path, root):
            continue
        if path.is_dir():
            continue
        files[rel.as_posix()] = sha256(path)
    return files


def matrix_from_ctrf(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid verification CTRF {path}: {exc}") from exc
    tests = data.get("tests")
    if not isinstance(tests, list):
        results = data.get("results")
        tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list) or not tests:
        raise SystemExit(f"{path}: tests must be a non-empty list")
    passed: list[str] = []
    failed: list[str] = []
    for index, item in enumerate(tests):
        if not isinstance(item, dict):
            raise SystemExit(f"{path}: tests[{index}] must be an object")
        case_id = item.get("name") or item.get("testId")
        status = str(item.get("status", "")).strip().lower()
        if not isinstance(case_id, str) or not case_id.strip():
            raise SystemExit(f"{path}: tests[{index}] has no name/testId")
        if status in {"passed", "pass"}:
            passed.append(case_id)
        elif status in {"failed", "fail"}:
            failed.append(case_id)
        else:
            raise SystemExit(
                f"{path}: tests[{index}] has unsupported status {status!r}; "
                "skipped/unknown units cannot count as semantic evidence"
            )
    if len(set(passed + failed)) != len(passed) + len(failed):
        raise SystemExit(f"{path}: test names must be unique")
    return {
        "total_units": len(passed) + len(failed),
        "passed_case_ids": sorted(passed),
        "failed_case_ids": sorted(failed),
    }


def load_manifest(probe_dir: Path) -> dict:
    path = probe_dir / "probe-manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid probe manifest {path}: {exc}") from exc
    if data.get("schema_version") not in {2, 3}:
        raise SystemExit(f"Unsupported probe manifest schema in {path}")
    return data


def semantic_node_map(path: Path) -> dict[str, set[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid semantic coverage manifest {path}: {exc}") from exc
    mapping: dict[str, set[str]] = {}
    for key, prefix in (("mechanisms", "M"), ("interactions", "I")):
        rows = data.get(key)
        if not isinstance(rows, list):
            raise SystemExit(f"{path}: {key} must be a list")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                raise SystemExit(f"{path}: invalid {key} row")
            for test_id in row.get("test_ids", []):
                if isinstance(test_id, str):
                    mapping.setdefault(test_id, set()).add(f"{prefix}:{row['id']}")
    return mapping


def semantic_failure_geometry(
    case_sets: list[tuple[set[str], set[str]]],
    node_map: dict[str, set[str]],
    total: int,
    passed: int,
) -> dict:
    failure_sets = [
        frozenset(
            node
            for test_id in failed_ids
            for node in node_map.get(test_id, set())
        )
        for _, failed_ids in case_sets
        if failed_ids
    ]
    de_correlated = len(failure_sets) >= 2 and len(set(failure_sets)) >= 2
    advanced_pass = (
        total == 3
        and passed == 1
        and len(failure_sets) == 2
        and all(len(nodes) >= 2 for nodes in failure_sets)
        and de_correlated
    )
    return {
        "failure_sets": failure_sets,
        "semantic_decorrelated": de_correlated,
        "advanced_geometry_pass": advanced_pass,
    }


def validate_case_matrix(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid case matrix {path}: {exc}") from exc
    passed = data.get("passed_case_ids")
    failed = data.get("failed_case_ids")
    total = data.get("total_units")
    if not isinstance(passed, list) or not all(isinstance(item, str) and item for item in passed):
        raise SystemExit(f"{path}: passed_case_ids must be non-empty strings")
    if not isinstance(failed, list) or not all(isinstance(item, str) and item for item in failed):
        raise SystemExit(f"{path}: failed_case_ids must be strings")
    if len(set(passed)) != len(passed) or len(set(failed)) != len(failed):
        raise SystemExit(f"{path}: case IDs must be unique within each list")
    if set(passed) & set(failed):
        raise SystemExit(f"{path}: passed_case_ids and failed_case_ids overlap")
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        raise SystemExit(f"{path}: total_units must be a positive integer")
    if len(passed) + len(failed) != total:
        raise SystemExit(f"{path}: total_units does not match the case ID lists")
    return data


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def prepare(args: argparse.Namespace) -> None:
    task = Path(args.task).resolve()
    if not task.exists() or not task.is_dir():
        raise SystemExit(f"Task folder not found: {task}")
    slug = task.name
    out = Path(args.output or Path("workspace/local-solve-probes") / slug).resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "probe-manifest.json"
    contract_hash = tree_hash(task, sanitized=True)
    task_snapshot = tree_hash(task, sanitized=False)
    mode = "exploratory" if args.exploratory else "counted"
    profile = args.profile
    report_dir = Path(
        args.report_dir or Path("workspace/reports") / slug
    ).resolve()
    coverage_path = Path(
        args.semantic_coverage
        or report_dir / "semantic-coverage.json"
    ).resolve()
    sufficiency_path = Path(
        args.sufficiency
        or report_dir / "instruction-sufficiency.json"
    ).resolve()
    verifier_path = Path(
        args.verifier_matrix
        or report_dir / "verifier-matrix.json"
    ).resolve()
    coverage_hash = None
    sufficiency_hash = None
    preprobe_receipts: dict[str, str] = {}
    if mode == "counted":
        sufficiency_checker = (
            Path(__file__).resolve().parents[2]
            / "terminus-regular-task-authoring"
            / "scripts"
            / "sufficiency_manifest_check.py"
        )
        sufficiency_result = run(
            [
                sys.executable,
                str(sufficiency_checker),
                "--require-v3",
                str(task),
                str(sufficiency_path),
            ]
        )
        if sufficiency_result.returncode != 0:
            raise SystemExit(
                "Counted probes require V3 evidence inferability:\n"
                + sufficiency_result.stdout
                + sufficiency_result.stderr
            )
        checker = (
            Path(__file__).resolve().parents[2]
            / "terminus-regular-task-authoring"
            / "scripts"
            / "semantic_coverage_check.py"
        )
        command = [sys.executable, str(checker)]
        if profile in {"advanced_frontier_only", "core_advanced_frontier"}:
            command.append("--advanced-plus")
        command.extend([str(task), str(coverage_path), str(verifier_path)])
        checked = run(command)
        if checked.returncode != 0:
            raise SystemExit(
                "Counted probes require frozen semantic coverage:\n"
                + checked.stdout
                + checked.stderr
            )
        coverage_hash = sha256(coverage_path)
        sufficiency_hash = sha256(sufficiency_path)
        preprobe_checker = Path(__file__).with_name("preprobe_check.py")
        preprobe_command = [
            sys.executable,
            str(preprobe_checker),
            str(task),
            str(report_dir),
        ]
        if args.quota_run_override:
            preprobe_command.extend(
                ["--quota-run-override", str(Path(args.quota_run_override).resolve())]
            )
        preprobe_result = run(preprobe_command)
        if preprobe_result.returncode != 0:
            raise SystemExit(
                "Counted probes require frozen pre-probe technical/review/style/role gates:\n"
                + preprobe_result.stdout
                + preprobe_result.stderr
            )
        for name in (
            "probe-preflight.json",
            "pre-freeze-review.json",
            "task-style-preflight.json",
            "agent-session-budget.json",
        ):
            preprobe_receipts[name] = sha256(report_dir / name)
        if args.quota_run_override:
            override_path = Path(args.quota_run_override).resolve()
            if override_path.parent != report_dir:
                raise SystemExit("Quota-run override must stay in the task report directory")
            preprobe_receipts[override_path.name] = sha256(override_path)
    if manifest_path.exists():
        manifest = load_manifest(out)
        if manifest.get("task_slug") != slug or Path(manifest.get("source_task", "")).resolve() != task:
            raise SystemExit(f"Probe directory belongs to a different task: {out}")
        if manifest.get("solver_contract_sha256") != contract_hash:
            raise SystemExit(
                "The instruction/environment contract changed after probe preparation; "
                "start a fresh probe directory"
            )
        if (
            manifest.get("schema_version") != 3
            or manifest.get("mode") != mode
            or manifest.get("profile") != profile
            or (
                mode == "counted"
                and Path(str(manifest.get("report_dir", ""))).resolve() != report_dir
            )
        ):
            raise SystemExit("Probe mode/profile/schema changed; start a fresh probe directory")
        if manifest.get("task_snapshot_sha256") != task_snapshot:
            raise SystemExit("Task/verifier snapshot changed; start a fresh probe directory")
        if mode == "counted" and manifest.get("semantic_coverage_sha256") != coverage_hash:
            raise SystemExit("Semantic coverage evidence changed; start a fresh probe directory")
        if mode == "counted" and manifest.get("instruction_sufficiency_sha256") != sufficiency_hash:
            raise SystemExit("Evidence inferability receipt changed; start a fresh probe directory")
        if mode == "counted" and manifest.get("verifier_matrix_sha256") != sha256(verifier_path):
            raise SystemExit("Verifier matrix evidence changed; start a fresh probe directory")
        if mode == "counted" and manifest.get("preprobe_receipts") != preprobe_receipts:
            raise SystemExit(
                "Pre-probe technical/review/style/role evidence changed; start fresh runs"
            )
    else:
        if any(out.iterdir()):
            raise SystemExit(f"Refusing to initialize a non-empty probe directory: {out}")
        manifest = {
            "schema_version": 3,
            "task_slug": slug,
            "source_task": str(task),
            "mode": mode,
            "profile": profile,
            "report_dir": str(report_dir) if mode == "counted" else None,
            "solver_contract_sha256": contract_hash,
            "task_snapshot_sha256": task_snapshot,
            "semantic_coverage": str(coverage_path) if mode == "counted" else None,
            "semantic_coverage_sha256": coverage_hash,
            "instruction_sufficiency": str(sufficiency_path) if mode == "counted" else None,
            "instruction_sufficiency_sha256": sufficiency_hash,
            "verifier_matrix": str(verifier_path) if mode == "counted" else None,
            "verifier_matrix_sha256": sha256(verifier_path) if mode == "counted" else None,
            "preprobe_receipts": preprobe_receipts if mode == "counted" else {},
            "prepared_at": utc_now(),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for idx in range(1, args.runs + 1):
        run_dir = out / f"run_{idx}"
        if run_dir.exists():
            continue
        run_dir.mkdir(exist_ok=False)
        copy_task(task, run_dir / "baseline", sanitized=True)
        copy_task(task, run_dir / "solve", sanitized=True)
        copy_task(task, run_dir / "verify", sanitized=False)
        prompt = run_dir / "solve_prompt.md"
        prompt.write_text(
            "You are solving a Terminus Regular task locally. Work only inside "
            "this copied task folder. Do not search for solution, tests, rubrics, "
            "reports, or platform feedback. Read instruction.md and the codebase, "
            "make the fix, and run whatever local checks are available inside the "
            "copied environment. Stop when you have a candidate patch. This is a "
            "one-shot attempt: after your final answer, you will not receive "
            "verifier feedback for another try.\n",
            encoding="utf-8",
        )
        (run_dir / "result.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "task": slug,
                    "run": idx,
                    "result": None,
                    "failure_type": None,
                    "notes": "",
                    "evidence_complete": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(out)


def diff_run(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    baseline = run_dir / "baseline"
    solve = run_dir / "solve"
    if not baseline.exists() or not solve.exists():
        raise SystemExit("run_dir must contain baseline/ and solve/")
    proc = run(["diff", "-ruN", "--exclude", ".git", str(baseline), str(solve)])
    patch = run_dir / "solve.diff"
    patch.write_text(proc.stdout, encoding="utf-8")
    if not proc.stdout.strip():
        print(
            "WARNING: solver produced no diff; record it only if the unchanged starter "
            "passes, which means the starter already satisfies the task",
            file=sys.stderr,
        )
    print(patch)


def materialize_run(args: argparse.Namespace) -> None:
    """Rebuild verify/ from the current full task plus the solver-only delta."""
    run_dir = Path(args.run_dir).resolve()
    probe_dir = run_dir.parent
    manifest = load_manifest(probe_dir)
    source_task = Path(manifest["source_task"]).resolve()
    baseline = run_dir / "baseline"
    solve = run_dir / "solve"
    verify = run_dir / "verify"
    if not baseline.is_dir() or not solve.is_dir():
        raise SystemExit("run_dir must contain baseline/ and solve/")
    baseline_files = file_hash_map(baseline, sanitized=False)
    solve_files = file_hash_map(solve, sanitized=False)
    source_contract_files = file_hash_map(source_task, sanitized=True)
    if baseline_files != source_contract_files:
        raise SystemExit("baseline/ does not match the current sanitized solver contract")
    changed_paths = {
        rel
        for rel in baseline_files.keys() | solve_files.keys()
        if baseline_files.get(rel) != solve_files.get(rel)
    }
    if not changed_paths:
        raise SystemExit("solve/ contains no candidate implementation change")
    invalid_changes = sorted(
        rel for rel in changed_paths if not rel.startswith("environment/")
    )
    if invalid_changes:
        raise SystemExit(
            "Solver changes outside environment/ are forbidden: " + ", ".join(invalid_changes)
        )
    if verify.exists():
        shutil.rmtree(verify)
    copy_task(source_task, verify, sanitized=False)
    for rel in sorted(changed_paths):
        source = solve / rel
        target = verify / rel
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        elif target.exists():
            target.unlink()
    print(verify)


def apply_run(args: argparse.Namespace) -> None:
    # WARNING: do NOT use `apply` when the solve copy was sanitized (the
    # default from `prepare`): the `diff -ruN` in `diff` records the
    # sanitized-away solution/ and tests/ as deletions, so applying it
    # corrupts verify/. Copy the solver's changed source file(s) into
    # verify/ manually instead (see SKILL.md, fair-probe section).
    print(
        "WARNING: `apply` corrupts verify/ when the solve copy was sanitized "
        "(diff records solution/ and tests/ as deletions). Prefer manually "
        "copying the changed source files into verify/ (see SKILL.md).",
        file=sys.stderr,
    )
    run_dir = Path(args.run_dir).resolve()
    patch = run_dir / "solve.diff"
    verify = run_dir / "verify"
    if not patch.exists():
        raise SystemExit(f"Missing patch: {patch}")
    if not verify.exists():
        raise SystemExit(f"Missing verify copy: {verify}")
    proc = run(["patch", "-p1", "-i", str(patch)], cwd=verify)
    (run_dir / "apply.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"Patch apply failed; see {run_dir / 'apply.log'}")
    print(run_dir / "apply.log")


def served_models(jsonl_path: Path) -> list[str]:
    """Models that actually answered in a Claude Code subagent JSONL transcript."""
    models: list[str] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        if entry.get("type") == "assistant" and isinstance(message, dict):
            model = message.get("model")
            if isinstance(model, str) and model and model != "<synthetic>":
                models.append(model)
    return models


def claude_probe_model_errors(declared: str, served: list[str]) -> list[str]:
    errors = []
    if not PLATFORM_CLAUDE_PROBE_MODEL_RE.match(declared):
        errors.append(
            f"--model must be {PLATFORM_CLAUDE_PROBE_MODEL} for a Claude probe (got {declared!r}); "
            "the `opus` alias resolves to Opus 5.5"
        )
    if not served:
        errors.append("the agent JSONL transcript shows no assistant model; cannot prove the probe ran on Opus 5")
    wrong = sorted({model for model in served if not PLATFORM_CLAUDE_PROBE_MODEL_RE.match(model)})
    if wrong:
        errors.append(
            f"the probe was served by {', '.join(wrong)}, not {PLATFORM_CLAUDE_PROBE_MODEL}; "
            "discard this run, launch terminus-probe without a model argument, and re-run"
        )
    return errors


def probe_dir_matches(slug: str, name: str) -> bool:
    """A probe folder is the slug itself or the slug plus a suffix.

    The builder_certified route keeps one folder per probe cycle
    (`<slug>-skeleton`, `<slug>-cycle-2`) so earlier pairs survive, and requiring
    the bare slug forced sessions to rename folders around every `record` call.
    """
    return bool(slug) and (name == slug or name.startswith(slug + "-"))


def record(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    if args.result not in VALID_RESULTS:
        raise SystemExit(f"--result must be one of: {', '.join(sorted(VALID_RESULTS))}")
    if args.type not in VALID_TYPES:
        raise SystemExit(f"--type must be one of: {', '.join(sorted(VALID_TYPES))}")
    if args.runner not in VALID_RUNNERS:
        raise SystemExit(f"--runner must be one of: {', '.join(sorted(VALID_RUNNERS))}")
    if args.runtime not in VALID_RUNTIMES:
        raise SystemExit(f"--runtime must be one of: {', '.join(sorted(VALID_RUNTIMES))}")
    if not args.agent_session_id.strip():
        raise SystemExit("--agent-session-id must be non-empty")
    if not args.model.strip():
        raise SystemExit("--model must be non-empty")
    if args.reasoning_effort != "medium":
        raise SystemExit("--reasoning-effort must be medium for task-batch evidence")
    jsonl_source: Path | None = None
    models_served: list[str] = []
    if args.runtime == "claude-code":
        if not args.agent_jsonl:
            raise SystemExit(
                "--agent-jsonl (the subagent's .jsonl transcript under ~/.claude/projects/.../subagents/) "
                "is required for a Claude probe, to prove it ran on Opus 5"
            )
        jsonl_source = Path(args.agent_jsonl).resolve()
        if not jsonl_source.is_file() or jsonl_source.stat().st_size == 0:
            raise SystemExit(f"Missing or empty agent JSONL transcript: {jsonl_source}")
        models_served = served_models(jsonl_source)
        model_errors = claude_probe_model_errors(args.model, models_served)
        if model_errors:
            raise SystemExit("; ".join(model_errors))
    forbidden_launch = ("stb ", "terminus-2", "@openai/", "@anthropic/")
    launch_lower = args.launch_command.lower()
    if any(token in launch_lower for token in forbidden_launch):
        raise SystemExit("Harbor/stb LLM commands cannot be used as local solve evidence")

    probe_dir = run_dir.parent
    manifest = load_manifest(probe_dir)
    if not probe_dir_matches(manifest.get("task_slug", ""), run_dir.parent.name):
        raise SystemExit("Probe manifest/task directory mismatch")
    source_task = Path(manifest["source_task"]).resolve()
    if not source_task.is_dir():
        raise SystemExit(f"Source task no longer exists: {source_task}")
    if tree_hash(source_task, sanitized=True) != manifest.get("solver_contract_sha256"):
        raise SystemExit(
            "The instruction/environment contract changed after the solver saw it; "
            "discard this run and prepare a fresh probe"
        )

    diff_path = run_dir / "solve.diff"
    if not diff_path.is_file():
        raise SystemExit(f"Missing solver diff: {diff_path}")
    if args.result == "fail" and not diff_path.read_text(encoding="utf-8").strip():
        raise SystemExit("A failing semantic solve run must contain a non-empty solver diff")
    verifier_source = Path(args.verifier_log).resolve()
    ctrf_source = Path(args.verification_ctrf).resolve()
    transcript_source = Path(args.agent_transcript).resolve()
    if not verifier_source.is_file() or verifier_source.stat().st_size == 0:
        raise SystemExit(f"Missing or empty verifier log: {verifier_source}")
    if not transcript_source.is_file() or transcript_source.stat().st_size == 0:
        raise SystemExit(f"Missing or empty agent transcript: {transcript_source}")
    if not ctrf_source.is_file() or ctrf_source.stat().st_size == 0:
        raise SystemExit(f"Missing or empty verification CTRF: {ctrf_source}")
    matrix = matrix_from_ctrf(ctrf_source)
    if args.result == "pass" and matrix["failed_case_ids"]:
        raise SystemExit("A passing run cannot contain failed_case_ids")
    if args.result == "fail" and not matrix["failed_case_ids"]:
        raise SystemExit("A failing run must contain failed_case_ids")
    if args.result == "fail" and args.type == "semantic" and not args.notes.strip():
        raise SystemExit("Semantic failures require non-empty notes")

    verifier_path = run_dir / "verifier.log"
    matrix_path = run_dir / "case-matrix.json"
    ctrf_path = run_dir / "verification-ctrf.json"
    transcript_path = run_dir / "agent-transcript.md"
    if verifier_source != verifier_path:
        shutil.copy2(verifier_source, verifier_path)
    matrix_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if ctrf_source != ctrf_path:
        shutil.copy2(ctrf_source, ctrf_path)
    if transcript_source != transcript_path:
        shutil.copy2(transcript_source, transcript_path)
    jsonl_path = run_dir / "agent-transcript.jsonl"
    if jsonl_source is not None and jsonl_source != jsonl_path:
        shutil.copy2(jsonl_source, jsonl_path)

    result_path = run_dir / "result.json"
    data = {}
    if result_path.exists():
        data = json.loads(result_path.read_text(encoding="utf-8"))
    data.update(
        {
            "schema_version": 2,
            "task": manifest["task_slug"],
            "result": args.result,
            "failure_type": None if args.result == "pass" else args.type,
            "notes": args.notes,
            "evidence_complete": True,
            "agent": {
                "runner": args.runner,
                "runtime": args.runtime,
                "model": args.model,
                "served_models": sorted(set(models_served)),
                "reasoning_effort": args.reasoning_effort,
                "session_id": args.agent_session_id,
                "fresh_context": True,
                "launch_command": args.launch_command,
            },
            "verification": {
                "command": args.verification_command,
                "exit_code": args.verification_exit_code,
                "reward": args.reward,
                "task_snapshot_sha256": tree_hash(source_task, sanitized=False),
                "completed_at": utc_now(),
            },
            "artifacts": {
                "solve_diff": "solve.diff",
                "solve_diff_sha256": sha256(diff_path),
                "verifier_log": "verifier.log",
                "verifier_log_sha256": sha256(verifier_path),
                "case_matrix": "case-matrix.json",
                "case_matrix_sha256": sha256(matrix_path),
                "verification_ctrf": "verification-ctrf.json",
                "verification_ctrf_sha256": sha256(ctrf_path),
                "agent_transcript": "agent-transcript.md",
                "agent_transcript_sha256": sha256(transcript_path),
                **(
                    {
                        "agent_jsonl": "agent-transcript.jsonl",
                        "agent_jsonl_sha256": sha256(jsonl_path),
                    }
                    if jsonl_source is not None
                    else {}
                ),
            },
        }
    )
    result_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result_path)


def core_plus_recommendation(
    *, total: int, passed: int, evidence_complete: bool, failures: dict[str, int], mode: str
) -> str:
    if not evidence_complete:
        return "incomplete_evidence"
    if any(kind != "semantic" for kind in failures):
        return "fix_task_first"
    if mode != "counted":
        return "exploratory_only"
    if total != 2:
        return "unsupported_campaign_sample"
    if passed == 2:
        return "rework_or_replace"
    return "core_plus_shortlist"


def summarize(args: argparse.Namespace) -> None:
    probe_dir = Path(args.probe_dir).resolve()
    manifest = load_manifest(probe_dir)
    if manifest.get("schema_version") == 3 and manifest.get("profile") != args.profile:
        raise SystemExit(
            "Summary profile differs from probe preparation; prepare fresh runs for that profile"
        )
    records = []
    for result_path in sorted(probe_dir.glob("run_*/result.json")):
        records.append(json.loads(result_path.read_text(encoding="utf-8")))
    if not records:
        raise SystemExit(f"No result.json files found under {probe_dir}")
    total = len(records)
    passed = sum(1 for item in records if item.get("result") == "pass")
    evidence_complete = all(item.get("evidence_complete") is True for item in records)
    model_violations = []
    for item in records:
        agent = item.get("agent") or {}
        if agent.get("runtime") == "claude-code":
            served = agent.get("served_models")
            if not isinstance(served, list) or claude_probe_model_errors(str(agent.get("model", "")), served):
                model_violations.append(f"{item.get('task')}:{agent.get('session_id')}:{served}")
    if model_violations:
        evidence_complete = False
    failures: dict[str, int] = {}
    for item in records:
        if item.get("result") != "pass":
            failures[item.get("failure_type") or "unknown"] = failures.get(item.get("failure_type") or "unknown", 0) + 1
    case_sets: list[tuple[set[str], set[str]]] = []
    if evidence_complete:
        try:
            for result_path in sorted(probe_dir.glob("run_*/result.json")):
                matrix = validate_case_matrix(result_path.parent / "case-matrix.json")
                case_sets.append((set(matrix["passed_case_ids"]), set(matrix["failed_case_ids"])))
        except SystemExit:
            evidence_complete = False
    all_cases = set().union(*(passed_ids | failed_ids for passed_ids, failed_ids in case_sets)) if case_sets else set()
    union_passed = set().union(*(passed_ids for passed_ids, _ in case_sets)) if case_sets else set()
    common_misses = set.intersection(*(failed_ids for _, failed_ids in case_sets)) if case_sets else set()
    union_coverage = len(union_passed) / len(all_cases) if all_cases else 0.0
    semantic_failure_sets: list[frozenset[str]] = []
    semantic_decorrelated = False
    advanced_geometry_pass = False
    if manifest.get("mode") == "counted" and manifest.get("semantic_coverage"):
        node_map = semantic_node_map(Path(manifest["semantic_coverage"]).resolve())
        geometry = semantic_failure_geometry(case_sets, node_map, total, passed)
        semantic_failure_sets = geometry["failure_sets"]
        semantic_decorrelated = geometry["semantic_decorrelated"]
        advanced_geometry_pass = geometry["advanced_geometry_pass"]

    if not evidence_complete:
        recommendation = "incomplete_evidence"
    elif any(kind != "semantic" for kind in failures):
        recommendation = "fix_task_first"
    elif passed == total:
        recommendation = "rework_or_replace"
    else:
        # Only batch-handover.py can combine this evidence with the verifier
        # matrix and issue candidate_ready.
        recommendation = "needs_handover_validation"
    accuracy = passed / total
    tier_signal = (
        "frontier"
        if accuracy < 0.2
        else "advanced"
        if accuracy < 0.5
        else "core"
        if accuracy < 0.8
        else "base"
    )
    if args.profile in {"advanced_frontier_only", "core_advanced_frontier"}:
        recommendation = core_plus_recommendation(
            total=total,
            passed=passed,
            evidence_complete=evidence_complete,
            failures=failures,
            mode=str(manifest.get("mode", "legacy")),
        )
    summary = {
        "probe_dir": os.path.relpath(probe_dir),
        "runs": total,
        "passed": passed,
        "failed": total - passed,
        "failure_types": failures,
        "evidence_complete": evidence_complete,
        "claude_model_violations": model_violations,
        "union_coverage": union_coverage,
        "common_miss_count": len(common_misses),
        "local_accuracy": accuracy,
        "local_tier_signal": tier_signal,
        "profile": args.profile,
        "probe_mode": manifest.get("mode", "legacy"),
        "semantic_failure_sets": [sorted(nodes) for nodes in semantic_failure_sets],
        "semantic_failures_decorrelated": semantic_decorrelated,
        "advanced_geometry_pass": advanced_geometry_pass,
        "recommendation": recommendation,
    }
    out = probe_dir / "summary.md"
    out.write_text(
        "# Local Solve Probe Summary\n\n"
        f"- Runs: {total}\n"
        f"- Passed: {passed}\n"
        f"- Failed: {total - passed}\n"
        f"- Failure types: {json.dumps(failures, sort_keys=True)}\n"
        f"- Evidence complete: {evidence_complete}\n"
        f"- Claude runs not served by {PLATFORM_CLAUDE_PROBE_MODEL}: {len(model_violations)}\n"
        f"- Union coverage: {union_coverage:.6f}\n"
        f"- Common misses: {len(common_misses)}\n"
        f"- Local accuracy: {accuracy:.6f}\n"
        f"- Provisional tier signal: `{tier_signal}`\n"
        f"- Profile: `{args.profile}`\n"
        f"- Probe mode: `{manifest.get('mode', 'legacy')}`\n"
        f"- Semantic failures de-correlated: {semantic_decorrelated}\n"
        f"- Advanced geometry pass: {advanced_geometry_pass}\n"
        f"- Recommendation: `{recommendation}`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("task")
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--output")
    p.add_argument("--report-dir")
    p.add_argument("--exploratory", action="store_true")
    p.add_argument(
        "--profile",
        choices=("general", "advanced_frontier_only", "core_advanced_frontier"),
        default="general",
    )
    p.add_argument("--semantic-coverage")
    p.add_argument("--sufficiency")
    p.add_argument("--verifier-matrix")
    p.add_argument("--quota-run-override")
    p.set_defaults(func=prepare)

    p = sub.add_parser("diff")
    p.add_argument("run_dir")
    p.set_defaults(func=diff_run)

    p = sub.add_parser("materialize")
    p.add_argument("run_dir")
    p.set_defaults(func=materialize_run)

    p = sub.add_parser("record")
    p.add_argument("run_dir")
    p.add_argument("--result", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--notes", default="")
    p.add_argument("--runner", required=True)
    p.add_argument("--runtime", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--reasoning-effort", default="medium")
    p.add_argument("--agent-session-id", required=True)
    p.add_argument("--launch-command", required=True)
    p.add_argument("--verifier-log", required=True)
    p.add_argument("--verification-ctrf", required=True)
    p.add_argument("--agent-transcript", required=True)
    p.add_argument(
        "--agent-jsonl",
        help="Claude Code subagent .jsonl transcript; required for --runtime claude-code",
    )
    p.add_argument("--verification-command", required=True)
    p.add_argument("--verification-exit-code", type=int, required=True)
    p.add_argument("--reward", type=float, required=True)
    p.set_defaults(func=record)

    p = sub.add_parser("summarize")
    p.add_argument("probe_dir")
    p.add_argument(
        "--profile",
        choices=("general", "advanced_frontier_only", "core_advanced_frontier"),
        default="general",
    )
    p.set_defaults(func=summarize)

    args = parser.parse_args()
    if getattr(args, "runs", 1) < 1 or getattr(args, "runs", 1) > 5:
        raise SystemExit("--runs must be between 1 and 5")
    if (
        args.cmd == "prepare"
        and args.profile in {"advanced_frontier_only", "core_advanced_frontier"}
        and args.runs != 2
    ):
        raise SystemExit("CORE+ batch probes require exactly two blind-solver runs")
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
