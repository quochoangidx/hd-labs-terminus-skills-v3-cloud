"""check_departures.py OUT_JSON: shipped vs model per departure, and the kept figure on each trap (in process).

For every departure family the shipped package's statement differs from the model on every job and on
the figure that departure decides; for each trap family the shipped step, fed the figures the schedule
defines (taken from the model), gives exactly the figure the model keeps; the Oracle matches the model.
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
FIGURE = {"D1": ["storage_weeks", "storage"], "D2": ["storage"], "D3": ["handling"], "D4": ["handling"],
          "D5": ["storage"], "D6": ["storage", "handling"], "D7": ["surcharge"], "D8": ["peak"], "D9": ["handling"]}  # D4: receipt rate


def main(out):
    shipped = fuzz.load_pkg(score_skeleton.TASK / "environment" / "app" / "src")
    import stockbill.dates as shipped_dates
    import stockbill.handling as shipped_handling
    import stockbill.lots as shipped_lots

    def shipped_calendar(job):
        return shipped_dates.Calendar(job)
    oracle = fuzz.load_pkg(HERE / "oracle" / "app" / "src")
    res = {}
    for fam, job in score_skeleton.cases():
        exp = model.report(job)
        got_s = json.loads(json.dumps(shipped.build_statement(json.loads(json.dumps(job)))))
        got_o = json.loads(json.dumps(oracle.build_statement(json.loads(json.dumps(job)))))
        e = res.setdefault(fam, {"jobs": 0, "shipped_differs": 0, "figure_differs": 0, "oracle_matches": 0,
                                 "shipped_step_gives_kept_figure": 0})
        e["jobs"] += 1
        e["shipped_differs"] += not fuzz.same(got_s, exp)
        e["oracle_matches"] += fuzz.same(got_o, exp)
        if fam in FIGURE:
            e["figure_differs"] += any(got_s["lots"][0][k] != exp["lots"][0][k] for k in FIGURE[fam])
        if fam == "T1":
            lot = job["lots"][0]
            ok = True
            for x in lot["dispatches"]:
                if x["pallets"] < 0:
                    d = date.fromisoformat(x["date"])
                    took = sum(y["pallets"] for y in lot["dispatches"] if y["pallets"] >= 1 and date.fromisoformat(y["date"]) < d)
                    view = {"pallets": lot["pallets"] - took, "dispatches": [y for y in lot["dispatches"] if y["pallets"] < 1]}
                    ok = ok and shipped_lots.on_hand(view, d) == model.pallets_on_hand(lot, d)
            e["shipped_step_gives_kept_figure"] += ok
        if fam == "T2":
            lot = job["lots"][0]
            client = job["clients"][lot["client"]]
            start, end = (date.fromisoformat(job["period"][k]) for k in ("start", "end"))
            e["shipped_step_gives_kept_figure"] += shipped_handling.handling(lot, client, shipped_calendar(job), start, end) == exp["lots"][0]["handling"]
    checks = {}
    for fam, e in res.items():
        checks[f"{fam}_oracle_matches"] = e["oracle_matches"] == e["jobs"]
        if fam.startswith("D"):
            checks[f"{fam}_shipped_differs_on_every_job"] = e["shipped_differs"] == e["jobs"]
            checks[f"{fam}_departure_figure_differs"] = e["figure_differs"] == e["jobs"]
        if fam.startswith("T"):
            checks[f"{fam}_shipped_step_gives_the_kept_figure"] = e["shipped_step_gives_kept_figure"] == e["jobs"]
    status = "pass" if all(checks.values()) else "fail"
    Path(out).write_text(json.dumps({"status": status, "checks": checks, "families": res}, indent=1) + "\n")
    print(status, [k for k, v in checks.items() if not v])


if __name__ == "__main__":
    main(sys.argv[1])
