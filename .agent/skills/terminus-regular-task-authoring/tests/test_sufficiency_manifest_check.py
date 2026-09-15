from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "sufficiency_manifest_check.py"
SPEC = importlib.util.spec_from_file_location("sufficiency_manifest_check", SCRIPT)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_v3_fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    task = tmp_path / "tbrain-evidence-example"
    evidence = task / "environment" / "evidence.txt"
    tests = task / "tests" / "test_outputs.py"
    evidence.parent.mkdir(parents=True)
    tests.parent.mkdir(parents=True)
    instruction = task / "instruction.md"
    instruction.write_text("Recover the session and write /app/result.json.\n")
    evidence.write_text("frame=7 counter=3\nframe=9 counter=4\n")
    tests.write_text(
        "def test_schema():\n    pass\n\n"
        "def test_session_sequence():\n    pass\n"
    )

    report_dir = tmp_path / "reports" / task.name
    report_dir.mkdir(parents=True)
    transcript_hashes = []
    for name in ("fairness-1.md", "fairness-2.md"):
        transcript = report_dir / name
        transcript.write_text("Goal clear; evidence supports counter progression.\n")
        transcript_hashes.append(digest(transcript))

    sources = [
        {"path": "instruction.md", "sha256": digest(instruction)},
        {"path": "environment/evidence.txt", "sha256": digest(evidence)},
    ]
    reviewed_sources = ["environment/evidence.txt", "instruction.md"]
    report = {
        "schema_version": 3,
        "task": task.name,
        "verdict": "pass",
        "contract_source_files": sources,
        "explicit_contract": [
            {
                "id": "result_path",
                "requirement": "Write /app/result.json.",
                "test_selectors": ["test_schema"],
                "source_locator": "instruction.md:/app/result.json",
            }
        ],
        "inference_families": [
            {
                "id": "counter_progression",
                "inferred_model": "Session counters advance across frames.",
                "test_selectors": ["test_session_*"],
                "evidence_sources": [
                    {
                        "path": "environment/evidence.txt",
                        "locator": "frame records",
                        "role": "observed state sequence",
                    }
                ],
                "reasoning_chain": "The paired records expose the progression.",
                "competing_interpretation": "Each frame resets the counter.",
                "evidence_discriminator": "The second record continues from the first.",
                "hidden_generalization": ["new_instances", "new_combinations"],
            }
        ],
        "unobtainable_knowledge": {
            "oracle_only_policies": [],
            "unreachable_authorities": [],
            "undocumented_exact_values": [],
        },
        "oracle_alignment": {
            "oracle_is_valid_realization": True,
            "verifier_accepts_semantic_equivalents": True,
            "equivalence_notes": "The result path is fixed; implementation is free.",
        },
        "fairness_review": {
            "reviewer_count": 2,
            "reviewers": [
                {
                    "reviewer_id": f"reviewer-{index + 1}",
                    "runtime": "test",
                    "model": "test-model",
                    "session_id": f"session-{index + 1}",
                    "fresh_context": True,
                    "task_visible_only": True,
                    "reviewed_source_files": reviewed_sources,
                    "transcript": f"fairness-{index + 1}.md",
                    "transcript_sha256": transcript_hashes[index],
                }
                for index in range(2)
            ],
            "questions": [
                {
                    "id": "counter_inferability",
                    "family_ids": ["counter_progression"],
                    "question": "Can the progression be inferred?",
                    "inferability_supported": True,
                    "unresolved_goal_ambiguity": False,
                    "unobtainable_knowledge_required": False,
                    "evidence_locators": ["environment/evidence.txt"],
                }
            ],
        },
    }
    report_path = report_dir / "instruction-sufficiency.json"
    report_path.write_text(json.dumps(report))
    return task, report_path, report


def test_v3_allows_multi_source_style_inference_and_hidden_variations(tmp_path: Path) -> None:
    task, report_path, _ = build_v3_fixture(tmp_path)
    assert CHECKER.validate_v3(task, report_path) == []


def test_v3_accepts_single_reviewer_two_pass_policy(tmp_path: Path) -> None:
    task, report_path, report = build_v3_fixture(tmp_path)
    reviewer = report["fairness_review"]["reviewers"][0]
    reviewer["review_passes"] = [
        {"phase": "contract_review"},
        {"phase": "final_review"},
    ]
    report["fairness_review"].update({
        "review_policy": "single_reviewer_two_pass_v1",
        "reviewer_count": 1,
        "reviewers": [reviewer],
    })
    report_path.write_text(json.dumps(report))
    assert CHECKER.validate_v3(task, report_path) == []


def test_v3_rejects_oracle_only_policy(tmp_path: Path) -> None:
    task, report_path, report = build_v3_fixture(tmp_path)
    report["unobtainable_knowledge"]["oracle_only_policies"] = ["secret tie-break"]
    report_path.write_text(json.dumps(report))
    errors = CHECKER.validate_v3(task, report_path)
    assert any("oracle_only_policies must be []" in error for error in errors)


def test_v3_rejects_unmapped_static_test(tmp_path: Path) -> None:
    task, report_path, _ = build_v3_fixture(tmp_path)
    with (task / "tests" / "test_outputs.py").open("a") as stream:
        stream.write("\ndef test_unmapped():\n    pass\n")
    errors = CHECKER.validate_v3(task, report_path)
    assert any("test_unmapped" in error for error in errors)
