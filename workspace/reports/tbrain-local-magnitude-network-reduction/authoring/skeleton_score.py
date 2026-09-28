#!/usr/bin/env python3
"""Model-based differential scorer for tbrain-local-magnitude-network-reduction.

Authoring / skeleton-probe tool (builder-only; never shipped). Runs a candidate
/app tree's package through the SHIPPED driver on generated bulletins from
solution/jobgen.py and compares each report with solution/model.py, grouped by
rule/trap cluster.

  skeleton_score.py --app <materialized /app tree> [--seeds N] [--json OUT]

Exit 0 when every cluster passes. The candidate's own tools/ml_bulletin.py is
byte-compared with the shipped one and reported, but never executed.
"""

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
TASK = HERE.parents[4] / "workspace" / "tasks" / "tbrain-local-magnitude-network-reduction"
sys.path.insert(0, str(TASK / "solution"))
import jobgen  # noqa: E402
import model  # noqa: E402

SHIPPED_DRIVER = TASK / "environment" / "app" / "tools" / "ml_bulletin.py"
TOL = 1e-6

CLUSTERS = {
    "D1_D2_D5_amplitude_and_correction": ["plain_nodes"],
    "D3_hypocentral": ["hypocentral"],
    "D4_linear_interpolation": ["interpolation", "table_ends"],
    "D6_station_mean": ["station_mean"],
    "D7_median": ["median"],
    "D8_min_three": ["min_three"],
    "T1_readings": ["readings"],
    "T2_off_table": ["off_table"],
    "T3_shared_station": ["shared_station"],
    "envelope_limits": ["limits"],
    "generated": ["generated-1", "generated-2", "generated-3"],
}


def run_candidate(app, bulletin):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "app"
        shutil.copytree(Path(app) / "mlnet", root / "mlnet", ignore=shutil.ignore_patterns("__pycache__"))
        (root / "tools").mkdir()
        shutil.copy2(SHIPPED_DRIVER, root / "tools" / "ml_bulletin.py")
        data = Path(tmp) / "b.json"
        data.write_text(json.dumps(bulletin))
        proc = subprocess.run([sys.executable, "-I", "-S", str(root / "tools" / "ml_bulletin.py"), str(data)],
                              capture_output=True, text=True, timeout=120, cwd=tmp)
    if proc.returncode != 0:
        return None, proc.stderr.strip().splitlines()[-1:] or ["exit %d" % proc.returncode]
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as exc:
        return None, ["bad json: %s" % exc]


def num_ok(got, exp):
    if exp is None:
        return got is None
    if isinstance(got, bool) or not isinstance(got, (int, float)):
        return False
    return math.isfinite(got) and abs(got - exp) <= TOL


def compare(got, exp):
    """List of (where, kind) mismatches."""
    bad = []
    if not isinstance(got, dict) or set(got) != {"events"} or len(got["events"]) != len(exp["events"]):
        return [("report", "shape")]
    for ge, ee in zip(got["events"], exp["events"]):
        if not isinstance(ge, dict) or set(ge) != {"id", "ml", "stations"} or ge["id"] != ee["id"]:
            bad.append((str(ee["id"]), "event shape/id"))
            continue
        if not num_ok(ge["ml"], ee["ml"]):
            bad.append((ee["id"], "network ml"))
        if not isinstance(ge["stations"], list) or len(ge["stations"]) != len(ee["stations"]):
            bad.append((ee["id"], "station list"))
            continue
        for gs, es in zip(ge["stations"], ee["stations"]):
            where = "%s/%s" % (ee["id"], es["code"])
            if not isinstance(gs, dict) or set(gs) != {"code", "distance_km", "ml", "contributes"} or gs["code"] != es["code"]:
                bad.append((where, "station shape/code"))
                continue
            if not num_ok(gs["distance_km"], es["distance_km"]):
                bad.append((where, "distance_km"))
            if not num_ok(gs["ml"], es["ml"]):
                bad.append((where, "station ml"))
            if gs["contributes"] is not es["contributes"]:
                bad.append((where, "contributes"))
    return bad


# --- diagnosis of the natural wrong repairs of the two traps --------------------

def _variant_t1(bulletin):
    """Mean over every amplitude (definition 2.3 not applied)."""
    orig = model.is_reading
    model.is_reading = lambda a: True
    try:
        return model.reduce_bulletin(bulletin)
    finally:
        model.is_reading = orig


def _variant_t2(bulletin, how):
    orig = model._shipped_off_table_correction

    def lin(d):
        (d0, v0), (d1, v1) = (model.TABLE[0], model.TABLE[1]) if d < 10 else (model.TABLE[-2], model.TABLE[-1])
        return v0 + (v1 - v0) * (d - d0) / (d1 - d0)

    def clamp(d):
        return model.TABLE[0][1] if d < 10 else model.TABLE[-1][1]
    model._shipped_off_table_correction = lin if how == "linear" else clamp
    try:
        return model.reduce_bulletin(bulletin)
    finally:
        model._shipped_off_table_correction = orig


def _variant_t3(bulletin, how):
    """Recordings treated as stations: per-recording magnitudes, or pooled but counted per row."""
    if how == "per_recording":
        split = {"stations": bulletin["stations"], "events": []}
        exp = {"events": []}
        for event in bulletin["events"]:
            corr = {s["code"]: s["correction"] for s in bulletin["stations"]}
            rows = []
            for rec in event["recordings"]:
                d = model.distance_km(rec["epi_km"], event["depth_km"])
                rows.append({"code": rec["code"], "distance_km": d,
                             "ml": model.station_magnitude(rec["amplitudes"], d, corr[rec["code"]]),
                             "contributes": model.in_table(d)})
            exp["events"].append({"id": event["id"], "stations": rows,
                                  "ml": model.network_magnitude([r["ml"] for r in rows if r["contributes"]])})
        return exp
    exp = model.reduce_bulletin(bulletin)
    for event in exp["events"]:
        event["ml"] = model.network_magnitude([r["ml"] for r in event["stations"] if r["contributes"]])
    return exp


def diagnose(cluster, bulletin, got):
    if got is None:
        return None
    if cluster == "T1_readings" and not compare(got, _variant_t1(bulletin)):
        return "matches wrong path: mean over every amplitude (rule 2.3 not applied)"
    if cluster == "T2_off_table":
        if not compare(got, _variant_t2(bulletin, "linear")):
            return "matches wrong path: linear-in-distance extrapolation beyond the table"
        if not compare(got, _variant_t2(bulletin, "clamp")):
            return "matches wrong path: correction clamped to the table's end values"
    if cluster == "T3_shared_station":
        if not compare(got, _variant_t3(bulletin, "per_recording")):
            return "matches wrong path: each recording treated as its own station"
        if not compare(got, _variant_t3(bulletin, "rows")):
            return "matches wrong path: readings pooled but the median/count of three taken over recordings"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", required=True, help="materialized /app tree of the candidate")
    ap.add_argument("--seeds", type=int, default=3, help="seeds per family (first is jobgen.SEED)")
    ap.add_argument("--json", help="write the per-cluster result here")
    args = ap.parse_args()

    app = Path(args.app)
    driver = app / "tools" / "ml_bulletin.py"
    driver_same = driver.is_file() and driver.read_bytes() == SHIPPED_DRIVER.read_bytes()
    result = {"app": str(app), "driver_unchanged": driver_same, "clusters": {}}
    all_pass = driver_same
    for cluster, families in CLUSTERS.items():
        rows = []
        for fam in families:
            for k in range(args.seeds):
                seed = jobgen.SEED + 7919 * k
                bulletin = jobgen.family(fam, seed)
                exp = model.reduce_bulletin(bulletin)
                got, err = run_candidate(app, bulletin)
                bad = [("run", "; ".join(err))] if got is None else compare(got, exp)
                rows.append({"family": fam, "seed": seed,
                             "digest": hashlib.sha256(json.dumps(bulletin, sort_keys=True).encode()).hexdigest()[:12],
                             "pass": not bad, "mismatches": len(bad), "first": bad[:3],
                             "diagnosis": diagnose(cluster, bulletin, got) if bad else None})
        ok = all(r["pass"] for r in rows)
        all_pass &= ok
        result["clusters"][cluster] = {"pass": ok, "runs": rows}
        diag = sorted({r["diagnosis"] for r in rows if r["diagnosis"]})
        print("%-36s %s  %d/%d%s" % (cluster, "PASS" if ok else "FAIL", sum(r["pass"] for r in rows), len(rows),
                                     ("  [" + "; ".join(diag) + "]") if diag else ""))
    print("driver unchanged:", driver_same)
    result["pass"] = all_pass
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
