"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"sheet", "report"} object per line, the report worked out by
solution/model.py, which never imports the package; NN is the reading order) and tests/expected/ROSTER (SHA-256,
file, row count), and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every sheet
must keep within rule 1.3, and a line of a class other than A, B or C may appear only in a family that grades it.
"""

import hashlib
import json
import shutil
from pathlib import Path

import jobgen
import model

TASK = Path(__file__).resolve().parent.parent
EXPECTED = TASK / "tests" / "expected"
SHIPPED = TASK / "tests" / "shipped" / "app"
CODE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def within_limits(s):
    lines = s["lines"]
    assert isinstance(s["sheet"], str) and 1 <= len(lines) <= jobgen.MAX_LINES
    assert len({x["sku"] for x in lines}) == len(lines)
    for x in lines:
        assert 1 <= len(x["sku"]) <= 12 and set(x["sku"]) <= CODE, x["sku"]
        assert len(x["class"]) == 1 and x["class"].isupper() and x["class"].isascii()
        for k in ("system", "count"):
            assert type(x[k]) is int and 0 <= x[k] <= 100000
        assert x["recount"] is None or (type(x["recount"]) is int and 0 <= x["recount"] <= 100000)
        assert type(x["unit_cost"]) is int and 1 <= x["unit_cost"] <= 1000000
    return True


def write(name, rows):
    text = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows)
    (EXPECTED / name).write_text(text)
    return hashlib.sha256(text.encode()).hexdigest(), name, len(rows)


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster, number = [], 0
    for index, (family, sheets) in enumerate(jobgen.families().items()):
        rows = []
        for s in sheets:
            number += 1
            s["sheet"] = f"CC2-{number:04d}"
            within_limits(s)
            other = any(x["class"] not in "ABC" for x in s["lines"])
            assert not other or "other_class" in jobgen.GRADES.get(family, set()), (family, number)
            rows.append({"sheet": s, "report": model.report(s)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/cyclecount_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c}" for _d, n, c in roster))


if __name__ == "__main__":
    main()
