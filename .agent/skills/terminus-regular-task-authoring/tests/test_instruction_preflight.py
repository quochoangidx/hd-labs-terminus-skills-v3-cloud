from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "instruction_preflight.py"
SPEC = importlib.util.spec_from_file_location("instruction_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_accepts_flat_requirement_list_up_to_twenty_items(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Update `/app/output.json` so it satisfies these requirements.\n\n"
        + "\n".join(f"- Preserve behavior {index}." for index in range(1, 21))
        + "\n",
        encoding="utf-8",
    )

    assert MODULE.scan(instruction) == ([], [])


def test_more_than_twenty_list_items_is_advisory_not_blocking(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Update `/app/output.json`.\n\n"
        + "\n".join(f"- Requirement {index}." for index in range(1, 22))
        + "\n",
        encoding="utf-8",
    )

    findings, advisory = MODULE.scan(instruction)
    assert any("21 bullet/numbered items" in note for note in advisory)
    assert findings == []


def test_long_contract_carrying_prose_is_advisory_not_blocking(tmp_path: Path) -> None:
    """A closure clause plus a restriction whitelist legitimately runs long.

    Failing such an instruction pushes the author to cut real contract, which is the
    opposite of what the gate is for.
    """
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Fix the package under `/app/src` so it matches `/app/NOTE.md`. "
        + "Where the note gives a rule it holds for every argument; where it gives none "
        + "the package already answers correctly. "
        + " ".join(f"Boundary clause {index} stays observable." for index in range(1, 120))
        + "\n",
        encoding="utf-8",
    )

    findings, advisory = MODULE.scan(instruction)
    assert any("words of prose" in note for note in advisory)
    assert findings == []


def test_rejects_nested_lists(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Update `/app/output.json`.\n\n- Preserve compatibility.\n  - Keep the legacy mode.\n",
        encoding="utf-8",
    )

    findings, _advisory = MODULE.scan(instruction)
    assert any("nested list item" in finding for finding in findings)


def test_naming_the_harness_is_advisory_not_blocking(tmp_path: Path) -> None:
    """A panel-cleared task names the verifier to scope a restriction it audits.

    Blocking the bare noun would have an author cut a real contract sentence.
    """
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Fix the package under `/app/src`. Package declarations and explicit type "
        "references stay inside the listed namespaces; the verifier reads compiled "
        "references as well as source.\n",
        encoding="utf-8",
    )

    findings, advisory = MODULE.scan(instruction)

    assert findings == []
    assert any('benchmark noun "verifier"' in note for note in advisory)


def test_grading_apparatus_paths_still_block(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Fix the package so the checks in `/tests/` pass and the rubric scores it.\n",
        encoding="utf-8",
    )

    findings, _advisory = MODULE.scan(instruction)

    assert any("/tests/" in finding for finding in findings)
    assert any("rubric" in finding for finding in findings)
