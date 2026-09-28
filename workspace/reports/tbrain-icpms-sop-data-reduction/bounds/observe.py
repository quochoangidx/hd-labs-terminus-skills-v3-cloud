"""icpms adapter for fixture_bounds_check.py: quantities SOP TM-07 section 1 bounds, via solution/model.py."""
import sys
sys.path.insert(0, "/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/tasks/tbrain-icpms-sop-data-reduction/solution")
import model  # noqa: E402


def observe(rows):
    seen = {}
    add = lambda k, v: seen.setdefault(k, []).append(v)
    for row in rows:
        b = row["batch"]
        add("analytes", len(b["analytes"])); add("standards", len(b["standards"])); add("runs", len(b["runs"]))
        for a in b["analytes"]:
            n = a["name"]
            add("mdl", a["mdl"]); add("loq", a["loq"]); add("loq_minus_mdl", a["loq"] - a["mdl"])
            add("distinct", len({s["conc"][n] for s in b["standards"]}))
            for s in b["standards"]:
                add("conc", s["conc"][n])
            slope, icpt = model.exact_line(b["standards"], n)
            add("slope", slope); add("intercept", icpt); add("icpt_over_slope", icpt / slope)
            line = model._line(b["standards"], n)
            for r in b["runs"]:
                v = model._reading(r, n, line); add("reading", v)
                if r["kind"] == "ccv":
                    t = r["true"][n]; add("ccv_true", t); add("ccv_true_over_10loq", t / (10 * a["loq"])); add("ccv_ratio", v / t); add("ccv_reading", v)
                if r["kind"] == "spike":
                    add("added", r["added"][n])
        for s in b["standards"]:
            add("is_std", s["is_counts"]); [add("counts", c) for c in s["counts"].values()]
        for r in b["runs"]:
            add("is_run", r["is_counts"]); [add("counts", c) for c in r["counts"].values()]
            if r["kind"] in ("sample", "spike"):
                add(r["kind"] + "_dil", r["dilution"])
    return seen
