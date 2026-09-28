"""Seal the verifier's inputs and expectations: python3 solution/seal.py (run from anywhere).

Writes tests/expected/<family>.jsonl, one {"form", "summary"} object per line: the form in the compact
layout the verifier expands (each entry written as "MAX MIN PRECIP"), the summary worked out by
solution/model.py, which never imports the package, with each station's figures listed in KEYS order.
tests/expected/ROSTER holds each file's SHA-256 and row count. It also copies the shipped package and
driver, byte for byte, into tests/shipped/app. Every form must keep within handbook 1.5 and carry only
the trap inputs its family declares.
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
KEYS = ["id", "complete", "lacking_max", "lacking_min", "mean_max", "mean_min", "mean", "highest", "highest_day",
        "lowest", "lowest_day", "heating_dd", "cooling_dd", "days_max_90", "days_max_32", "days_min_32",
        "days_min_0", "precip", "precip_days", "precip_days_10", "precip_days_100", "greatest", "greatest_day"]


def trap_inputs(form):
    out = set()
    if model.carries_accumulated_at_morning(form):
        out.add("accumulated_at_morning")
    if model.carries_incomplete_month(form):
        out.add("gap_count_above_five")
    return out


def compact_entry(e):
    return f"{e['max']} {e['min']} {e['precip']}"


def compact(form, summary):
    stations = [{"id": s["id"], "hour": s["hour"], "days": [compact_entry(e) for e in s["days"]],
                 "next": compact_entry(s["next"])} for s in form["stations"]]
    rows = []
    for st in summary["stations"]:
        assert list(st) == KEYS
        rows.append([st[k] for k in KEYS])
    return {"form": {"network": form["network"], "month": form["month"], "stations": stations},
            "summary": {"network": summary["network"], "month": summary["month"], "stations": rows}}


def main():
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    EXPECTED.mkdir(parents=True)
    roster = []
    for name, forms in jobgen.families().items():
        allowed = {jobgen.TRAP_FAMILIES[name]} if name in jobgen.TRAP_FAMILIES else set()
        lines = []
        for form in forms:
            model.within_limits(form)
            carried = trap_inputs(form)
            assert carried == allowed if allowed else not carried, (name, carried)
            lines.append(json.dumps(compact(form, model.summarize(form)), separators=(",", ":"), ensure_ascii=False))
        data = ("\n".join(lines) + "\n").encode()
        (EXPECTED / f"{name}.jsonl").write_bytes(data)
        roster.append(f"{hashlib.sha256(data).hexdigest()} {name}.jsonl {len(lines)}")
    (EXPECTED / "ROSTER").write_text("\n".join(roster) + "\n")
    if SHIPPED.exists():
        shutil.rmtree(SHIPPED)
    app = TASK / "environment" / "app"
    shutil.copytree(app / "src", SHIPPED / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(app / "tools", SHIPPED / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    print("\n".join(roster))


if __name__ == "__main__":
    main()
