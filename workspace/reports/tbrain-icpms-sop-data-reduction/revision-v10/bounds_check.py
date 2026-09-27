"""bounds_check.py TASK_DIR: every numeric range SOP TM-07 section 1 states, and the extremes the sealed
fixtures reach. A closed end must be reached exactly; an open end ("between") within 0.1% of it.
Exit 1 when an end is not reached."""
import json, sys
from fractions import Fraction
from pathlib import Path
task = Path(sys.argv[1])
sys.path.insert(0, str(task / "solution"))
import model  # noqa: E402
rows = []
for f in sorted((task / "tests/expected").glob("*.jsonl")):
    rows += [json.loads(l)["batch"] for l in f.read_text().splitlines() if l]
seen = {k: [] for k in ("analytes", "mdl", "loq-mdl", "loq", "standards", "conc", "distinct", "runs", "sample_dil", "spike_dil",
                        "added", "counts", "is_std", "is_run", "slope", "intercept", "ccv_true_over_10loq", "ccv_true",
                        "ccv_ratio", "reading", "icpt_over_slope")}
for b in rows:
    seen["analytes"].append(len(b["analytes"])); seen["standards"].append(len(b["standards"])); seen["runs"].append(len(b["runs"]))
    for a in b["analytes"]:
        n = a["name"]; seen["mdl"].append(a["mdl"]); seen["loq"].append(a["loq"]); seen["loq-mdl"].append(a["loq"] - a["mdl"])
        seen["distinct"].append(len({s["conc"][n] for s in b["standards"]}))
        seen["conc"] += [s["conc"][n] for s in b["standards"]]
        slope, icpt = model.exact_line(b["standards"], n); seen["slope"].append(slope); seen["intercept"].append(icpt); seen["icpt_over_slope"].append(icpt / slope)
        line = model._line(b["standards"], n)
        for r in b["runs"]:
            v = model._reading(r, n, line); seen["reading"].append(v)
            if r["kind"] == "ccv":
                t = r["true"][n]; seen["ccv_true"].append(t); seen["ccv_true_over_10loq"].append(t / (10 * a["loq"])); seen["ccv_ratio"].append(v / t)
            if r["kind"] == "spike": seen["added"].append(r["added"][n])
    for s in b["standards"]:
        seen["is_std"].append(s["is_counts"]); seen["counts"] += list(s["counts"].values())
    for r in b["runs"]:
        seen["is_run"].append(r["is_counts"]); seen["counts"] += list(r["counts"].values())
        if r["kind"] == "sample": seen["sample_dil"].append(r["dilution"])
        if r["kind"] == "spike": seen["spike_dil"].append(r["dilution"])
# name, key, low, high, open ends
spec = [("analytes", "analytes", 1, 4, ""), ("mdl", "mdl", 0.0001, 100, ""), ("loq = mdl allowed", "loq-mdl", 0, None, ""),
        ("loq", "loq", None, 1000, ""), ("standards", "standards", 3, 8, ""), ("conc", "conc", 0, 1000, ""),
        ("distinct concentrations", "distinct", 2, None, ""), ("runs", "runs", 1, 80, ""), ("sample dilution", "sample_dil", 1, 1000, ""),
        ("spike dilution", "spike_dil", 1, 1000, ""), ("added", "added", 0.001, 1000, ""), ("counts", "counts", 0, 1e9, ""),
        ("standard is_counts", "is_std", 1000, 1e9, ""), ("run is_counts", "is_run", 1000, 1e9, ""),
        ("slope", "slope", Fraction(1, 10**12), 10**6, ""), ("intercept below nought", "intercept", "neg", None, ""), ("intercept / slope", "icpt_over_slope", None, 10**4, ""),
        ("CCV true / (10 loq)", "ccv_true_over_10loq", 1, None, ""), ("CCV true", "ccv_true", None, 1e4, ""),
        ("CCV reading / true", "ccv_ratio", 0.5, 1.5, "both"), ("reading", "reading", -1e4, 1e4, "")]
bad = 0
out = []
for name, key, lo, hi, open_ in spec:
    vals = seen[key]; mn, mx = min(vals), max(vals)
    ok_lo = lo is None or (mn < 0 if lo == "neg" else (abs(mn - lo) <= 1e-3 * max(abs(lo), 1e-12) if open_ else mn == lo or abs(mn - lo) <= 1e-9 * max(abs(lo), 1e-12)))
    ok_hi = hi is None or (abs(mx - hi) <= 1e-3 * abs(hi) if open_ else mx == hi or abs(mx - hi) <= 1e-9 * abs(hi))
    bad += not (ok_lo and ok_hi)
    out.append(f"{'OK ' if ok_lo and ok_hi else 'GAP'} {name:28s} stated [{lo}, {hi}] reached [{float(mn):.6g}, {float(mx):.6g}]")
print("\n".join(out)); sys.exit(1 if bad else 0)
