"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from anywhere).

Writes tests/expected/<family>.jsonl (one {"job", "statements"} object per line, the statements worked out
by solution/model.py, which never imports the package), tests/expected/differential-<family>.jsonl (job
pairs for the shipped differential) and tests/expected/ROSTER (SHA-256, file, row count). It also copies the
shipped package and driver, byte for byte, into tests/shipped/app. Before writing, every job must keep within
the limits of manual section 1 and carry only the inputs its family declares.
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


def dump(rows):
    return "".join(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows)


def write(name, rows):
    text = dump(rows)
    (EXPECTED / name).write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest(), name, len(rows)


def check(family, job):
    assert not model.within_limits(job), (family, model.within_limits(job))
    for c in job["claims"]:  # 1.4: one line of a week's wages per payday; only corrections share one
        paydays = [p for p, cents in c["wages"] if cents >= jobgen.WEEKS_PAY]
        assert len(paydays) == len(set(paydays)), (family, c["claim"], "two week's-pay lines on one payday")
    allowed = jobgen.TRAP_INPUTS.get(family, set())
    carried = jobgen.trap_inputs(job)
    assert carried <= allowed, (family, carried)
    return carried


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster = []
    for family, jobs in jobgen.families().items():
        rows = []
        for job in jobs:
            carried = check(family, job)
            if jobgen.TRAP_INPUTS.get(family):
                assert carried, (family, "carries none of its inputs")
            rows.append({"job": job, "statements": model.statements(job)})
        roster.append(write(f"{family}.jsonl", rows))
    for family, pairs in jobgen.differential_pairs().items():
        rows = []
        for pair in pairs:
            if isinstance(pair, dict):  # a single job the shipped package and the manual agree on
                assert check(f"differential-{family}", pair)
                rows.append({"job": pair})
            else:
                check(f"differential-{family}", pair[0])
                check(f"differential-{family}", pair[1])
                rows.append({"a": pair[0], "b": pair[1]})
        roster.append(write(f"differential-{family}.jsonl", rows))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in sorted(roster, key=lambda r: r[1])))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/tdbenefit_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c} rows" for _d, n, c in sorted(roster, key=lambda r: r[1])))


if __name__ == "__main__":
    main()
