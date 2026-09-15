#!/usr/bin/env python3
"""Mechanical pre-flight for the platform instruction_check gate.

Usage:
    python3 instruction_preflight.py <instruction.md | task-folder>

Exit 0 = no structural findings. Exit 1 = findings listed; fix them BEFORE the
first platform check. This catches the MECHANICAL triggers only (structure,
length, hint phrases, leakage). Content judgment — algorithm narration,
mechanism/root-cause leaks, sufficiency of tested values — still needs a human
read against the Prompt Rules in SKILL.md.
"""

import pathlib
import re
import sys

HINT_PHRASES = [
    "pay particular attention",
    "pay attention",
    "note that",
    "make sure",
    "be careful",
    "easy to miss",
    "keep in mind",
    "study both",
    "tricky part",
    "common mistake",
    "bears emphasis",
    "a few points",
    "where a naive",
]

LEAK_WORDS = [
    "verifier",
    "test.sh",
    "test_outputs",
    "pytest",
    "hidden test",
    "rubric",
    "reward",
    "/tests/",
    "ctrf",
]

WORD_LIMIT = 300
MAX_FLAT_LIST_ITEMS = 20


def scan(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Fenced code blocks (worked I/O examples) are allowed — scan prose only.
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    findings: list[str] = []

    list_items: list[tuple[int, str]] = []
    for i, raw in enumerate(prose.splitlines(), 1):
        s = raw.strip()
        if re.match(r"^#{2,}\s", s):
            findings.append(f"line {i}: section header {s[:50]!r} — use flowing prose, no ##/### headers")
        list_match = re.match(r"^(\s*)(?:[-*+]|\d+[.)])\s", raw)
        if list_match:
            list_items.append((i, s))
            if list_match.group(1):
                findings.append(
                    f"line {i}: nested list item {s[:50]!r} — keep instruction lists flat"
                )
        if s.count("|") >= 3:
            findings.append(f"line {i}: table-like row {s[:50]!r} — tables always trip the check")

    if len(list_items) > MAX_FLAT_LIST_ITEMS:
        findings.append(
            f"{len(list_items)} bullet/numbered items — keep a flat list to at most "
            f"{MAX_FLAT_LIST_ITEMS} items"
        )

    words = len(prose.split())
    if words > WORD_LIMIT:
        findings.append(
            f"{words} words of prose (aim <= ~{WORD_LIMIT}) — trim, delegate rules to the "
            "named standard, or move reference data to an in-env file (disclosure ladder)"
        )

    low = prose.lower()
    for phrase in HINT_PHRASES:
        if phrase in low:
            findings.append(f'hint framing "{phrase}" — state the contract, never point at traps')
    for word in LEAK_WORDS:
        if word in low:
            findings.append(f'verifier/test leakage "{word}" — rename or remove (bare-word scanner also flags this)')

    if re.search(r"https?://github\.com/\S+/(?:pull|issues)/\d+", prose):
        findings.append("PR/issue URL in the prompt — remove")
    if "CANARY" in text:
        findings.append("canary string — remove")

    literal_density = len(re.findall(r"`[^`]+`", prose))
    if literal_density >= 15:
        findings.append(
            f"{literal_density} backtick literals — possible inline mapping chain/spec table; "
            "keep only family-covering facts or move examples to an in-env data file"
        )

    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = pathlib.Path(sys.argv[1])
    if path.is_dir():
        path = path / "instruction.md"
    if not path.is_file():
        print(f"not found: {path}")
        return 2

    findings = scan(path)
    if not findings:
        print(f"OK: {path} passes the mechanical instruction_check pre-flight")
        return 0
    print(f"{len(findings)} finding(s) in {path}:")
    for f in findings:
        print(f"- {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
