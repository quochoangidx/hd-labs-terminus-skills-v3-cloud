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

    assert MODULE.scan(instruction) == []


def test_rejects_more_than_twenty_list_items(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Update `/app/output.json`.\n\n"
        + "\n".join(f"- Requirement {index}." for index in range(1, 22))
        + "\n",
        encoding="utf-8",
    )

    findings = MODULE.scan(instruction)
    assert any("21 bullet/numbered items" in finding for finding in findings)


def test_rejects_nested_lists(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.md"
    instruction.write_text(
        "Update `/app/output.json`.\n\n- Preserve compatibility.\n  - Keep the legacy mode.\n",
        encoding="utf-8",
    )

    findings = MODULE.scan(instruction)
    assert any("nested list item" in finding for finding in findings)
