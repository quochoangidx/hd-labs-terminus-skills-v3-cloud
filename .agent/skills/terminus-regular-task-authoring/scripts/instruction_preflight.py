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

# Names and paths of the grading apparatus. These tell the agent where the answer key
# lives or how the score is computed, and no contract ever needs them.
LEAK_WORDS = [
    "test.sh",
    "test_outputs",
    "pytest",
    "hidden test",
    "rubric",
    "reward",
    "/tests/",
    "ctrf",
]

# Bare benchmark nouns. These are worth rewriting — say what is checked, not who checks
# it — but they can carry real contract: naming the harness is how a task states that a
# restriction is audited over compiled output as well as source. A task that cleared the
# platform panel does exactly that, so this is guidance, not a gate.
META_WORDS = ["verifier", "oracle"]

WORD_LIMIT = 300
MAX_FLAT_LIST_ITEMS = 20


def scan(path: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return (blocking, advisory).

    Blocking = a structural trigger the platform check actually rejects.
    Advisory = size/shape guidance. SKILL.md already treats paragraph, word and
    bullet counts as style guidance rather than standalone rejection reasons, so
    they must not fail the gate: a task whose contract genuinely needs the space
    (an in-env authority note plus closure and restriction clauses) is correct and
    long, and failing it here pushes an author to cut real contract.
    """
    text = path.read_text(encoding="utf-8")
    # Fenced code blocks (worked I/O examples) are allowed — scan prose only.
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    findings: list[str] = []
    advisory: list[str] = []

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
        advisory.append(
            f"{len(list_items)} bullet/numbered items — keep a flat list to at most "
            f"{MAX_FLAT_LIST_ITEMS} items"
        )

    words = len(prose.split())
    if words > WORD_LIMIT:
        advisory.append(
            f"{words} words of prose (aim <= ~{WORD_LIMIT}) — trim, delegate rules to the "
            "named standard, or move reference data to an in-env file (disclosure ladder). "
            "Keep the length if it is carrying contract: closure clauses, a restriction "
            "whitelist with its allowed exceptions, or a coverage envelope."
        )

    low = prose.lower()
    for phrase in HINT_PHRASES:
        if phrase in low:
            findings.append(f'hint framing "{phrase}" — state the contract, never point at traps')
    for word in LEAK_WORDS:
        if word in low:
            findings.append(
                f'grading-apparatus leakage "{word}" — rename or remove; the contract never '
                "needs the harness's own paths or scoring names"
            )
    for word in META_WORDS:
        if word in low:
            advisory.append(
                f'benchmark noun "{word}" — prefer naming the requirement over the harness '
                '("compiled references are checked as well as source"). Keep it if removing '
                "it would cost a real restriction; this is repo style, not a platform gate."
            )

    if re.search(r"https?://github\.com/\S+/(?:pull|issues)/\d+", prose):
        findings.append("PR/issue URL in the prompt — remove")
    if "CANARY" in text:
        findings.append("canary string — remove")

    literal_density = len(re.findall(r"`[^`]+`", prose))
    if literal_density >= 15:
        advisory.append(
            f"{literal_density} backtick literals — possible inline mapping chain/spec table; "
            "keep only family-covering facts or move examples to an in-env data file. "
            "A namespace whitelist or a named-exclusion list is contract, not a spec table."
        )

    return findings, advisory


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

    findings, advisory = scan(path)
    if advisory:
        print(f"{len(advisory)} advisory note(s) in {path} — judgement, not a gate:")
        for a in advisory:
            print(f"~ {a}")
    if not findings:
        print(f"OK: {path} passes the mechanical instruction_check pre-flight")
        return 0
    print(f"{len(findings)} blocking finding(s) in {path}:")
    for f in findings:
        print(f"- {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
