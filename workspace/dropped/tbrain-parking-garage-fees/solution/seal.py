"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"sessions", "statement"} object per line, the statement worked out by
solution/model.py, which never imports the package; NN is the reading order) and tests/expected/ROSTER (SHA-256,
file, row count), and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every exits file
must keep within rule 1.2, and a session carrying a figure the tariff leaves to today's code (a validated
ticket whose amount due goes below nought, or a motorcycle past the car-and-van maximum) may appear only in a family that grades it.
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


def silent(session):
    """The figures the tariff leaves to today's code that this session carries."""
    return model.silent(session)


def within_limits(e):
    items = e["sessions"]
    assert isinstance(e["garage"], str) and 1 <= len(items) <= jobgen.MAX_SESSIONS
    assert len({x["id"] for x in items}) == len(items)
    for x in items:
        assert 1 <= len(x["id"]) <= 10 and set(x["id"]) <= CODE, x["id"]
        assert x["vehicle"] in ("CAR", "VAN", "MOTO")
        assert type(x["entry"]) is int and 0 <= x["entry"] <= 100000
        assert type(x["exit"]) is int and 0 <= x["exit"] - x["entry"] <= 10080
        assert type(x["validated"]) is bool
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
        for e in files:
            number += 1
            e["garage"] = f"GT2-{number:04d}"
            within_limits(e)
            for x in e["sessions"]:
                assert silent(x) <= jobgen.GRADES.get(family, set()), (family, x["id"])
            rows.append({"sessions": e, "statement": model.statement(e)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/parkfee_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c}" for _d, n, c in roster))


if __name__ == "__main__":
    main()
