#!/usr/bin/env python3
"""Validate the local Task Instruction Sufficiency evidence manifest."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import sys
from pathlib import Path


SOURCE_TYPES = {
    "instruction",
    "environment_reference",
    "reachable_authority",
    "visible_training_data",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def static_test_names(task_dir: Path) -> set[str]:
    names: set[str] = set()
    for path in (task_dir / "tests").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                names.add(node.name)
    return names


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(task_dir: Path, report_path: Path) -> list[str]:
    errors: list[str] = []
    if not task_dir.is_dir():
        return [f"task folder not found: {task_dir}"]
    if not report_path.is_file():
        return [f"sufficiency report not found: {report_path}"]
    instruction_path = task_dir / "instruction.md"
    if not instruction_path.is_file():
        return [f"instruction not found: {instruction_path}"]
    instruction = instruction_path.read_text(encoding="utf-8")
    try:
        report_path.resolve().relative_to(task_dir.resolve())
    except ValueError:
        pass
    else:
        fail(errors, "sufficiency report must stay outside the task folder and ZIP")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid JSON: {exc}"]

    if report.get("task") != task_dir.name:
        fail(errors, f"task must equal {task_dir.name!r}")
    if report.get("verdict") != "pass":
        fail(errors, "verdict must be 'pass'")

    policy = report.get("hidden_case_policy")
    expected_policy = {
        "hidden_inputs": True,
        "hidden_expected_outputs": True,
        "hidden_contract_rules": False,
    }
    if policy != expected_policy:
        fail(errors, f"hidden_case_policy must equal {expected_policy}")

    source_rows = report.get("contract_source_files")
    source_hashes: dict[str, str] = {}
    if not isinstance(source_rows, list) or not source_rows:
        fail(errors, "contract_source_files must be a non-empty list")
        source_rows = []
    for index, item in enumerate(source_rows):
        label = f"contract_source_files[{index}]"
        if not isinstance(item, dict):
            fail(errors, f"{label} must be an object")
            continue
        rel = item.get("path")
        expected_hash = item.get("sha256")
        if not nonempty_string(rel):
            fail(errors, f"{label}.path must be a non-empty string")
            continue
        rel = str(rel)
        if rel in source_hashes:
            fail(errors, f"duplicate contract source path: {rel}")
            continue
        source_path = (task_dir / rel).resolve()
        try:
            source_path.relative_to(task_dir.resolve())
        except ValueError:
            fail(errors, f"{label}.path escapes the task folder: {rel}")
            continue
        if not source_path.is_file():
            fail(errors, f"{label}.path does not exist: {rel}")
            continue
        actual_hash = sha256(source_path)
        source_hashes[rel] = actual_hash
        if expected_hash != actual_hash:
            fail(errors, f"{label}.sha256 does not match current {rel}")
    if "instruction.md" not in source_hashes:
        fail(errors, "contract_source_files must include instruction.md")

    rows = report.get("contract_rows")
    if not isinstance(rows, list) or not rows:
        fail(errors, "contract_rows must be a non-empty list")
        rows = []

    row_ids: set[str] = set()
    row_locators: dict[str, str] = {}
    selectors: list[str] = []
    referenced_source_files = {"instruction.md"}
    for index, row in enumerate(rows):
        label = f"contract_rows[{index}]"
        if not isinstance(row, dict):
            fail(errors, f"{label} must be an object")
            continue
        row_id = row.get("id")
        if not nonempty_string(row_id):
            fail(errors, f"{label}.id must be a non-empty string")
        elif row_id in row_ids:
            fail(errors, f"duplicate contract id: {row_id}")
        else:
            row_ids.add(row_id)
        for field in ("asserted_behavior", "source_locator", "reasonable_alternative"):
            if not nonempty_string(row.get(field)):
                fail(errors, f"{label}.{field} must be a non-empty string")
        tests = row.get("test_selectors")
        if not isinstance(tests, list) or not tests or not all(nonempty_string(x) for x in tests):
            fail(errors, f"{label}.test_selectors must contain one or more names/globs")
        else:
            selectors.extend(tests)
        source_type = row.get("source_type")
        if source_type not in SOURCE_TYPES:
            fail(errors, f"{label}.source_type must be one of {sorted(SOURCE_TYPES)}")
        if row.get("visible_contract_rejects_alternative") is not True:
            fail(errors, f"{label} does not prove that the visible contract rejects its reasonable alternative")

        locator = row.get("source_locator", "")
        if nonempty_string(row_id) and nonempty_string(locator):
            row_locators[str(row_id)] = str(locator)
        if source_type == "instruction" and not str(locator).startswith("instruction.md:"):
            fail(errors, f"{label} instruction source_locator must start with 'instruction.md:'")
        elif source_type == "instruction":
            anchor = str(locator).split(":", 1)[1].strip()
            if not anchor or anchor not in instruction:
                fail(errors, f"{label} instruction anchor is not present verbatim: {anchor!r}")
        elif source_type == "environment_reference":
            rel = str(locator).split(":", 1)[0]
            if not rel.startswith("environment/") or not (task_dir / rel).is_file():
                fail(errors, f"{label} environment reference does not exist: {rel}")
            else:
                referenced_source_files.add(rel)
        elif source_type == "reachable_authority":
            if row.get("offline_reachable") is not True or not nonempty_string(row.get("authority_command")):
                fail(errors, f"{label} reachable authority needs offline_reachable=true and authority_command")
        elif source_type == "visible_training_data":
            support = row.get("support")
            if not isinstance(support, dict):
                fail(errors, f"{label}.support must be an object for visible_training_data")
                continue
            training_path = support.get("training_path")
            if not nonempty_string(training_path) or not (task_dir / str(training_path)).is_file():
                fail(errors, f"{label} visible training path does not exist: {training_path}")
            else:
                referenced_source_files.add(str(training_path))
            for field in ("positive_examples", "contrast_examples"):
                value = support.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 2:
                    fail(errors, f"{label}.support.{field} must be an integer >= 2")
            if support.get("hidden_only_feature_values") != []:
                fail(errors, f"{label}.support.hidden_only_feature_values must be []")

    static_tests = static_test_names(task_dir)
    uncovered = sorted(
        name for name in static_tests if not any(fnmatch.fnmatchcase(name, selector) for selector in selectors)
    )
    if uncovered:
        fail(errors, "static pytest functions missing from contract rows: " + ", ".join(uncovered))
    missing_sources = sorted(referenced_source_files - set(source_hashes))
    if missing_sources:
        fail(
            errors,
            "contract_source_files missing referenced visible sources: "
            + ", ".join(missing_sources),
        )

    review = report.get("blind_contract_review")
    if not isinstance(review, dict):
        fail(errors, "blind_contract_review must be an object")
        return errors
    reviewer_count = review.get("reviewer_count")
    if not isinstance(reviewer_count, int) or isinstance(reviewer_count, bool) or reviewer_count < 2:
        fail(errors, "blind_contract_review.reviewer_count must be >= 2")
    if review.get("contract_inventory_complete") is not True:
        fail(errors, "blind_contract_review.contract_inventory_complete must be true")
    reviewers = review.get("reviewers")
    if not isinstance(reviewers, list) or len(reviewers) < 2:
        fail(errors, "blind_contract_review.reviewers must contain at least two evidence records")
        reviewers = []
    if isinstance(reviewer_count, int) and not isinstance(reviewer_count, bool):
        if reviewer_count != len(reviewers):
            fail(errors, "blind_contract_review.reviewer_count must equal len(reviewers)")
    reviewer_ids: set[str] = set()
    reviewer_sessions: set[str] = set()
    report_dir = report_path.resolve().parent
    expected_reviewed_sources = sorted(source_hashes)
    for index, reviewer in enumerate(reviewers):
        label = f"blind_contract_review.reviewers[{index}]"
        if not isinstance(reviewer, dict):
            fail(errors, f"{label} must be an object")
            continue
        for field in ("reviewer_id", "runtime", "model", "session_id", "transcript"):
            if not nonempty_string(reviewer.get(field)):
                fail(errors, f"{label}.{field} must be a non-empty string")
        reviewer_id = reviewer.get("reviewer_id")
        session_id = reviewer.get("session_id")
        if nonempty_string(reviewer_id):
            if str(reviewer_id) in reviewer_ids:
                fail(errors, f"{label}.reviewer_id must be unique")
            reviewer_ids.add(str(reviewer_id))
        if nonempty_string(session_id):
            if str(session_id) in reviewer_sessions:
                fail(errors, f"{label}.session_id must be unique")
            reviewer_sessions.add(str(session_id))
        if reviewer.get("fresh_context") is not True:
            fail(errors, f"{label}.fresh_context must be true")
        if reviewer.get("source_only") is not True:
            fail(errors, f"{label}.source_only must be true")
        if reviewer.get("reviewed_source_files") != expected_reviewed_sources:
            fail(
                errors,
                f"{label}.reviewed_source_files must equal the hash-bound contract source list",
            )
        transcript_value = reviewer.get("transcript")
        if nonempty_string(transcript_value):
            transcript = (report_dir / str(transcript_value)).resolve()
            try:
                transcript.relative_to(report_dir)
            except ValueError:
                fail(errors, f"{label}.transcript escapes the report directory")
            else:
                if not transcript.is_file() or transcript.stat().st_size == 0:
                    fail(errors, f"{label}.transcript is missing or empty")
                elif reviewer.get("transcript_sha256") != sha256(transcript):
                    fail(errors, f"{label}.transcript_sha256 mismatch")
    questions = review.get("questions")
    if not isinstance(questions, list) or not questions:
        fail(errors, "blind_contract_review.questions must be a non-empty list")
        questions = []
    reviewed_ids: set[str] = set()
    for index, question in enumerate(questions):
        label = f"blind_contract_review.questions[{index}]"
        if not isinstance(question, dict):
            fail(errors, f"{label} must be an object")
            continue
        for field in ("id", "question", "source_locator"):
            if not nonempty_string(question.get(field)):
                fail(errors, f"{label}.{field} must be a non-empty string")
        contract_ids = question.get("contract_ids")
        if not isinstance(contract_ids, list) or not contract_ids:
            fail(errors, f"{label}.contract_ids must be a non-empty list")
        else:
            unknown = set(contract_ids) - row_ids
            if unknown:
                fail(errors, f"{label} references unknown contract ids: {sorted(unknown)}")
            reviewed_ids.update(contract_ids)
            source_locator = question.get("source_locator")
            expected_locators = {row_locators.get(contract_id) for contract_id in contract_ids}
            if source_locator not in expected_locators:
                fail(errors, f"{label}.source_locator must match one of its contract-row locators")
        if question.get("answers_agree") is not True:
            fail(errors, f"{label} blind reviewers did not agree")
        if question.get("matches_oracle") is not True:
            fail(errors, f"{label} blind answer does not match the oracle")
    missing_review = sorted(row_ids - reviewed_ids)
    if missing_review:
        fail(errors, "contract rows missing blind-review coverage: " + ", ".join(missing_review))
    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {Path(sys.argv[0]).name} <task-dir> <instruction-sufficiency.json>")
        return 2
    task_dir = Path(sys.argv[1])
    report_path = Path(sys.argv[2])
    errors = validate(task_dir, report_path)
    if errors:
        print(f"FAIL: {len(errors)} instruction-sufficiency finding(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {task_dir.name} has complete instruction-sufficiency evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
