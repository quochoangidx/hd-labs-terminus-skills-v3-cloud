"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"agreements", "bills"} object per line, the bill run worked
out by solution/model.py, which never imports the package; NN is the reading order) and
tests/expected/ROSTER (SHA-256, file, row count), and copies the shipped package and driver, byte for byte,
into tests/shipped/app. Every file must keep within the limits of rule 1.3, and an input whose figure the
manual leaves to today's code may appear only in a family that grades it.
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import jobgen
import model

TASK = Path(__file__).resolve().parent.parent
EXPECTED = TASK / "tests" / "expected"
SHIPPED = TASK / "tests" / "shipped" / "app"
CODE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def within_limits(run):
    """Rule 1.3, every limit including its ends."""
    items = run["agreements"]
    assert isinstance(run["branch"], str) and 1 <= len(items) <= jobgen.MAX_AGREEMENTS
    assert len({a["id"] for a in items}) == len(items)
    for a in items:
        assert 1 <= len(a["id"]) <= 10 and set(a["id"]) <= CODE, a["id"]
        out, back = (datetime.strptime(a[k], jobgen.FMT) for k in ("out", "in"))
        assert 2000 <= out.year <= 2099 and 2000 <= back.year <= 2099
        assert 1 <= model.length(a) <= 86400
        for k, lo, hi in (("odometer_out", 0, 999_999), ("odometer_in", 0, 999_999), ("fuel_out", 0, 8), ("fuel_in", 0, 8),
                          ("day_rate", 100, 100_000), ("mile_rate", 0, 500), ("fuel_rate", 0, 2000)):
            assert type(a[k]) is int and lo <= a[k] <= hi, (a["id"], k)
        assert model.miles(a) <= 20_000
    return True


def silent_inputs(run):
    out = set()
    for a in run["agreements"]:
        if model.length(a) < model.DAY:
            out.add("short")
        if a["fuel_in"] > a["fuel_out"]:
            out.add("fuller")
    return out


def write(name, rows):
    text = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
    (EXPECTED / name).write_text(text)
    return hashlib.sha256(text.encode()).hexdigest(), name, len(rows)


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster, number = [], 0
    for index, (family, files) in enumerate(jobgen.families().items()):
        rows = []
        for run in files:
            number += 1
            run["branch"] = f"RC3-{number:04d}"  # a neutral name: no family label reaches the package
            within_limits(run)
            carried, allowed = silent_inputs(run), jobgen.SILENT.get(family, set())
            assert carried <= allowed, (family, number, carried)
            assert not allowed or carried, (family, number, "carries none of its inputs")
            rows.append({"agreements": run, "bills": model.report(run)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/rentcharge_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c} rows" for _d, n, c in roster))


if __name__ == "__main__":
    main()
