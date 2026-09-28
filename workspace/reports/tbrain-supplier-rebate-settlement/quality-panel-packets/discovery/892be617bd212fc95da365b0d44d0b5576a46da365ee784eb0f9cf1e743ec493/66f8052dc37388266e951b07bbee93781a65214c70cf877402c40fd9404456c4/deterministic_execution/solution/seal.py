"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from anywhere).

Writes tests/expected/<family>.jsonl (one {"job", "settlements"} object per line, the settlements worked out
by solution/model.py, which never imports the package) and tests/expected/ROSTER (SHA-256, file, row count),
and copies the shipped package and driver, byte for byte, into tests/shipped/app. Every job must keep within
Schedule R section 1 and carry only the inputs its family declares.
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


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster = []
    for family, jobs in jobgen.families().items():
        rows = []
        allowed = jobgen.TRAP_INPUTS.get(family, set())
        for job in jobs:
            assert not model.within_limits(job), (family, model.within_limits(job))
            carried = jobgen.trap_inputs(job)
            assert carried == allowed, (family, carried)
            graded = jobgen.expand(job) if family == "limits_job" else job
            assert not model.within_limits(graded), (family, model.within_limits(graded))
            row = {"job": job, "settlements": model.statements(graded)["settlements"]}
            if family == "limits_job":
                row["repeat"] = jobgen.REPEAT
            rows.append(row)
        text = "".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows)
        (EXPECTED / f"{family}.jsonl").write_text(text, encoding="utf-8")
        roster.append((hashlib.sha256(text.encode()).hexdigest(), f"{family}.jsonl", len(rows)))
    (EXPECTED / "ROSTER").write_text("".join(f"{d}  {n}  {c}\n" for d, n, c in sorted(roster, key=lambda r: r[1])))
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    source = TASK / "environment" / "app"
    for rel in ["tools/rebate_run.py"] + sorted(p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")):
        (SHIPPED / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, SHIPPED / rel)
    print("\n".join(f"{n}: {c} rows" for _d, n, c in sorted(roster, key=lambda r: r[1])))


if __name__ == "__main__":
    main()
