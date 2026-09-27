"""Each departure reverted alone on the Oracle must disagree with the model; the shipped
package must agree with the model on the silent case (a certificate dated after the survey).

Usage: python3 departure_check.py TASK_DIR SCRATCH_DIR OUT_JSON
"""

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fuzz_model_oracle as F  # noqa: E402  (argv is shared: TASK SCRATCH OUT)

REVERTS = {
    "D1_day_count_30_360": ("dates.py", "    days = datetime.date(*parse(end)).toordinal() - datetime.date(*parse(start)).toordinal()\n",
                            "    sy, sm, sd = parse(start)\n    ey, em, ed = parse(end)\n    days = ((ey - sy) * 12 + (em - sm)) * 30 + (ed - sd)\n"),
    "D2_year_365": ("nuclides.py", "DAYS_PER_YEAR = 365.25", "DAYS_PER_YEAR = 365"),
    "D3_exp_mean_life": ("decay.py", "return ref_bq * 2.0 ** (-days / half_life_days(nuclide))",
                         "return ref_bq * __import__('math').exp(-days / half_life_days(nuclide))"),
    "D4_branching_ignored": ("decay.py", "return parent_bq * branching", "return parent_bq"),
    "D5_exempt_parent_only": ("checks.py", "return activity_bq + daughter_bq <= exempt_quantity(nuclide)",
                              "return activity_bq <= exempt_quantity(nuclide)"),
    "D6_leak_on_certificate": ("checks.py", "if activity_bq < LEAK_THRESHOLD_BQ[cls]:", "if entry[\"ref_bq\"] < LEAK_THRESHOLD_BQ[cls]:"),
    "D7_last_listed_wipe": ("checks.py", 'dates = [parse(w["date"]) for w in entry["leak_tests"] if w["removable_bq"] < WIPE_LEAK_BQ]',
                            'dates = [parse(w["date"]) for w in entry["leak_tests"][-1:]]'),
    "D8_disposal_thousandth": ("checks.py", "return days >= 10 * half_life_days(nuclide)", "return activity_bq <= ref_bq / 1000.0"),
    "D9_location_certificate_sum": ("locations.py", "held[entry[\"location\"]] += activity", "held[entry[\"location\"]] += entry[\"ref_bq\"]"),
}


def main():
    F.SCRATCH.mkdir(parents=True, exist_ok=True)
    variants = F.build_variants()
    out = {"reverts": {}, "silent_case": {}}
    rng = random.Random(7)
    jobs = [F.gen_inventory(rng) for _ in range(200)] + [F.gen_inventory(rng, failed_wipes=True) for _ in range(100)] + [F.gen_inventory(rng, licensing=True) for _ in range(100)]
    expect = [F.model.survey(j) for j in jobs]
    import shutil, subprocess
    for name, (rel, old, new) in REVERTS.items():
        root = F.SCRATCH / ("revert-" + name)
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(F.TASK / "environment" / "app", root / "app", ignore=shutil.ignore_patterns("__pycache__"))
        subprocess.run(["patch", "-s", "-p1", "-d", str(root)], input=(F.TASK / "solution" / "fix.patch").read_bytes(), check=True)
        p = root / "app" / "src" / "sealsrc" / rel
        s = p.read_text()
        assert old in s, name
        p.write_text(s.replace(old, new))
        got = F.run_variant(root / "app" / "src", jobs, "rev-" + name)
        bad = sum(0 if F.same(g, e) else 1 for g, e in zip(got, expect))
        out["reverts"][name] = {"jobs": len(jobs), "mismatching_jobs": bad, "detected": bad > 0}
        print(name, bad, flush=True)
    # T1 silent case: entries certified after the survey (non-daughter beta-gamma nuclides,
    # so the shipped departures D4/D5 do not confound); whole report compared.
    rng = random.Random(11)
    t1_jobs = []
    for _ in range(100):
        inv = F.gen_inventory(rng, future=True)
        inv["sources"] = [s for s in inv["sources"] if s["ref_date"] > inv["survey_date"]
                          and F.model.TABLE_2[s["nuclide"]][3] == "beta-gamma" and F.model.TABLE_2[s["nuclide"]][4] is None]
        for s in inv["sources"]:
            s["leak_tests"] = []  # the leak interval uses the day count too (D1 would confound)
        t1_jobs.append(inv)
    # TB kept shipped step: the licensing test on the certificate figure decides the source
    # count, which the shipped package computes exactly as the manual does (its D9 sum differs).
    rng = random.Random(13)
    tb_jobs = [F.gen_inventory(rng, licensing=True) for _ in range(100)]
    def counts(rep):
        return [(p["id"], p["sources"]) for p in rep["locations"]] if "locations" in rep else rep
    for label, jobs_, proj, names in (
        ("T1_future_certificate_whole_report", t1_jobs, lambda r: r, ("shipped", "oracle", "t1_overrepair")),
        ("TB_licensing_source_count", tb_jobs, counts, ("shipped", "oracle", "tB_current", "tB_total", "tB_nofilter")),
    ):
        exp_s = [proj(F.model.survey(j)) for j in jobs_]
        out["silent_case"][label] = {}
        for name in names:
            got = F.run_variant(variants[name], jobs_, "silent-" + label + name)
            bad = sum(0 if F.same(proj(g), e) else 1 for g, e in zip(got, exp_s))
            out["silent_case"][label][name] = {"jobs": len(jobs_), "mismatching_jobs": bad}
            print("silent", label, name, bad, flush=True)
    out["silent_case"]["TA_note"] = ("TA is a definition hop (1.7 decides that a wipe of 185 Bq or more is not a leak test); "
                                     "the shipped package has no kept step for it: its last-listed-wipe departure (D7) is what forces the rebuild")
    F.OUT.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
