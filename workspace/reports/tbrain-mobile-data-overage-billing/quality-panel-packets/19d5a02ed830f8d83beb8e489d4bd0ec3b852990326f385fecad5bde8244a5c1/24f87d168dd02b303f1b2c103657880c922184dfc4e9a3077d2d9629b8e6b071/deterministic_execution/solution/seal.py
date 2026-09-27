"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"usage", "statement"} object per line, the statement worked out by
solution/model.py, which never imports the package; NN is the reading order) and tests/expected/ROSTER (SHA-256,
file, row count), and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every account file
must keep within rule 1.2, and a line carrying a figure the tariff leaves to today's code (a FLEX line, or a
line not over its allowance) may appear only in a family that grades it.
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
CODE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def silent(entry):
    """The figures the tariff leaves to today's code that this line carries."""
    return model.silent(entry)


def within_limits(u):
    items = u["lines"]
    assert isinstance(u["account"], str) and 1 <= len(items) <= jobgen.MAX_LINES
    assert len({x["id"] for x in items}) == len(items)
    for x in items:
        assert 1 <= len(x["id"]) <= 10 and set(x["id"]) <= CODE, x["id"]
        assert x["plan"] in ("BASIC", "PLUS", "FLEX")
        assert isinstance(x["sessions"], list) and len(x["sessions"]) <= 60
        assert all(type(k) is int and 1 <= k <= 2000000 for k in x["sessions"]), x["id"]
        assert type(x["rate"]) is int and 1 <= x["rate"] <= 500
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
    for index, (family, files) in enumerate(jobgen.families().items()):
        rows = []
        for u in files:
            number += 1
            u["account"] = f"MD2-{number:04d}"
            within_limits(u)
            for x in u["lines"]:
                assert silent(x) <= jobgen.GRADES.get(family, set()), (family, x["id"])
            rows.append({"usage": u, "statement": model.statement(u)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/usagebill_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c}" for _d, n, c in roster))


if __name__ == "__main__":
    main()
