"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"loans", "statement"} object per line, the statement worked out by
solution/model.py, which never imports the package; NN is the reading order) and tests/expected/ROSTER (SHA-256,
file, row count), and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every return file
must keep within rule 1.2, and a loan carrying a figure the policy leaves to today's code (a journal, or a
loan that is not late) may appear only in a family that grades it.
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


def silent(loan):
    """The figures the policy leaves to today's code that this loan carries."""
    return model.silent(loan)


def within_limits(r):
    items = r["loans"]
    assert isinstance(r["branch"], str) and 1 <= len(items) <= jobgen.MAX_LOANS
    assert len({x["id"] for x in items}) == len(items)
    for x in items:
        assert 1 <= len(x["id"]) <= 10 and set(x["id"]) <= CODE, x["id"]
        assert x["kind"] in ("BOOK", "DVD", "JOURNAL")
        assert type(x["borrowed"]) is int and 0 <= x["borrowed"] <= 3650
        assert type(x["returned"]) is int and 0 <= x["returned"] - x["borrowed"] <= 180
        assert type(x["daily_fine"]) is int and 1 <= x["daily_fine"] <= 500
        assert type(x["replacement"]) is int and 100 <= x["replacement"] <= 20000
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
        for r in files:
            number += 1
            r["branch"] = f"LF5-{number:04d}"
            within_limits(r)
            for x in r["loans"]:
                assert silent(x) <= jobgen.GRADES.get(family, set()), (family, x["id"])
            rows.append({"loans": r, "statement": model.statement(r)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/finebook_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c}" for _d, n, c in roster))


if __name__ == "__main__":
    main()
