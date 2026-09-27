"""Write every graded batch and its expected report into tests/expected/.

Run from the task folder: python3 solution/seal.py

The expectations come from solution/model.py, which is written from SOP TM-07
and never imports the package. The hand-built families (solution/fixtures.py) are
first checked in exact rational arithmetic: every reading, blank level and
corrected reading must equal its exact value, so each value built to sit on a
limit really sits on it. The generated batches come from solution/jobgen.py with
a fixed seed. Nothing here is run at grading time; the verifier only reads the
files written below and checks their SHA-256 sums.
"""

import hashlib
import json
import math
import random
import statistics
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fixtures  # noqa: E402
import jobgen  # noqa: E402
import model  # noqa: E402

OUT = HERE.parent / "tests" / "expected"
SEED = 20260926
SIZES = [1, 3, 6, 10, 14, 20, 28, 40]


def check_exact(batch):
    """Readings, blank levels and corrected readings of a hand-built batch are exact."""
    for a in batch["analytes"]:
        name = a["name"]
        slope, intercept = model.exact_line(batch["standards"], name)
        float_line = model._line(batch["standards"], name)
        # an exact line, or (for scattered replicate standards) one within 1e-12 of it
        assert abs(Fraction(float_line[0]) - slope) <= abs(slope) / 10**12, name
        assert abs(Fraction(float_line[1]) - intercept) <= max(abs(intercept), 1) / 10**12, name
        readings = {}
        for run in batch["runs"]:
            exact = (Fraction(run["counts"][name]) / Fraction(run["is_counts"]) - intercept) / slope
            value = model._reading(run, name, float_line)
            if run["kind"] != "ccv" and Fraction(value) != exact:
                # a value built a hair off a limit: tiny rounding, far from every limit
                assert abs(Fraction(value) - exact) < Fraction(1, 10**12), run["id"]
                assert all(abs(exact - Fraction(lim)) > Fraction(1, 10**9) for lim in (a["mdl"], a["loq"])), run["id"]
            readings[run["id"]] = value
        results = [readings[r["id"]] for r in batch["runs"] if r["kind"] == "blank" and readings[r["id"]] >= a["mdl"]]
        if results:
            means = {sum(results) / len(results), statistics.fmean(results), float(statistics.mean(Fraction(v) for v in results))}
            assert len(means) == 1, (name, means)


def check_domain(batch):
    """SOP section 1, under the SOP fit."""
    analytes, standards, runs = batch["analytes"], batch["standards"], batch["runs"]
    assert 1 <= len(analytes) <= 4 and 3 <= len(standards) <= 8 and 1 <= len(runs) <= 80
    assert len({a["name"] for a in analytes}) == len(analytes)
    assert len({r["id"] for r in runs}) == len(runs)
    for a in analytes:
        assert 0.0001 <= a["mdl"] <= 100 and a["mdl"] <= a["loq"] <= 1000
        assert len({s["conc"][a["name"]] for s in standards}) >= 2
        assert all(0 <= s["conc"][a["name"]] <= 1000 for s in standards)
        line = model._line(standards, a["name"])
        exact_slope = model.exact_line(standards, a["name"])[0]
        assert Fraction(1, 10**12) <= exact_slope <= 10**6, a["name"]
        assert model.exact_line(standards, a["name"])[1] <= 10**4 * exact_slope, a["name"]  # intercept at most 10^4 x slope
        for r in runs:
            if r["kind"] == "ccv":
                true = r["true"][a["name"]]
                assert 10 * a["loq"] <= true <= 1e4 and 0.5 * true < model._reading(r, a["name"], line) < 1.5 * true, r["id"]
                tenths = model._reading(r, a["name"], line) / true * 100.0 * 10
                assert abs(tenths - (math.floor(tenths) + 0.5)) > 1e-5, r["id"]
    levels = model.reduce_batch(batch)["blank_levels"]
    for a in analytes:
        name, line = a["name"], model._line(standards, a["name"])
        for r in runs:
            value = model._reading(r, name, line)
            assert abs(value) <= 1e4 * (1 + 1e-12), r["id"]  # every reading from -10^4 to 10^4
            if r["kind"] in {"blank", "sample", "spike"}:
                judged = value if r["kind"] == "blank" else value - levels[name]
                for limit in (a["mdl"], a["loq"]):
                    # never within 10^-5 of a limit, nor one part in 10^5 of a limit above one
                    assert abs(judged - limit) > 1e-5 * max(1.0, limit), (r["id"], name, judged, limit)
    for item in standards + runs:
        assert 1000 <= item["is_counts"] <= 1e9
        assert all(0 <= c <= 1e9 for c in item["counts"].values())
    seen = set()
    for r in runs:
        assert r["kind"] in {"sample", "spike", "blank", "ccv"}
        if r["kind"] in {"sample", "spike"}:
            assert isinstance(r["dilution"], int) and 1 <= r["dilution"] <= 1000
        else:
            assert "dilution" not in r
        if r["kind"] == "spike":
            assert r["parent"] in seen and all(0.001 <= v <= 1000 for v in r["added"].values())
        if r["kind"] == "sample":
            seen.add(r["id"])


def capacity_batch(rng):
    while True:
        b = jobgen.draw_valid(rng, 80)
        if len(b["analytes"]) == 4 and len(b["standards"]) == 8 and any(r.get("dilution") == 1000 for r in b["runs"]):
            return b


def dump(path, rows):
    text = "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n"
    path.write_text(text)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        old.unlink()
    files = {}
    for family, batches in fixtures.families().items():
        rows = []
        for b in batches:
            check_exact(b)
            check_domain(b)
            rows.append({"batch": b, "report": model.reduce_batch(b)})
        files[f"{family}.jsonl"] = rows
    rng = random.Random(SEED)
    generated = [jobgen.draw_valid(rng, size) for size in SIZES]
    for b in generated:
        check_domain(b)
    rows = [{"batch": b, "report": model.reduce_batch(b)} for b in generated]
    files["generated-1.jsonl"] = rows[:5]
    # the 28- and 40-run draws stay in the sequence (so the capacity draw is unchanged) but are not
    # sealed: the panel stops reading a packet at about 150 KB, and they only repeat what
    # capacity.jsonl and the named families already cover
    files["generated-2.jsonl"] = rows[5:6]
    cap = capacity_batch(rng)
    files["capacity.jsonl"] = [{"batch": cap, "report": model.reduce_batch(cap)}]
    sums = []
    for name, rows in files.items():
        dump(OUT / name, rows)
        sums.append(f"{hashlib.sha256((OUT / name).read_bytes()).hexdigest()}  {name}  {len(rows)}")
    (OUT / "ROSTER").write_text("\n".join(sorted(sums, key=lambda s: s.split()[1])) + "\n")
    for line in sums:
        print(line)


if __name__ == "__main__":
    main()
