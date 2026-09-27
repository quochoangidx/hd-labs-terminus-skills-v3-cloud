"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/<family>.jsonl (one {"claims", "report"} object per line, the report worked out by
solution/model.py, which never imports the package), tests/expected/differential-<family>.jsonl (claims pairs
for the shipped differential) and tests/expected/ROSTER (SHA-256, file, row count). It also copies the shipped
package and driver, byte for byte, into tests/shipped/app. Before writing, every file must keep within the
limits of rule 1.3, and a fill above the supply limit may appear only in a family that grades it.
"""

import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

import jobgen
import model

TASK = Path(__file__).resolve().parent.parent
EXPECTED = TASK / "tests" / "expected"
SHIPPED = TASK / "tests" / "shipped" / "app"
CODE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def within_limits(claims):
    """Rule 1.3, every limit including its ends."""
    year = claims["year"]
    assert type(year) is int and 2000 <= year <= 2099
    members = claims["members"]
    assert isinstance(claims["plan"], str) and 1 <= len(members) <= jobgen.MAX_MEMBERS
    assert len({m["id"] for m in members}) == len(members)
    assert len({f["class"] for m in members for f in m["fills"]}) <= 40
    classes = {}
    for f in (f for m in members for f in m["fills"]):
        assert classes.setdefault(f["drug"], f["class"]) == f["class"], ("drug code under two classes", f["drug"])
    for m in members:
        assert 1 <= len(m["id"]) <= 12 and set(m["id"]) <= CODE | {"-"}, m["id"]
        assert len(m["fills"]) <= 400
        for f in m["fills"]:
            assert set(f) == {"date", "drug", "class", "days"}
            assert date.fromisoformat(f["date"]).year == year
            assert 1 <= len(f["drug"]) <= 11 and f["drug"].isdigit() and f["drug"].isascii()
            assert 1 <= len(f["class"]) <= 8 and set(f["class"]) <= CODE
            assert type(f["days"]) is int and 0 <= f["days"] <= 365
        assert len(m["stays"]) <= 10
        days = []
        for admission, discharge in m["stays"]:
            a, b = date.fromisoformat(admission), date.fromisoformat(discharge)
            assert a.year == year and b.year == year and a <= b
            days += range(a.toordinal(), b.toordinal() + 1)
        assert len(days) == len(set(days)) <= 60
    return True


def over_limit(claims):
    return any(f["days"] > model.SUPPLY_LIMIT for m in claims["members"] for f in m["fills"])


def no_supply(claims):
    return any(f["days"] == 0 for m in claims["members"] for f in m["fills"])


def dump(rows):
    return "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)


def write(name, rows):
    text = dump(rows)
    (EXPECTED / name).write_text(text)
    return hashlib.sha256(text.encode()).hexdigest(), name, len(rows)


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster = []
    number = 0
    for family, files in jobgen.families().items():
        rows = []
        for claims in files:
            number += 1
            claims["plan"] = f"AM2-{number:04d}"  # a neutral name: no family label reaches the package
            within_limits(claims)
            assert not over_limit(claims) or "over_limit" in jobgen.GRADES_SILENT.get(family, set()), (family, number)
            assert not no_supply(claims) or "no_supply" in jobgen.GRADES_SILENT.get(family, set()), (family, number)
            rows.append({"claims": claims, "report": model.report(claims)})
        roster.append(write(f"{family}.jsonl", rows))
    for family, pairs in jobgen.differential_pairs().items():
        rows = []
        for a, b in pairs:
            for claims in (a, b):
                number += 1
                claims["plan"] = f"AM2-{number:04d}"
                within_limits(claims)
            rows.append({"a": a, "b": b})
        roster.append(write(f"differential-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in sorted(roster, key=lambda r: r[1])))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/pdc_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c} rows" for _d, n, c in sorted(roster, key=lambda r: r[1])))


if __name__ == "__main__":
    main()
