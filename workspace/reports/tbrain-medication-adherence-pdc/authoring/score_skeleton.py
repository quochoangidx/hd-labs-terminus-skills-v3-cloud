"""score_skeleton.py APP_DIR OUT_JSON: skeleton-probe scorer for tbrain-medication-adherence-pdc (authoring only).

Runs APP_DIR/src through our own pristine copy of the driver inside the local task image (--network none,
package read-only) on seeded claims files, one family per departure and per trap (trap families isolated,
broad families trap-free), and compares type-strictly with solution/model.py (pdc/rate numerically equal).
"""
import json, random, shutil, subprocess, sys, tempfile
from datetime import date, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-medication-adherence-pdc"
sys.path.insert(0, str(TASK / "solution")); sys.path.insert(0, str(HERE))
import model, gen
IMAGE = "tbrain-pdc:env"
PER = 6
D = lambda y, m, d: date(y, m, d).isoformat()
def F(dt, drug, c, days): return {"date": dt, "drug": drug, "class": c, "days": days}
def M(mid, fills, stays=()): return {"id": mid, "fills": fills, "stays": [list(s) for s in stays]}
def C(members, year): return {"plan": "SK", "year": year, "members": members}
def add(d0, k): return (date.fromisoformat(d0) + timedelta(days=k)).isoformat()

def measured_member(rng, y, mid, c="STA", drug=None, supply=30, n=None, start=None, stays=()):
    """In the measure; fills within the limit, spaced so they never overlap (trap/carry-over free)."""
    drug = drug or {"STA": "1111", "RAS": "2222"}[c]
    d = start or D(y, 1, 1 + rng.randint(0, 27))
    fills = []
    for _ in range(n or rng.randint(3, 8)):
        fills.append(F(d, drug, c, supply)); d = add(d, supply + rng.randint(0, 40))
        if date.fromisoformat(d).year != y: break
    if len(fills) < 2: fills.append(F(add(fills[0]["date"], 1 if supply == 1 else supply), drug, c, supply))
    return M(mid, fills, stays)

def fam_broad(rng):  # trap-free: every member in the measure, fills within the limit, no carry-over, classes < 10 measured
    y = rng.randint(2000, 2099)
    return C([measured_member(rng, y, f"B{k}", rng.choice(["STA", "RAS"])) for k in range(rng.randint(1, 8))], y)
def fam_d1_start(rng):  # a single 30-day fill on index + one late fill; start on fill date
    y = rng.randint(2000, 2099); s = D(y, rng.randint(1, 6), rng.randint(1, 28))
    return C([M("A1", [F(s, "1", "STA", 30), F(add(s, 60), "1", "STA", 30)])], y)
def fam_d2_carry(rng):  # early refill of the same drug
    y = rng.randint(2000, 2099); s = D(y, rng.randint(1, 6), rng.randint(1, 28)); e = rng.randint(1, 25)
    return C([M("A1", [F(s, "1", "STA", 30), F(add(s, 30 - e), "1", "STA", 30), F(add(s, 60 - e), "1", "STA", 30)])], y)
def fam_d2_otherdrug(rng):  # overlapping fills of two drugs do not move one another
    y = rng.randint(2000, 2099); s = D(y, rng.randint(1, 6), rng.randint(1, 28)); e = rng.randint(1, 25)
    return C([M("A1", [F(s, "1", "STA", 30), F(add(s, 30 - e), "2", "STA", 30), F(add(s, 150), "1", "STA", 30)])], y)
def fam_d3_period(rng):  # stops early: treatment period to year end
    y = rng.randint(2000, 2099); s = D(y, rng.randint(1, 3), rng.randint(1, 28))
    return C([M("A1", [F(s, "1", "STA", 30), F(add(s, 30), "1", "STA", 30)])], y)
def fam_d4_sameday(rng):  # two fills on one day only: not in measure (needs full composition too)
    y = rng.randint(2000, 2099); s = D(y, rng.randint(1, 6), rng.randint(1, 28))
    m1 = M("A1", [F(s, "1", "STA", 30), F(s, "2", "STA", 30)])
    return C([m1, measured_member(rng, y, "A2")], y)
def fam_d4_late(rng):  # index 90 / 89 days before year end
    y = rng.randint(2000, 2099); end = D(y, 12, 31)
    return C([M("A1", [F(add(end, -90), "1", "STA", 30), F(add(end, -40), "1", "STA", 30)]),
              M("A2", [F(add(end, -89), "1", "STA", 30), F(add(end, -40), "1", "STA", 30)])], y)
def fam_d5_stays(rng):
    y = rng.randint(2000, 2099); s = D(y, 1, rng.randint(1, 20)); a = add(s, rng.randint(40, 200))
    return C([measured_member(rng, y, "A1", start=s, stays=[(a, add(a, rng.randint(0, 20)))])], y)
def fam_d6_round(rng):  # PDC landing on x.x5 or between: 80 days covered from period 128 etc.
    y = rng.randint(2000, 2099)
    ms = []
    for k in range(4):
        s = D(y, rng.randint(1, 8), rng.randint(1, 28)); sup = rng.randint(5, 60)
        ms.append(M(f"R{k}", [F(s, "1", "STA", sup), F(add(s, rng.randint(sup, 120)), "1", "STA", sup)]))
    return C(ms, y)
def fam_d7_adherent(rng):  # PDC exactly 80.0 in measure
    y = 2001; s = "2001-07-05"  # period from Jul 5 to Dec 31 = 180 days; 144 covered
    return C([M("A1", [F(s, "1", "STA", 72), F(add(s, 100), "1", "STA", 72)])], y)
def fam_d8_rate(rng):  # reportable class (>=10 measured) plus non-measured members
    y = rng.randint(2000, 2099)
    ms = [measured_member(rng, y, f"P{k}", supply=rng.choice([30, 90])) for k in range(rng.randint(10, 14))]
    ms += [M(f"Q{k}", [F(D(y, 5, 1 + k), "1", "STA", 30)]) for k in range(rng.randint(1, 4))]
    return C(ms, y)
def fam_t1_outside(rng):  # TRAP 1: members outside the measure keep today's span
    y = rng.randint(2000, 2099); ms = []
    s = D(y, rng.randint(1, 6), rng.randint(1, 28))
    ms.append(M("O1", [F(s, "1", "STA", rng.randint(10, 60))], [(add(s, 3), add(s, 5))]))
    late = add(D(y, 12, 31), -rng.randint(10, 89))
    ms.append(M("O2", [F(late, "1", "STA", 30), F(add(late, 5), "1", "STA", 30)]))
    return C(ms, y)
def fam_t2_small_class(rng):  # TRAP 2: a class with fewer than ten members in the measure keeps today's divisor
    y = rng.randint(2000, 2099)
    ms = [measured_member(rng, y, f"S{k}", supply=30) for k in range(rng.randint(1, 5))]
    ms += [M(f"N{k}", [F(D(y, 3, 1 + k), "1", "STA", 30)]) for k in range(rng.randint(1, 4))]
    return C(ms, y)
def fam_t3_overlimit(rng):  # TRAP 3: a fill above the supply limit covers what today's step gives it
    y = rng.randint(2000, 2099); s = D(y, rng.randint(1, 3), rng.randint(1, 28))
    return C([M("L1", [F(s, "1", "STA", rng.randint(120, 365)), F(add(s, 250), "2", "STA", 30)])], y)

FAMILIES = {k[4:]: v for k, v in globals().items() if k.startswith("fam_")}

def run(app, claims):
    with tempfile.TemporaryDirectory() as t:
        Path(t, "c.json").write_text(json.dumps(claims))
        shutil.copytree(TASK / "environment" / "app" / "tools", Path(t, "tools"))
        p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{Path(app).resolve()}/src:/app/src:ro",
                            "-v", f"{t}/tools:/app/tools:ro", "-v", f"{t}/c.json:/data/c.json:ro", "-w", "/tmp", IMAGE,
                            "python3", "-I", "-S", "/app/tools/pdc_run.py", "/data/c.json"], capture_output=True, text=True, timeout=300)
        if p.returncode: return {"error": p.stderr[-500:]}
        return json.loads(p.stdout)

def same(a, e):
    if isinstance(e, dict):
        return isinstance(a, dict) and set(a) >= set(e) and all(same(a[k], e[k]) for k in e)
    if isinstance(e, list):
        return isinstance(a, list) and len(a) == len(e) and all(same(x, y) for x, y in zip(a, e))
    if isinstance(e, float):
        return isinstance(a, (int, float)) and not isinstance(a, bool) and a == e
    return type(a) is type(e) and a == e

def main(app, out):
    res = {}
    for name, fam in FAMILIES.items():
        ok = 0
        for i in range(PER):
            claims = fam(random.Random(f"{name}-{i}"))
            ok += same(run(app, claims), json.loads(json.dumps(model.report(claims))))
        res[name] = f"{ok}/{PER}"
        print(name, res[name], flush=True)
    solved = all(v == f"{PER}/{PER}" for v in res.values())
    Path(out).write_text(json.dumps({"families": res, "solved": solved}, indent=1))
    print("SOLVED" if solved else "NOT SOLVED")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
