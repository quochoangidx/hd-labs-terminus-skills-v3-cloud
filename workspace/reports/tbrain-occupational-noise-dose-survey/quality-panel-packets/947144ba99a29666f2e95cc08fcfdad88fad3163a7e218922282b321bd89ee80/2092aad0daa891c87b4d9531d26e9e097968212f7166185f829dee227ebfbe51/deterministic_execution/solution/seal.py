"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from the task folder).

Writes tests/expected/<family>.jsonl (one {"survey", "report"} object per line, the report worked out by
solution/model.py, which never imports the package), tests/expected/differential-<family>.jsonl (survey
pairs for the shipped differential) and tests/expected/ROSTER (SHA-256, file, row count). It also copies the
shipped package and driver, byte for byte, into tests/shipped/app. Before writing, every survey must keep
within the limits of manual section 1, carry only the trap inputs its family declares, and stay clear of a
rounding half.
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


def within_limits(survey):
    """Manual 1.4, every limit including its ends."""
    workers = survey["workers"]
    assert isinstance(survey["survey"], str) and 1 <= len(workers) <= 300
    assert len({w["group"] for w in workers}) <= 40
    assert len({w["id"] for w in workers}) == len(workers)
    for w in workers:
        assert 1 <= len(w["id"]) <= 12 and set(w["id"]) <= CODE | {"-"}, w["id"]
        assert 1 <= len(w["group"]) <= 8 and set(w["group"]) <= CODE, w["group"]
        assert type(w["shift_minutes"]) is int and 60 <= w["shift_minutes"] <= 1440
        assert len(w["log"]) <= 1500 and sum(m for m, _ in w["log"]) <= 2880
        for m, level in w["log"]:
            assert type(m) is int and 1 <= m <= 1440
            assert type(level) is float and (level == 0.0 or 40.0 <= level <= 140.0) and round(level, 1) == level
        assert len(w["peaks"]) <= 500
        for p in w["peaks"]:
            assert type(p) is float and 60.0 <= p <= 170.0 and round(p, 1) == p
    return True


def trap_inputs(survey):
    """Inputs the manual leaves to today's code, or governed inputs kept to their own family."""
    out = set()
    for w in survey["workers"]:
        log = [tuple(r) for r in w["log"]]
        if any(level == 0.0 for _m, level in log):
            out.add("paused")
        if any(level > 115.0 for _m, level in log):
            out.add("above_ceiling")
        if not model.is_full_shift(model.sampled_time(log), w["shift_minutes"]):
            out.add("below_three_quarters")
    return out


def short(report):
    """Doses to twelve significant figures (the verifier's tolerance is one part in a million)."""
    for row in report["workers"] + report["groups"]:
        row["dose"] = float(f"{row['dose']:.12g}")
    return report


def dump(rows):
    return "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster = []
    number = 0
    fams = jobgen.families()
    late = sum(1 for surveys in fams.values() for s in surveys if s["survey"] != "LATE")
    for surveys in fams.values():  # surveys added later take numbers after all the others
        for s in surveys:
            if s["survey"] == "LATE":
                late += 1
                s["survey"] = f"HC4-{late:04d}"
    for family, surveys in fams.items():
        allowed = jobgen.TRAP_INPUTS.get(family, set())
        rows = []
        for survey in surveys:
            if not survey["survey"].startswith("HC4-"):
                number += 1
                survey["survey"] = f"HC4-{number:04d}"  # a neutral name: no family label reaches the package
            within_limits(survey)
            carried = trap_inputs(survey)
            assert carried <= allowed, (family, survey["survey"], carried)
            if allowed:
                assert carried, (family, survey["survey"], "carries none of its inputs")
            assert not model.near_rounding_edge(survey), (family, survey["survey"])
            rows.append({"survey": survey, "report": short(model.report(survey))})
        roster.append(write(f"{family}.jsonl", rows))
    for family, pairs in jobgen.differential_pairs().items():
        for a, b in pairs:
            within_limits(a)
            within_limits(b)
            assert trap_inputs(a) <= jobgen.TRAP_INPUTS[family] and trap_inputs(b) <= jobgen.TRAP_INPUTS[family]
        roster.append(write(f"differential-{family}.jsonl", [{"a": a, "b": b} for a, b in pairs]))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in sorted(roster, key=lambda r: r[1])))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/noisedose_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c} rows" for _d, n, c in sorted(roster, key=lambda r: r[1])))


def write(name, rows):
    text = dump(rows)
    (EXPECTED / name).write_text(text)
    return hashlib.sha256(text.encode()).hexdigest(), name, len(rows)


if __name__ == "__main__":
    main()
