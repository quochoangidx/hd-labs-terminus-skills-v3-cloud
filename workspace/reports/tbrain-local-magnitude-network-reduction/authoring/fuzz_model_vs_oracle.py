#!/usr/bin/env python3
"""Fuzz solution/model.py against the Oracle (shipped package + solution/fix.patch).

  fuzz_model_vs_oracle.py --oracle-app <patched /app> [--seeds N] [--out receipt.json]

Imports the patched package in-process (the model never imports it) and compares
every figure of every report on every family, both trap families and the exact
table ends included, at 1e-9. Also scores single-edit mutants of the Oracle per
cluster to show each departure and each trap wrong path is isolated.
"""
import argparse, hashlib, importlib, json, math, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
TASK = HERE.parents[4] / "workspace" / "tasks" / "tbrain-local-magnitude-network-reduction"
sys.path.insert(0, str(TASK / "solution"))
import jobgen, model  # noqa: E402

def cmp(got, exp, tol):
    worst = 0.0; bad = 0
    for ge, ee in zip(got["events"], exp["events"]):
        pairs = [(ge["ml"], ee["ml"])] + [(g[k], e[k]) for g, e in zip(ge["stations"], ee["stations"]) for k in ("distance_km", "ml")]
        for g, e in pairs:
            if (g is None) != (e is None): bad += 1; continue
            if g is None: continue
            d = abs(g - e); worst = max(worst, d); bad += d > tol
        bad += sum(g["contributes"] is not e["contributes"] or g["code"] != e["code"] for g, e in zip(ge["stations"], ee["stations"]))
        bad += ge["id"] != ee["id"] or len(ge["stations"]) != len(ee["stations"])
    return bad, worst

MUTANTS = {  # (file, old, new) applied to the Oracle
    "revert_D1_gain": ("amplitude.py", "WOOD_ANDERSON_GAIN = 2080.0", "WOOD_ANDERSON_GAIN = 2800.0"),
    "revert_D2_half": ("amplitude.py", "float(amplitude_nm) / 2.0 *", "float(amplitude_nm) *"),
    "revert_D3_hypocentral": ("distance.py", "math.sqrt(float(epi_km) ** 2 + float(depth_km) ** 2)", "float(epi_km)"),
    "revert_D4_linear": ("attenuation.py", "    if CALIBRATION[0][0] <= distance_km <= CALIBRATION[-1][0]:\n", "    if False:\n"),
    "revert_D5_sign": ("station.py", "minus_log_a0(distance_km) + correction", "minus_log_a0(distance_km) - correction"),
    "revert_D6_mean": ("station.py", "    return sum(magnitudes) / len(magnitudes)", "    return max(magnitudes)"),
    "revert_D7_median": ("network.py", "    middle = len(values) // 2\n", "    return sum(values) / len(values)\n    middle = len(values) // 2\n"),
    "revert_D8_min_three": ("network.py", "if len(values) < 3:", "if not values:"),
    "t1_mean_over_every_amplitude": ("station.py", "        if float(item[\"amplitude_nm\"]) >= 3.0 * float(item[\"noise_nm\"])\n", ""),
    "t1_strict_threshold": ("station.py", ">= 3.0 * float", "> 3.0 * float"),
    "t2_linear_everywhere": ("attenuation.py", "    if CALIBRATION[0][0] <= distance_km <= CALIBRATION[-1][0]:\n", "    if True:\n"),
    "t2_clamp_to_ends": ("attenuation.py", "    if CALIBRATION[0][0] <= distance_km <= CALIBRATION[-1][0]:\n",
                         "    distance_km = min(max(distance_km, CALIBRATION[0][0]), CALIBRATION[-1][0])\n    if True:\n"),
    "median_lower_middle": ("network.py", "    return (values[middle - 1] + values[middle]) / 2.0", "    return values[middle - 1]"),
    "exclusive_table_ends": ("network.py", "return NEAREST_KM <= distance_km <= FARTHEST_KM", "return NEAREST_KM < distance_km < FARTHEST_KM"),
    "t3_median_over_recordings": ("bulletin.py", "    counted = [row[\"ml\"] for row in stations.values() if row[\"contributes\"]]",
                                  "    counted = [row[\"ml\"] for row in rows if row[\"contributes\"]]"),
    "t3_recording_is_a_station": ("bulletin.py", None, "SHIPPED"),
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--oracle-app", required=True)
    ap.add_argument("--seeds", type=int, default=40); ap.add_argument("--out")
    a = ap.parse_args()
    sys.path.insert(0, a.oracle_app); mlnet = importlib.import_module("mlnet")
    fams = {}; worst_all = 0.0; total = 0
    for fam in jobgen.FAMILIES:
        bad_f = 0; worst_f = 0.0; ends = set()
        for k in range(a.seeds):
            b = jobgen.family(fam, jobgen.SEED + 7919 * k)
            bad, worst = cmp(mlnet.reduce_bulletin(b), model.reduce_bulletin(b), 1e-9)
            bad_f += bad; worst_f = max(worst_f, worst); total += 1
            for e in b["events"]:
                for r in e["recordings"]:
                    h = math.hypot(r["epi_km"], e["depth_km"])
                    ends.add("R<10" if h < 10 else "R>600" if h > 600 else "R=10" if h == 10 else "R=600" if h == 600 else None)
        worst_all = max(worst_all, worst_f)
        fams[fam] = {"bulletins": a.seeds, "mismatches": bad_f, "max_abs_diff": worst_f,
                     "distance_regions": sorted(x for x in ends if x), "trap_inputs": sorted(jobgen.TRAP_FAMILIES.get(fam, []))}
    # mutants: which clusters each one fails (skeleton scorer, 1 seed)
    scorer = HERE.parent / "skeleton_score.py"; mut = {}
    for name, (f, old, new) in MUTANTS.items():
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "app"; shutil.copytree(a.oracle_app, app, ignore=shutil.ignore_patterns("__pycache__"))
            p = app / "mlnet" / f
            if old is None:  # whole file back to the shipped version
                p.write_bytes((TASK / "environment/app/mlnet" / f).read_bytes())
            else:
                s = p.read_text(); assert old in s, name; p.write_text(s.replace(old, new, 1))
            out = Path(tmp) / "r.json"
            subprocess.run([sys.executable, str(scorer), "--app", str(app), "--seeds", "1", "--json", str(out)], capture_output=True)
            r = json.loads(out.read_text())
            mut[name] = sorted(c for c, v in r["clusters"].items() if not v["pass"])
    receipt = {"status": "pass" if all(v["mismatches"] == 0 for v in fams.values()) else "fail",
               "model": "solution/model.py", "oracle": "environment/app + solution/fix.patch",
               "model_sha256": hashlib.sha256((TASK / "solution/model.py").read_bytes()).hexdigest(),
               "fix_patch_sha256": hashlib.sha256((TASK / "solution/fix.patch").read_bytes()).hexdigest(),
               "jobgen_sha256": hashlib.sha256((TASK / "solution/jobgen.py").read_bytes()).hexdigest(),
               "tolerance": 1e-9, "bulletins_compared": total, "max_abs_diff": worst_all,
               "families": fams, "mutant_failed_clusters": mut}
    txt = json.dumps(receipt, indent=1); print(txt)
    if a.out: Path(a.out).write_text(txt)
    return 0 if receipt["status"] == "pass" else 1

if __name__ == "__main__":
    sys.exit(main())
