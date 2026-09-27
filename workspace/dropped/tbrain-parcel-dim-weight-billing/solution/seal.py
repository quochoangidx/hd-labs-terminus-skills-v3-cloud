"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/NN-<family>.jsonl (one {"manifest", "invoice"} object per line, the invoice worked out by
solution/model.py, which never imports the package; NN is the reading order) and tests/expected/ROSTER (SHA-256,
file, row count), and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every manifest
must keep within rule 1.3, and a parcel carrying a figure the rules leave to today's code (a parcel that is not a
box, or an express parcel) may appear only in a family that grades it.
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


def silent(parcel):
    """The figures the rules leave to today's code that this parcel carries."""
    out = set()
    if min(parcel["sides"]) < 2:
        out.add("not_box")
    if parcel["service"] == "EXPRESS":
        out.add("express")
        if parcel["residential"]:
            out.add("express_home")
    return out


def within_limits(m):
    parcels = m["parcels"]
    assert isinstance(m["manifest"], str) and 1 <= len(parcels) <= jobgen.MAX_PARCELS
    assert len({x["id"] for x in parcels}) == len(parcels)
    for x in parcels:
        assert 1 <= len(x["id"]) <= 12 and set(x["id"]) <= CODE, x["id"]
        assert len(x["sides"]) == 3 and all(type(s) is int and 1 <= s <= 108 for s in x["sides"])
        assert type(x["weight"]) is int and 1 <= x["weight"] <= 1500
        assert x["service"] in ("GROUND", "EXPRESS") and type(x["zone"]) is int and 2 <= x["zone"] <= 8
        assert type(x["residential"]) is bool
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
    for index, (family, manifests) in enumerate(jobgen.families().items()):
        rows = []
        for m in manifests:
            number += 1
            m["manifest"] = f"PB4-{number:04d}"
            within_limits(m)
            for x in m["parcels"]:
                assert silent(x) <= jobgen.GRADES.get(family, set()), (family, x["id"])
            rows.append({"manifest": m, "invoice": model.invoice(m)})
        roster.append(write(f"{index + 1:02d}-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in roster))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/parcelbill_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c}" for _d, n, c in roster))


if __name__ == "__main__":
    main()
