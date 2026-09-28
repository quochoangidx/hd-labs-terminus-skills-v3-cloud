"""Departure and trap checks against the unpatched package (authoring only), in process.

- every departure family: the unpatched package differs from the model on every form;
- T1 silent case: with every other precipitation entry neutralised to 0.00, the unpatched package's
  precipitation figures equal the model's (the accumulated amount stays on its form day in both), and the
  natural over-repair differs;
- T2 silent case: on afternoon stations of incomplete months (no crediting shift), the unpatched `mean`
  equals the model's, and both natural over-repairs differ.
python3 check_departures.py OUT.json"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_skeleton as sk  # noqa: E402

PRECIP = ("precip", "precip_days", "precip_days_10", "precip_days_100", "greatest", "greatest_day")


def load_shipped():
    import importlib.util
    src = sk.TASK / "environment" / "app" / "src" / "coopsum"
    spec = importlib.util.spec_from_file_location("coopsum_shipped", src / "__init__.py", submodule_search_locations=[str(src)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["coopsum_shipped"] = mod
    spec.loader.exec_module(mod)
    return mod


def run(pkg, form):
    return json.loads(json.dumps(pkg.summarize(form)))


def main():
    shipped = load_shipped()
    all_cases = sk.cases()
    natural_t1 = sk.load_variant("T1_natural_shift_every_amount")
    natural_t2 = [sk.load_variant("T2_natural_null_when_incomplete"), sk.load_variant("T2_natural_new_formula_everywhere")]
    out = {"departures": {}, "traps": {}}
    for fam in [f"D{k}" for k in range(1, 9)]:
        forms = [(f, w) for x, f, w in all_cases if x == fam]
        out["departures"][fam] = {"forms": len(forms), "unpatched_differs": sum(not sk.same(run(shipped, f), w) for f, w in forms)}
    # T1
    t1 = {"stations": 0, "shipped_equals_model": 0, "natural_differs": 0, "in_next": 0}
    for x, form, _ in all_cases:
        if x != "T1":
            continue
        for s in form["stations"]:
            acc = sk.model.accumulated_positions(s)
            one = copy.deepcopy(form)
            one["stations"] = [copy.deepcopy(s)]
            rows = one["stations"][0]["days"] + [one["stations"][0]["next"]]
            for k, e in enumerate(rows, start=1):
                if k not in acc and e["precip"] not in ("A", "M"):
                    e["precip"] = "0.00"
            want = sk.model.summarize(one)["stations"][0]
            got = run(shipped, one)["stations"][0]
            nat = run(natural_t1, one)["stations"][0]
            t1["stations"] += 1
            t1["in_next"] += (len(s["days"]) + 1) in acc
            t1["shipped_equals_model"] += all(sk.same(got[k], want[k]) for k in PRECIP)
            t1["natural_differs"] += not all(sk.same(nat[k], want[k]) for k in PRECIP)
    out["traps"]["T1"] = t1
    # T2
    t2 = {"afternoon_incomplete_stations": 0, "shipped_mean_equals_model": 0, "null_differs": 0, "everywhere_differs": 0}
    for x, form, want in all_cases:
        if x != "T2":
            continue
        for s, w in zip(form["stations"], want["stations"]):
            if s["hour"] <= 11 or w["complete"]:
                continue
            one = dict(form, stations=[s])
            t2["afternoon_incomplete_stations"] += 1
            t2["shipped_mean_equals_model"] += sk.same(run(shipped, one)["stations"][0]["mean"], w["mean"])
            t2["null_differs"] += not sk.same(run(natural_t2[0], one)["stations"][0]["mean"], w["mean"])
            t2["everywhere_differs"] += not sk.same(run(natural_t2[1], one)["stations"][0]["mean"], w["mean"])
    out["traps"]["T2"] = t2
    ok = (all(v["forms"] == v["unpatched_differs"] for v in out["departures"].values())
          and t1["stations"] and t1["shipped_equals_model"] == t1["stations"] and t1["natural_differs"] > 0
          and t2["afternoon_incomplete_stations"] and t2["shipped_mean_equals_model"] == t2["afternoon_incomplete_stations"])
    out["status"] = "pass" if ok else "fail"
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
