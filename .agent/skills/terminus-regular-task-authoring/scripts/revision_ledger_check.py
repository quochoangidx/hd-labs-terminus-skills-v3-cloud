#!/usr/bin/env python3
"""Check that a platform panel return was answered finding by finding, with evidence.

The build path runs on receipts: no gate result is reported unless a snapshot-bound
file shows it. The revision path has run on prose, which is where returns get answered
with "repaired" and come back with the same finding a round later.

This validates the ledger a revision writes:

- every numbered finding in the report has a decision and a reason;
- a finding answered by *backing* the promise carries two receipts — the defect
  reproduced on the snapshot the platform judged, and its closure on the snapshot
  being resubmitted. One without the other proves nothing: a reproduction alone
  shows the finding was real, a closure alone shows the current tree passes a test
  that may never have failed;
- a finding answered by *dropping* the promise names the obligation removed, so
  `panel_precheck.py` can confirm the prose went with it;
- a finding *disputed* cites the contract passage and a reproducible counterexample,
  because a dispute without both is an opinion;
- every finding either buys a permanent gate rule or records why the class cannot be
  mechanised — otherwise the return is paid for once and the lesson is lost;
- every earlier `P`-finding carried forward by the report gets an explicit response.

Usage:
    revision_ledger_check.py <task-folder> <revision-ledger.json>
        [--manifest <panel-precheck-manifest.json>] [--output <report.json>]

Exit 0 = the return is answered. Exit 1 = findings listed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
DECISIONS = {"backed", "dropped", "disputed", "acknowledged"}
AXES = {
    "coherent_contract",
    "correct_reference_solution",
    "protected_ground_truth",
    "sound_verifier",
    "deterministic_execution",
}
SEVERITIES = {"Major", "Minor", "Advisory", "Unsure"}
PREVIOUS_STATUSES = {"closed", "still_open", "not_a_defect", "mixed", "unanswered"}


def tree_hash(root: Path) -> str:
    """Must stay identical to panel_precheck.tree_hash, including the NUL separators."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in VOLATILE_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def nonempty(value: object) -> bool:
    """Non-empty, and not a skeleton placeholder left unfilled.

    `--init` writes REPLACE-prefixed values so the required fields are visible. They
    are non-empty strings, so without this they would satisfy every presence check
    and a ledger could pass while naming no report and no returned snapshot.
    """
    return isinstance(value, str) and bool(value.strip()) and not value.startswith("REPLACE")


def load_json(path: Path, label: str, errors: list[dict]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append({"code": "unreadable", "message": f"{label}: {exc}"})
        return {}
    if not isinstance(value, dict):
        errors.append({"code": "shape", "message": f"{label} must be a JSON object"})
        return {}
    return value


def check_receipt(
    ledger_dir: Path, ref: object, label: str, expect_snapshot: str | None, errors: list[dict]
) -> None:
    if not nonempty(ref):
        errors.append({"code": "missing_receipt", "message": f"{label} is required"})
        return
    path = (ledger_dir / str(ref)).resolve()
    if not path.is_file():
        errors.append({"code": "missing_receipt", "message": f"{label}: {ref} not found"})
        return
    receipt = load_json(path, label, errors)
    if not receipt:
        return
    if not nonempty(receipt.get("command")) or receipt.get("exit_code") is None:
        errors.append({"code": "unbacked_receipt", "message": f"{label} must record the command and its exit_code"})
    bound = receipt.get("task_snapshot_sha256")
    if expect_snapshot and bound != expect_snapshot:
        errors.append({
            "code": "stale_receipt",
            "message": f"{label} is bound to {str(bound)[:12]}… but the finding needs {expect_snapshot[:12]}…",
        })


def validate(task_dir: Path, ledger_path: Path, manifest_path: Path | None) -> dict:
    errors: list[dict] = []
    current = tree_hash(task_dir) if task_dir.is_dir() else None
    if not ledger_path.is_file():
        # Reporting six schema violations for one absent file buries the only fact
        # that matters and teaches authors to skim this output.
        return {
            "schema_version": 1,
            "task_slug": task_dir.name,
            "task_snapshot_sha256": current,
            "findings_answered": 0,
            "status": "fail",
            "blockers": [{
                "code": "no_ledger",
                "message": f"{ledger_path} does not exist. Start it with "
                f"`--init`, which records the current snapshot {str(current)[:12]}… as repaired_snapshot_sha256.",
            }],
        }
    ledger = load_json(ledger_path, ledger_path.name, errors)
    ledger_dir = ledger_path.parent

    if not task_dir.is_dir():
        errors.append({"code": "missing_task", "message": f"task folder not found: {task_dir}"})
    if ledger.get("schema_version") != 1:
        errors.append({"code": "schema", "message": "schema_version must be 1"})
    if ledger.get("task_slug") != task_dir.name:
        errors.append({"code": "slug", "message": "task_slug must match the task folder name"})
    if not nonempty(ledger.get("report_path")):
        errors.append({"code": "report", "message": "report_path must point at the retained platform report"})

    returned = ledger.get("returned_snapshot_sha256")
    repaired = ledger.get("repaired_snapshot_sha256")
    if not nonempty(returned):
        errors.append({
            "code": "returned_snapshot",
            "message": "returned_snapshot_sha256 is required: findings are about what the platform judged, "
            "not about a working tree that has drifted since",
        })
    if not nonempty(repaired):
        errors.append({"code": "repaired_snapshot", "message": "repaired_snapshot_sha256 is required"})
    elif current and repaired != current:
        errors.append({"code": "stale_ledger", "message": "repaired_snapshot_sha256 does not match the current task"})

    findings = ledger.get("findings")
    if not isinstance(findings, list) or not findings:
        errors.append({"code": "findings", "message": "findings must be a non-empty list, one row per numbered finding"})
        findings = []

    removed_ids: set[str] = set()
    manifest_loaded = False
    if manifest_path and manifest_path.is_file():
        manifest_loaded = True
        manifest = load_json(manifest_path, manifest_path.name, errors)
        removed = manifest.get("removed_obligations", [])
        if isinstance(removed, list):
            removed_ids = {str(r["id"]) for r in removed if isinstance(r, dict) and nonempty(r.get("id"))}

    seen: set[str] = set()
    for index, row in enumerate(findings):
        label = f"findings[{index}]"
        if not isinstance(row, dict) or not nonempty(row.get("id")):
            errors.append({"code": "finding", "message": f"{label} requires the id the report gives it"})
            continue
        fid = str(row["id"])
        label = f"finding {fid}"
        if fid in seen:
            errors.append({"code": "duplicate_finding", "message": f"{label} appears twice"})
        seen.add(fid)

        if row.get("axis") not in AXES:
            errors.append({"code": "axis", "message": f"{label}.axis must be one of {sorted(AXES)}"})
        if row.get("severity") not in SEVERITIES:
            errors.append({"code": "severity", "message": f"{label}.severity must be one of {sorted(SEVERITIES)}"})

        decision = row.get("decision")
        if decision not in DECISIONS:
            errors.append({"code": "decision", "message": f"{label}.decision must be one of {sorted(DECISIONS)}"})
            continue
        if not nonempty(row.get("rationale")):
            errors.append({"code": "rationale", "message": f"{label}.rationale must say why this answer, not the other"})

        blocking = row.get("blocking") is True
        if decision == "acknowledged" and blocking:
            errors.append({
                "code": "unanswered_blocker",
                "message": f"{label} is blocking; acknowledging it is not an answer. Back it, drop it, or dispute it.",
            })

        if decision == "backed":
            # Both halves are needed. A reproduction alone shows the finding was real;
            # a closure alone shows the current tree passes a test that may never have failed.
            check_receipt(ledger_dir, row.get("reproduction"), f"{label}.reproduction", returned if nonempty(returned) else None, errors)
            check_receipt(ledger_dir, row.get("closure"), f"{label}.closure", repaired if nonempty(repaired) else None, errors)
        elif decision == "dropped":
            dropped = row.get("removed_obligation_id")
            if not nonempty(dropped):
                errors.append({"code": "dropped_without_id", "message": f"{label} must name the obligation removed"})
            elif manifest_loaded and str(dropped) not in removed_ids:
                errors.append({
                    "code": "dropped_not_recorded",
                    "message": f"{label} drops {dropped}, which is absent from the manifest's removed_obligations; "
                    "the precheck cannot then confirm the promise left the prose too",
                })
        elif decision == "disputed":
            citation = row.get("contract_citation")
            if not isinstance(citation, dict) or not nonempty(citation.get("file")) or not nonempty(citation.get("anchor")):
                errors.append({"code": "dispute_without_citation", "message": f"{label} must cite the contract passage it relies on"})
            check_receipt(ledger_dir, row.get("counterexample"), f"{label}.counterexample", returned if nonempty(returned) else None, errors)

        # A return is expensive. Spend it once: turn the class into a rule, or say why
        # it resists mechanisation so the exposure is at least recorded.
        gate = row.get("gate")
        if not isinstance(gate, dict) or not (nonempty(gate.get("rule")) or nonempty(gate.get("not_mechanizable"))):
            errors.append({
                "code": "no_gate",
                "message": f"{label}.gate must name the rule this finding bought, or explain in "
                "not_mechanizable why the class cannot become one",
            })

    previous = ledger.get("previous_findings", [])
    if not isinstance(previous, list):
        errors.append({"code": "previous_findings", "message": "previous_findings must be a list"})
        previous = []
    for index, row in enumerate(previous):
        label = f"previous_findings[{index}]"
        if not isinstance(row, dict) or not nonempty(row.get("id")):
            errors.append({"code": "previous_finding", "message": f"{label} requires an id"})
            continue
        if row.get("status") not in PREVIOUS_STATUSES:
            errors.append({"code": "previous_status", "message": f"{label}.status must be one of {sorted(PREVIOUS_STATUSES)}"})
        if not nonempty(row.get("response")):
            errors.append({
                "code": "previous_unanswered",
                "message": f"{label} needs an explicit response; a carried-forward finding is not "
                "resolved by the report omitting it this round",
            })

    return {
        "schema_version": 1,
        "task_slug": task_dir.name,
        "task_snapshot_sha256": current,
        "findings_answered": len(seen),
        "status": "fail" if errors else "pass",
        "blockers": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--print-snapshot",
        action="store_true",
        help="print the task's snapshot hash and exit; run it on the restored returned "
        "artifact to obtain returned_snapshot_sha256",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="write a skeleton ledger bound to the current snapshot, then exit",
    )
    args = parser.parse_args()

    if not args.task_dir.is_dir():
        print(f"task folder not found: {args.task_dir}")
        return 2
    if args.print_snapshot:
        print(tree_hash(args.task_dir))
        return 0
    if args.init:
        if args.ledger.exists():
            print(f"{args.ledger} already exists; refusing to overwrite an answered return")
            return 2
        skeleton = {
            "schema_version": 1,
            "task_slug": args.task_dir.name,
            "report_path": "REPLACE-with-the-retained-platform-report",
            "returned_snapshot_sha256": "REPLACE-run --print-snapshot on the restored returned artifact",
            "repaired_snapshot_sha256": tree_hash(args.task_dir),
            "findings": [],
            "previous_findings": [],
        }
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        args.ledger.write_text(json.dumps(skeleton, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.ledger}; one row per numbered finding, then rerun without --init")
        return 0

    result = validate(args.task_dir, args.ledger, args.manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    for blocker in result["blockers"]:
        print(f"{blocker['code']:24} {blocker['message']}")
    if result["status"] == "pass":
        print(f"OK: {result['findings_answered']} finding(s) answered with snapshot-bound evidence")
        return 0
    print(f"\n{len(result['blockers'])} blocker(s); the return is not answered yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
