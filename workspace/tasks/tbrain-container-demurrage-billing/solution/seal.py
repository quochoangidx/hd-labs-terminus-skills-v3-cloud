"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"release", "statement"} object per line, the statement worked out by
solution/model.py, which never imports the package; NN is the reading order) and tests/expected/ROSTER (SHA-256,
file, row count), and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every release file
must keep within rule 1.2, and a container carrying a figure the tariff leaves to today's code (a tank, or a
container not on demurrage) may appear only in a family that grades it.
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


def silent(box):
    """The figures the tariff leaves to today's code that this container carries."""
    return model.silent(box)


def within_limits(r):
    boxes = r["containers"]
    assert isinstance(r["terminal"], str) and 1 <= len(boxes) <= jobgen.MAX_CONTAINERS
    assert len({x["id"] for x in boxes}) == len(boxes)
    for x in boxes:
        assert 1 <= len(x["id"]) <= 11 and set(x["id"]) <= CODE, x["id"]
        assert x["type"] in ("DRY", "REEFER", "TANK")
        assert type(x["discharged"]) is int and 0 <= x["discharged"] <= 3650
        assert type(x["picked_up"]) is int and 0 <= x["picked_up"] - x["discharged"] <= 120
        assert type(x["rate"]) is int and 1 <= x["rate"] <= 100000
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
            r["terminal"] = f"DM3-{number:04d}"
            within_limits(r)
            for x in r["containers"]:
                assert silent(x) <= jobgen.GRADES.get(family, set()), (family, x["id"])
            rows.append({"release": r, "statement": model.statement(r)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/demurrage_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c}" for _d, n, c in roster))


if __name__ == "__main__":
    main()
