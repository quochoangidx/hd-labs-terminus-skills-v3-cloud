"""Skeleton scorer for tbrain-cell-line-passage-doubling (exploratory, not a verifier).

Usage: python3 score_skeleton.py APP_DIR OUT_JSON

Runs the pristine copy of the fixed driver (authoring/pristine_driver, sha-checked)
against APP_DIR/src mounted read-only in the digest-pinned task base image, with
--network none, as an unprivileged uid. Every log comes from seeded families: one broad
trap-free family, one per SOP departure, one per restraint trap. Each report is compared
type-strictly with solution/model.py (floats to 1e-9 relative, 1e-9 absolute below one).
"""

import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TASK = REPO / "workspace" / "tasks" / "tbrain-cell-line-passage-doubling"
sys.path.insert(0, str(TASK / "solution"))
import jobgen  # noqa: E402
import model  # noqa: E402

IMAGE = ("public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:"
         "01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb")
DRIVER = HERE / "pristine_driver" / "cellbank_run.py"
DRIVER_SHA = "bb967446a06055a7e161747acd947a783181a82d911783d09939ab3cd356f8a8"
SEED = 4172026
PER_FAMILY = 8


# ------------------------------------------------------------------ log builders
class Log:
    def __init__(self, rng, seed_pdl=None, max_pdl=300.0):
        self.rng = rng
        self.n = 0
        self.line = {
            "name": f"CL-{rng.randint(10, 99)}",
            "seed_pdl": round(rng.uniform(0.0, 40.0), 2) if seed_pdl is None else seed_pdl,
            "seed_passage": rng.randint(0, 50),
            "max_pdl": max_pdl,
        }
        self.records = []

    def rid(self, p):
        self.n += 1
        return f"{p}{self.rng.randint(100, 999)}-{self.n}"

    def v(self):
        return round(self.rng.uniform(70.0, 100.0), 1)

    def thaw(self, vial=None, viability=None):
        r = {"id": self.rid("T"), "kind": "thaw", "line": self.line["name"], "vial": vial,
             "cells": self.rng.randint(10**5, 10**7), "viability": self.v() if viability is None else viability}
        self.records.append(r)
        return r["id"]

    def culture(self, source, gain=None, viability=None, seeded=None):
        seeded = seeded or self.rng.randint(10**5, 10**7)
        gain = self.rng.uniform(0.5, 4.0) if gain is None else gain
        harvested = max(1000, min(10**9, int(round(seeded * 2 ** gain))))
        r = {"id": self.rid("C"), "kind": "culture", "source": source, "seeded": seeded,
             "harvested": harvested, "viability": self.v() if viability is None else viability}
        self.records.append(r)
        return r["id"]

    def freeze(self, source, bank, vials):
        r = {"id": self.rid("F"), "kind": "freeze", "source": source, "bank": bank, "vials": vials}
        self.records.append(r)
        return r["id"]

    def done(self):
        return {"lines": [self.line], "records": self.records}


def climb(g, source, total):
    """Cultures at 100.0 viability whose doublings add up to `total` (steps of at most 8)."""
    steps = max(1, math.ceil(total / 8.0))
    for _ in range(steps):
        source = g.culture(source, gain=total / steps, viability=100.0, seeded=100000)
    return source


def fam_broad(rng):
    return jobgen.draw(rng, rng.choice([5, 20, 60, 150, 400]))


def fam_d1(rng):  # 3.1: harvest at its own viability; seeds from 100.0 thaws
    g = Log(rng)
    for _ in range(rng.randint(1, 3)):
        g.culture(g.thaw(viability=100.0), viability=round(rng.uniform(70.0, 99.9), 1))
    return g.done()


def fam_d2(rng):  # 2.4: seed at the source suspension's viability
    g = Log(rng)
    for _ in range(rng.randint(1, 3)):
        g.culture(g.thaw(viability=round(rng.uniform(70.0, 99.9), 1)), viability=100.0)
    return g.done()


def fam_d3(rng):  # 4.3: sisters and interleaved lineages
    g = Log(rng)
    a = g.culture(g.thaw(viability=100.0), viability=100.0)
    b = g.culture(g.thaw(viability=100.0), viability=100.0)
    for _ in range(rng.randint(2, 4)):
        g.culture(a, viability=100.0)
        g.culture(b, viability=100.0)
    return g.done()


def fam_d4(rng):  # 4.2: a bank vial thawed after the line has grown on
    g = Log(rng)
    c1 = g.culture(g.thaw(viability=100.0), viability=100.0)
    f = g.freeze(c1, g.line["name"] + " MCB", rng.randint(3, 500))
    g.culture(g.culture(c1, viability=100.0), viability=100.0)
    g.culture(g.thaw(vial=f, viability=100.0), viability=100.0)
    return g.done()


def fam_d5(rng):  # 4.2: a thaw is not a passage
    g = Log(rng)
    g.culture(g.thaw(viability=100.0), viability=100.0)
    return g.done()


def fam_d6(rng):  # 5.1/5.2: a crash after passing the maximum keeps LIMIT
    seed = round(rng.uniform(5.0, 30.0), 2)
    top = round(seed + rng.uniform(10.0, 30.0), 2)
    g = Log(rng, seed_pdl=seed, max_pdl=top)
    c = climb(g, g.thaw(viability=100.0), top - seed + rng.uniform(0.3, 2.0))
    g.culture(c, gain=-rng.uniform(6.0, 9.0), viability=100.0, seeded=10**9 // 2)
    return g.done()


def fam_d7(rng):  # 5.2: the NEAR band is three doublings
    seed = round(rng.uniform(5.0, 30.0), 2)
    top = round(seed + rng.uniform(8.0, 15.0), 2)
    g = Log(rng, seed_pdl=seed, max_pdl=top)
    climb(g, g.thaw(viability=100.0), top - seed - rng.uniform(3.3, 4.7))
    return g.done()


def fam_d8(rng):  # 6.1: thawed vials come off the bank
    g = Log(rng)
    c = g.culture(g.thaw(viability=100.0), viability=100.0)
    n = rng.randint(2, 500)
    f = g.freeze(c, g.line["name"] + " WCB-1", n)
    for _ in range(rng.randint(1, min(n - 1, 6))):
        g.thaw(vial=f, viability=100.0)
    return g.done()


def fam_d9(rng):  # 6.2: highest PDL in stock, not the latest freeze
    g = Log(rng)
    bank = g.line["name"] + " WCB-2"
    c = g.culture(g.culture(g.thaw(viability=100.0), viability=100.0), viability=100.0)
    g.freeze(c, bank, rng.randint(2, 50))
    low = g.culture(c, gain=-rng.uniform(0.5, 2.5), viability=100.0)
    g.freeze(low, bank, rng.randint(2, 50))
    return g.done()


def fam_t1(rng):  # restraint: a count that is not valid keeps today's total-count doublings
    g = Log(rng)
    fail = lambda: rng.choice([69.9, round(rng.uniform(1.0, 69.9), 1)])  # noqa: E731
    g.culture(g.thaw(viability=fail()), viability=100.0)  # seed from a failed thaw count
    c = g.culture(g.thaw(viability=100.0), viability=fail())  # failed harvest count
    g.culture(c, viability=round(rng.uniform(70.0, 100.0), 1))  # seed drawn from it
    return g.done()


def fam_t2(rng):  # restraint: a bank not in use keeps today's latest-freeze PDL
    g = Log(rng)
    bank = g.line["name"] + " MCB"
    c = g.culture(g.culture(g.thaw(viability=100.0), viability=100.0), viability=100.0)
    f1 = g.freeze(c, bank, rng.randint(1, 3))
    low = g.culture(c, gain=-rng.uniform(0.5, 2.5), viability=100.0)
    f2 = g.freeze(low, bank, rng.randint(1, 3))
    for f in (f1, f2):
        n = next(r["vials"] for r in g.records if r["id"] == f)
        for _ in range(n):
            g.thaw(vial=f, viability=100.0)
    return g.done()


FAMILIES = {
    "broad": fam_broad, "D1_viable_harvest": fam_d1, "D2_seed_source_viability": fam_d2,
    "D3_lineage_not_log_order": fam_d3, "D4_thaw_takes_vial_figures": fam_d4,
    "D5_thaw_is_not_a_passage": fam_d5, "D6_flag_on_age": fam_d6, "D7_near_band_three": fam_d7,
    "D8_vials_left_less_thaws": fam_d8, "D9_bank_pdl_highest_in_stock": fam_d9,
    "T1_invalid_count_keeps_todays_doublings": fam_t1, "T2_bank_not_in_use_keeps_latest_freeze_pdl": fam_t2,
}
TRAP_FAMILIES = {"T1_invalid_count_keeps_todays_doublings", "T2_bank_not_in_use_keeps_latest_freeze_pdl"}


def within(log):
    return jobgen._within_limits(log)


def build_logs():
    rng = random.Random(SEED)
    logs = {}
    for fam, maker in FAMILIES.items():
        logs[fam] = []
        while len(logs[fam]) < PER_FAMILY:
            log = maker(rng)
            if not within(log):
                continue
            trap = jobgen.has_failed_count(log) or jobgen.has_drained_bank(log)
            if (fam in TRAP_FAMILIES) != trap:
                raise SystemExit(f"family {fam} trap predicate violated")
            logs[fam].append(log)
    return logs


# ------------------------------------------------------------------ comparison
def close(g, e, path, out):
    if type(g) is not type(e):
        out.append(f"{path}: type {type(g).__name__} != {type(e).__name__}")
        return
    if isinstance(e, dict):
        if list(g.keys()) != list(e.keys()) and set(g.keys()) != set(e.keys()):
            out.append(f"{path}: keys {sorted(g)} != {sorted(e)}")
            return
        for k in e:
            close(g[k], e[k], f"{path}.{k}", out)
    elif isinstance(e, list):
        if len(g) != len(e):
            out.append(f"{path}: length {len(g)} != {len(e)}")
            return
        for i, (x, y) in enumerate(zip(g, e)):
            close(x, y, f"{path}[{i}]", out)
    elif isinstance(e, float):
        tol = 1e-9 * abs(e) if abs(e) >= 1 else 1e-9
        if not (math.isfinite(g) and abs(g - e) <= tol):
            out.append(f"{path}: {g!r} != {e!r}")
    elif g != e:
        out.append(f"{path}: {g!r} != {e!r}")


def run(app_dir, out_json):
    app_dir = Path(app_dir).resolve()
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest() != DRIVER_SHA:
        raise SystemExit("pristine driver copy changed")
    logs = build_logs()
    work = Path(tempfile.mkdtemp(prefix="cbscore"))
    (work / "tools").mkdir()
    shutil.copy2(DRIVER, work / "tools" / "cellbank_run.py")
    (work / "logs").mkdir()
    (work / "out").mkdir()
    (work / "out").chmod(0o777)
    names = []
    for fam, items in logs.items():
        for i, log in enumerate(items):
            name = hashlib.sha256(json.dumps(log, sort_keys=True).encode()).hexdigest()[:20]
            (work / "logs" / f"{name}.json").write_text(json.dumps(log))
            names.append((fam, i, name))
    for p in work.rglob("*"):
        p.chmod(p.stat().st_mode | 0o044 | (0o011 if p.is_dir() else 0))
    cmd = [
        "docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
        "-v", f"{work / 'tools'}:/app/tools:ro", "-v", f"{app_dir / 'src'}:/app/src:ro",
        "-v", f"{work / 'logs'}:/logs:ro", "-v", f"{work / 'out'}:/out", "-w", "/app", IMAGE,
        "sh", "-c",
        "for f in /logs/*.json; do b=$(basename $f .json); "
        "timeout 60 python3 -I /app/tools/cellbank_run.py $f > /out/$b.json 2> /out/$b.err; done",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    result = {"app_dir": str(app_dir), "seed": SEED, "per_family": PER_FAMILY, "image": IMAGE,
              "docker_exit": proc.returncode, "families": {}}
    for fam, i, name in names:
        entry = result["families"].setdefault(fam, {"logs": 0, "passed": 0, "first_failure": None})
        entry["logs"] += 1
        want = model.build_report(json.loads((work / "logs" / f"{name}.json").read_text()))
        diffs = []
        try:
            got = json.loads((work / "out" / f"{name}.json").read_text())
            close(got, want, "report", diffs)
        except Exception as exc:  # noqa: BLE001
            err = (work / "out" / f"{name}.err")
            diffs.append(f"no report: {exc}; stderr: {err.read_text()[-300:] if err.exists() else ''}")
        if diffs:
            if entry["first_failure"] is None:
                entry["first_failure"] = {"log": i, "diffs": diffs[:3]}
        else:
            entry["passed"] += 1
    for entry in result["families"].values():
        entry["family_pass"] = entry["passed"] == entry["logs"]
    result["failed_families"] = [f for f, e in result["families"].items() if not e["family_pass"]]
    result["verdict"] = "pass" if not result["failed_families"] else "fail"
    shutil.rmtree(work, ignore_errors=True)
    Path(out_json).write_text(json.dumps(result, indent=1) + "\n")
    return result


if __name__ == "__main__":
    res = run(sys.argv[1], sys.argv[2])
    print(res["verdict"], res["failed_families"])
