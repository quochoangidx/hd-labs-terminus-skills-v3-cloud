"""Authoring receipt: model vs Oracle fuzz, and shipped-vs-model departure/trap checks.

Usage: python3 fuzz_and_departures.py TASK_DIR OUT_JSON

Builds two copies of /app (shipped, and shipped + solution/fix.patch), imports each
package in a fresh interpreter-level module namespace, and compares with solution/model.py.
"""

import copy
import hashlib
import importlib
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TASK = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(TASK / "solution"))
import jobgen  # noqa: E402
import model  # noqa: E402


def load_package(app_dir):
    for name in [m for m in sys.modules if m == "cellbank" or m.startswith("cellbank.")]:
        del sys.modules[name]
    sys.path.insert(0, str(app_dir / "src"))
    try:
        pkg = importlib.import_module("cellbank")
    finally:
        sys.path.pop(0)
    return pkg.build_report


def trees():
    work = Path(tempfile.mkdtemp())
    shipped = work / "shipped" / "app"
    oracle = work / "oracle" / "app"
    shutil.copytree(TASK / "environment" / "app", shipped)
    shutil.copytree(TASK / "environment" / "app", oracle)
    subprocess.run(
        ["patch", "-p1", "--no-backup-if-mismatch", "-i", str(TASK / "solution" / "fix.patch")],
        cwd=oracle.parent, check=True, capture_output=True,
    )
    return shipped, oracle


def same(a, b):
    """Type-strict recursive equality."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        return a == b or (math.isnan(a) and math.isnan(b))
    return a == b


SHIPPED_DIR, ORACLE_DIR = trees()
ORACLE = load_package(ORACLE_DIR)
SHIPPED = load_package(SHIPPED_DIR)
# re-load oracle last-used check: ensure both are distinct callables
assert ORACLE is not SHIPPED

receipt = {"task_dir": str(TASK), "fix_patch_sha256": hashlib.sha256((TASK / "solution" / "fix.patch").read_bytes()).hexdigest(),
           "model_sha256": hashlib.sha256((TASK / "solution" / "model.py").read_bytes()).hexdigest()}

# ---------------------------------------------------------------- fuzz model vs Oracle
rng = random.Random(20260926)
fuzz = {}
for mode, kwargs in {
    "governed": {},
    "failed_counts": {"failed_counts": True},
    "drained_banks": {"drain_banks": True},
    "both_silent_kinds": {"failed_counts": True, "drain_banks": True},
}.items():
    mismatches = 0
    runs = 0
    carried = {"failed_count": 0, "drained_bank": 0}
    for i in range(150):
        size = rng.choice([1, 2, 5, 20, 60, 150, 400]) if i % 5 else rng.randint(1, 400)
        log = jobgen.draw(rng, size, **kwargs)
        want = model.build_report(copy.deepcopy(log))
        got = ORACLE(copy.deepcopy(log))
        runs += 1
        if not same(want, got):
            mismatches += 1
        carried["failed_count"] += jobgen.has_failed_count(log)
        carried["drained_bank"] += jobgen.has_drained_bank(log)
    fuzz[mode] = {"logs": runs, "model_vs_oracle_mismatches": mismatches, "logs_carrying": carried}
receipt["fuzz_model_vs_oracle"] = fuzz


# ---------------------------------------------------------------- targeted checks
def line(name="HX-1", seed_pdl=10.0, seed_passage=3, max_pdl=60.0):
    return {"name": name, "seed_pdl": seed_pdl, "seed_passage": seed_passage, "max_pdl": max_pdl}


def thaw(rid, vial=None, viability=90.0, line_name="HX-1", cells=2000000):
    return {"id": rid, "kind": "thaw", "line": line_name, "vial": vial, "cells": cells, "viability": viability}


def cult(rid, source, seeded, harvested, viability=95.0):
    return {"id": rid, "kind": "culture", "source": source, "seeded": seeded, "harvested": harvested, "viability": viability}


def frz(rid, source, bank, vials):
    return {"id": rid, "kind": "freeze", "source": source, "bank": bank, "vials": vials}


def cultures_by_id(report):
    return {c["id"]: c for c in report["cultures"]}


CASES = {
    "D1_viable_harvest": {
        "log": {"lines": [line()], "records": [thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 4000000, viability=80.0)]},
        "field": ("culture", "C1", "doublings"),
    },
    "D2_seed_at_source_viability": {
        "log": {"lines": [line()], "records": [thaw("T1", viability=75.0), cult("C1", "T1", 1000000, 4000000, viability=100.0)]},
        "field": ("culture", "C1", "doublings"),
    },
    "D3_pdl_follows_lineage": {
        "log": {"lines": [line()], "records": [
            thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 4000000, 100.0),
            cult("C2", "C1", 1000000, 8000000, 100.0), cult("C3", "C1", 1000000, 2000000, 100.0)]},
        "field": ("culture", "C3", "pdl"),
    },
    "D4_thaw_takes_vial_pdl": {
        "log": {"lines": [line()], "records": [
            thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 16000000, 100.0), frz("F1", "C1", "HX-1 MCB", 5),
            thaw("T2", "F1", viability=100.0), cult("C2", "T2", 1000000, 2000000, 100.0)]},
        "field": ("culture", "C2", "pdl"),
    },
    "D5_thaw_is_not_a_passage": {
        "log": {"lines": [line()], "records": [thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 2000000, 100.0)]},
        "field": ("culture", "C1", "passage"),
    },
    "D6_flag_on_age_after_a_loss": {
        "log": {"lines": [line(seed_pdl=10.0, max_pdl=20.0)], "records": [
            thaw("T1", viability=100.0), cult("C1", "T1", 100000, 2 ** 11 * 100000, 100.0),
            cult("C2", "C1", 8000000, 1000000, 100.0)]},
        "field": ("culture", "C2", "flag"),
    },
    "D7_near_band_is_three": {
        "log": {"lines": [line(seed_pdl=10.0, max_pdl=20.0)], "records": [
            thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 2 ** 6 * 1000000, 100.0)]},
        "field": ("culture", "C1", "flag"),
    },
    "D8_vials_left_less_thaws": {
        "log": {"lines": [line()], "records": [
            thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 4000000, 100.0), frz("F1", "C1", "HX-1 MCB", 5),
            thaw("T2", "F1", viability=100.0)]},
        "field": ("bank", "HX-1 MCB", "vials_left"),
    },
    "D9_bank_pdl_highest_in_stock": {
        "log": {"lines": [line()], "records": [
            thaw("T1", viability=100.0), cult("C1", "T1", 1000000, 4000000, 100.0),
            cult("C2", "C1", 1000000, 4000000, 100.0), frz("F1", "C2", "HX-1 MCB", 3),
            cult("C3", "C2", 4000000, 1000000, 100.0), frz("F2", "C3", "HX-1 MCB", 2)]},
        "field": ("bank", "HX-1 MCB", "pdl"),
    },
}


def pick(report, where):
    kind, key, field = where
    if kind == "culture":
        return cultures_by_id(report)[key][field]
    return {b["bank"]: b for b in report["banks"]}[key][field]


departures = {}
for name, case in CASES.items():
    want = model.build_report(copy.deepcopy(case["log"]))
    shipped = SHIPPED(copy.deepcopy(case["log"]))
    oracle = ORACLE(copy.deepcopy(case["log"]))
    departures[name] = {
        "model": pick(want, case["field"]),
        "shipped": pick(shipped, case["field"]),
        "oracle_matches_model_whole_report": same(want, oracle),
        "shipped_differs_on_field": not same(pick(want, case["field"]), pick(shipped, case["field"])),
    }
receipt["departures"] = departures


# ---------------------------------------------------------------- traps: silent case keeps shipped
def overrepair_t1(log):
    """Natural repair: viable counts everywhere, whatever the viability."""
    rep = model.build_report(copy.deepcopy(log))
    by_id = {r["id"]: r for r in log["records"]}
    tree = model.Lineage(log)
    # recompute doublings for every culture with viability applied regardless of 2.3
    for c in rep["cultures"]:
        rec = by_id[c["id"]]
        seed_v = by_id[rec["source"]]["viability"]
        c["doublings"] = math.log2((rec["harvested"] * rec["viability"] / 100) / (rec["seeded"] * seed_v / 100))
    del tree
    return rep


T1_LOG = {"lines": [line(max_pdl=80.0)], "records": [
    thaw("T1", viability=62.5),  # failed thaw count: the first culture's seed has no viable count
    cult("C1", "T1", 1000000, 6000000, viability=92.0),
    cult("C2", "C1", 1000000, 5000000, viability=64.0),  # failed harvest count
    cult("C3", "C2", 1000000, 4000000, viability=90.0),  # seed drawn from a failed count
    cult("C4", "C3", 1000000, 4000000, viability=70.0),  # valid at exactly 70.0
    cult("C5", "C4", 1000000, 3000000, viability=69.9),  # failed at 69.9
]}
want = model.build_report(copy.deepcopy(T1_LOG))
shipped = SHIPPED(copy.deepcopy(T1_LOG))
over = overrepair_t1(T1_LOG)
t1 = {}
for cid in ["C1", "C2", "C3", "C4", "C5"]:
    t1[cid] = {
        "model_doublings": cultures_by_id(want)[cid]["doublings"],
        "shipped_doublings": cultures_by_id(shipped)[cid]["doublings"],
        "overrepair_doublings": cultures_by_id(over)[cid]["doublings"],
    }
receipt["trap_T1_failed_count_keeps_total_count_doublings"] = {
    "cases": t1,
    "shipped_equals_model_on_silent_cultures": all(
        t1[c]["shipped_doublings"] == t1[c]["model_doublings"] for c in ["C1", "C2", "C3", "C5"]),
    "overrepair_differs_on_silent_cultures": all(
        t1[c]["overrepair_doublings"] != t1[c]["model_doublings"] for c in ["C1", "C2", "C3", "C5"]),
    "governed_C4_differs_from_shipped": t1["C4"]["shipped_doublings"] != t1["C4"]["model_doublings"],
    "oracle_matches_model": same(want, ORACLE(copy.deepcopy(T1_LOG))),
}

# T2: supplier-vial lineage in log order, so shipped figures of each freeze equal the model's
T2_LOG = {"lines": [line(seed_passage=0, max_pdl=80.0)], "records": [
    {"id": "T1", "kind": "thaw", "line": "HX-1", "vial": None, "cells": 2000000, "viability": 100.0},
    cult("C1", "T1", 1000000, 4000000, 100.0),
    cult("C2", "C1", 1000000, 8000000, 100.0), frz("F1", "C2", "HX-1 WCB-1", 2),
    cult("C3", "C2", 4000000, 1000000, 100.0), frz("F2", "C3", "HX-1 WCB-1", 1),
    frz("F3", "C3", "HX-1 MCB", 2),
    thaw("T2", "F1", viability=100.0), thaw("T3", "F1", viability=100.0), thaw("T4", "F2", viability=100.0),
    thaw("T5", "F3", viability=100.0),
]}
want = model.build_report(copy.deepcopy(T2_LOG))
shipped = SHIPPED(copy.deepcopy(T2_LOG))
wb = {b["bank"]: b for b in want["banks"]}
sb = {b["bank"]: b for b in shipped["banks"]}
tree = model.Lineage(T2_LOG)
all_freeze_max = max(tree.figures("C2")[1], tree.figures("C3")[1])
receipt["trap_T2_drained_bank_keeps_latest_freeze_pdl"] = {
    "drained_bank": {"model_pdl": wb["HX-1 WCB-1"]["pdl"], "shipped_pdl": sb["HX-1 WCB-1"]["pdl"],
                     "overrepair_max_over_all_freezes": all_freeze_max, "overrepair_none": None,
                     "model_vials_left": wb["HX-1 WCB-1"]["vials_left"]},
    "governed_bank": {"model_pdl": wb["HX-1 MCB"]["pdl"], "model_vials_left": wb["HX-1 MCB"]["vials_left"]},
    "shipped_equals_model_on_drained_bank_pdl": sb["HX-1 WCB-1"]["pdl"] == wb["HX-1 WCB-1"]["pdl"],
    "overrepair_differs": all_freeze_max != wb["HX-1 WCB-1"]["pdl"],
    "oracle_matches_model": same(want, ORACLE(copy.deepcopy(T2_LOG))),
}

receipt["summary"] = {
    "fuzz_total_logs": sum(v["logs"] for v in fuzz.values()),
    "fuzz_mismatches": sum(v["model_vs_oracle_mismatches"] for v in fuzz.values()),
    "all_departures_differ_in_shipped": all(v["shipped_differs_on_field"] for v in departures.values()),
    "all_departure_cases_oracle_matches_model": all(v["oracle_matches_model_whole_report"] for v in departures.values()),
    "t1_ok": receipt["trap_T1_failed_count_keeps_total_count_doublings"]["shipped_equals_model_on_silent_cultures"]
    and receipt["trap_T1_failed_count_keeps_total_count_doublings"]["overrepair_differs_on_silent_cultures"],
    "t2_ok": receipt["trap_T2_drained_bank_keeps_latest_freeze_pdl"]["shipped_equals_model_on_drained_bank_pdl"]
    and receipt["trap_T2_drained_bank_keeps_latest_freeze_pdl"]["overrepair_differs"],
}
OUT.write_text(json.dumps(receipt, indent=1) + "\n")
print(json.dumps(receipt["summary"], indent=1))
print(json.dumps(receipt["fuzz_model_vs_oracle"], indent=1))
