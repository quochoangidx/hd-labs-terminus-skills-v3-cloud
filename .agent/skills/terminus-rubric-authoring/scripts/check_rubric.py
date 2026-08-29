#!/usr/bin/env python3
"""Check Terminus rubric mechanics and flag repeated authoring topology."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ALLOWED_SCORES = {-5, -3, -2, -1, 1, 2, 3, 5}
SCORE_RE = re.compile(r", ([+-][1235])$")
LEAK_RE = re.compile(
    r"\b(?:tests?|verifier|grader|pytest|reward|hidden checks?|ci)\b|/tests/",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^#\s+Rubrics\s*$", re.IGNORECASE)
NEXT_HEADING_RE = re.compile(r"^#\s+")
BLOCKED_COVERAGE_RE = re.compile(r"\|\s*(?:partial|uncovered)\s*\|", re.IGNORECASE)
REQUIRED_MATRIX_COLUMNS = (
    "contract_id",
    "source",
    "observable_requirement",
    "witness_ids",
    "discrimination",
    "coverage",
    "criterion_id",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_rubric(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next((index + 1 for index, line in enumerate(lines) if HEADING_RE.match(line)), None)
    if start is None:
        return []
    output: list[str] = []
    for line in lines[start:]:
        if NEXT_HEADING_RE.match(line):
            break
        if line.strip():
            output.append(line)
    return output


def inspect(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    criteria = extract_rubric(path)
    if not criteria:
        errors.append("missing or empty '# Rubrics' section")
    scores: list[int] = []
    verbs: list[str] = []
    negative_lines: list[str] = []
    for number, line in enumerate(criteria, start=1):
        if not line.startswith("Agent "):
            errors.append(f"criterion {number} must start with 'Agent '")
        match = SCORE_RE.search(line)
        if not match:
            errors.append(f"criterion {number} must end with a signed allowed score")
            continue
        score = int(match.group(1))
        if score not in ALLOWED_SCORES:
            errors.append(f"criterion {number} uses unsupported score {score:+d}")
        scores.append(score)
        if score < 0:
            negative_lines.append(line)
        if LEAK_RE.search(line):
            errors.append(f"criterion {number} contains evaluation leakage vocabulary")
        words = line.split()
        if len(words) > 1:
            verbs.append(words[1].lower())

    positive_total = sum(score for score in scores if score > 0)
    if criteria and not 10 <= positive_total <= 40:
        errors.append(f"positive score total must be 10-40, got {positive_total}")
    if criteria and not negative_lines:
        errors.append("at least one negative criterion is required")

    for line in negative_lines:
        body = SCORE_RE.sub("", line)
        disjunctions = len(re.findall(r"\bor\b", body, flags=re.IGNORECASE))
        comma_clauses = body.count(",")
        if disjunctions >= 3 or (disjunctions >= 2 and comma_clauses >= 1):
            warnings.append("one negative criterion combines three or more failure clauses")
            break
    if verbs:
        most_common = max(verbs.count(verb) for verb in set(verbs))
        if len(verbs) >= 6 and most_common / len(verbs) >= 0.6:
            warnings.append("criterion lead verbs are highly repetitive")

    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "status": "fail" if errors else "pass",
        "criterion_count": len(criteria),
        "positive_count": sum(score > 0 for score in scores),
        "negative_count": sum(score < 0 for score in scores),
        "positive_total": positive_total,
        "scores": scores,
        "verbs": verbs,
        "errors": errors,
        "warnings": warnings,
    }


def inspect_coverage_matrix(path: Path | None) -> dict[str, object]:
    if path is None:
        return {
            "path": None,
            "sha256": None,
            "status": "not_checked",
            "errors": [],
        }
    resolved = path.resolve()
    errors: list[str] = []
    if not path.is_file():
        errors.append("coverage matrix does not exist")
        return {
            "path": str(resolved),
            "sha256": None,
            "status": "fail",
            "errors": errors,
        }
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        errors.append("coverage matrix is empty")
    lines = text.splitlines()
    header_index = None
    header: list[str] = []
    for index, line in enumerate(lines):
        cells = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
        if set(REQUIRED_MATRIX_COLUMNS).issubset(cells):
            header_index = index
            header = cells
            break
    if header_index is None:
        errors.append("coverage matrix is missing the required contract-witness columns")
    else:
        rows: list[dict[str, str]] = []
        for line in lines[header_index + 2 :]:
            if not line.strip().startswith("|"):
                break
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != len(header):
                errors.append("coverage matrix contains a malformed data row")
                continue
            rows.append(dict(zip(header, cells, strict=True)))
        if not rows:
            errors.append("coverage matrix has no contract rows")
        for row in rows:
            contract_id = row.get("contract_id") or "<blank>"
            missing = [column for column in REQUIRED_MATRIX_COLUMNS if not row.get(column)]
            if missing:
                errors.append(
                    f"coverage row {contract_id} has empty required fields: {', '.join(missing)}"
                )
            if row.get("coverage", "").lower() != "covered":
                errors.append(f"coverage row {contract_id} is not covered")
    if BLOCKED_COVERAGE_RE.search(text) and not any("is not covered" in item for item in errors):
        errors.append("coverage matrix contains partial or uncovered contract rows")
    return {
        "path": str(resolved),
        "sha256": sha256(path),
        "status": "fail" if errors else "pass",
        "errors": errors,
    }


def portfolio_warnings(results: list[dict[str, object]]) -> list[str]:
    if len(results) < 3:
        return []
    warnings: list[str] = []
    signatures = [
        (
            result["positive_count"],
            result["negative_count"],
            tuple(result["scores"]),
        )
        for result in results
    ]
    if len(set(signatures)) == 1:
        warnings.append("all packets share the same positive/negative count and score sequence")
    if all(result["negative_count"] == 1 and result["scores"][-1:] == [-5] for result in results):
        warnings.append("all packets end in the same single -5 negative topology")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packets", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--coverage-matrix", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for path in args.packets:
        if not path.is_file():
            results.append(
                {
                    "path": str(path),
                    "sha256": None,
                    "status": "fail",
                    "criterion_count": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "positive_total": 0,
                    "scores": [],
                    "verbs": [],
                    "errors": ["file does not exist"],
                    "warnings": [],
                }
            )
        else:
            results.append(inspect(path))
    portfolio = portfolio_warnings(results)
    coverage = inspect_coverage_matrix(args.coverage_matrix)
    failed = any(result["status"] == "fail" for result in results) or coverage["status"] == "fail"
    receipt = {
        "schema_version": 1,
        "status": "fail" if failed else "pass",
        "results": results,
        "portfolio_warnings": portfolio,
        "coverage_matrix": coverage,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(receipt, indent=2))
    else:
        for result in results:
            print(
                f"{result['path']}: {result['status']} "
                f"({result['positive_count']} positive / {result['negative_count']} negative; "
                f"positive total {result['positive_total']})"
            )
            for error in result["errors"]:
                print(f"  ERROR: {error}")
            for warning in result["warnings"]:
                print(f"  WARN: {warning}")
        for warning in portfolio:
            print(f"PORTFOLIO WARN: {warning}")
        for error in coverage["errors"]:
            print(f"COVERAGE ERROR: {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
