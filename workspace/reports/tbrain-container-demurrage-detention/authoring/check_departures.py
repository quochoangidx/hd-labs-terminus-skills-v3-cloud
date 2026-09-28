"""check_departures.py OUT_JSON: shipped vs model per departure, and the kept figure on each trap (in process).

For every scorer family: the shipped package's statement differs from the model on every job of each
departure family (and on the figure that departure decides). For each trap family: the shipped step,
fed the figures the rules define (taken from the model), gives exactly the figure the model keeps.
"""

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fuzz  # noqa: E402
import score_skeleton  # noqa: E402

model = score_skeleton.model

FIGURE = {  # (stage, key) or container key the departure decides
    "D1": [("terminal", "days")], "D2": [("terminal", "last_free_day")], "D3": [("terminal", "last_free_day"), ("terminal", "chargeable")],
    "D4": [("merchant", "first_day")], "D5": [("terminal", "amount")], "D6": [("merchant", "amount"), ("terminal", "amount")],
    "D7": [(None, "discount")],
}


def figure(report, stage, key):
    row = report["containers"][0]
    return row[key] if stage is None else (row[stage] or {}).get(key)


def main(out):
    shipped = fuzz.load_pkg(score_skeleton.TASK / "environment" / "app" / "src")
    import ddbill.rates as shipped_rates
    import ddbill.statement as shipped_statement
    oracle = fuzz.load_pkg(HERE / "oracle" / "app" / "src")
    res = {"departures": {}, "traps": {}, "broad": {}}
    for fam, job in score_skeleton.cases():
        exp = model.report(job)
        got_s = json.loads(json.dumps(shipped.build_statement(json.loads(json.dumps(job)))))
        got_o = json.loads(json.dumps(oracle.build_statement(json.loads(json.dumps(job)))))
        entry = res["departures" if fam.startswith("D") else "traps" if fam.startswith("T") else "broad"].setdefault(
            fam, {"jobs": 0, "shipped_differs": 0, "figure_differs": 0, "oracle_matches": 0, "shipped_keeps_silent_figure": 0})
        entry["jobs"] += 1
        entry["shipped_differs"] += not fuzz.same(got_s, exp)
        entry["oracle_matches"] += fuzz.same(got_o, exp)
        if fam in FIGURE:
            entry["figure_differs"] += any(figure(got_s, st, k) != figure(exp, st, k) for st, k in FIGURE[fam])
        if fam == "T1":
            row = exp["containers"][0]
            pct = job["contracts"]["K1"]["discount_percent"]
            entry["shipped_keeps_silent_figure"] += shipped_statement.discount_on(row["amount"], pct) == row["discount"]
        if fam == "T2":
            c = job["containers"][0]
            contract = job["contracts"][c["contract"]]
            ok = True
            for name, first, last, _e in model.stage_list(c, date.fromisoformat(job["cut_off"])):
                free = contract[name + "_free_days"]
                lfd = model.last_free_day(name, first, free, {date.fromisoformat(x) for x in job["holidays"]},
                                          {date.fromisoformat(x) for x in job["closures"]})
                dates = model.chargeable_dates(name, last, lfd, {date.fromisoformat(x) for x in job["closures"]})
                if dates and model.revision_in_force(contract["revisions"], dates[0]) is None:
                    ok = ok and shipped_rates.scale_for(contract, name, c["size"]) == model.stage_scale(contract, name, c["size"], dates[0])
            entry["shipped_keeps_silent_figure"] += ok
    checks = {}
    for fam, e in res["departures"].items():
        checks[f"{fam}_shipped_differs_on_every_job"] = e["shipped_differs"] == e["jobs"]
        checks[f"{fam}_departure_figure_differs"] = e["figure_differs"] == e["jobs"]
        checks[f"{fam}_oracle_matches"] = e["oracle_matches"] == e["jobs"]
    for fam, e in res["traps"].items():
        checks[f"{fam}_shipped_step_gives_the_kept_figure"] = e["shipped_keeps_silent_figure"] == e["jobs"]
        checks[f"{fam}_oracle_matches"] = e["oracle_matches"] == e["jobs"]
    checks["broad_oracle_matches"] = res["broad"]["broad"]["oracle_matches"] == res["broad"]["broad"]["jobs"]
    status = "pass" if all(checks.values()) else "fail"
    Path(out).write_text(json.dumps({"status": status, "checks": checks, "families": res}, indent=1) + "\n")
    print(status, [k for k, v in checks.items() if not v])


if __name__ == "__main__":
    main(sys.argv[1])
