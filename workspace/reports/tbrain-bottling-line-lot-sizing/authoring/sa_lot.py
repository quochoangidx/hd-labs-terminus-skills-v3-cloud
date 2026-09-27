"""Authoring tool: simulated annealing for lot-sizing plans.

State: batches x[(p, l, d)] >= 0; every state keeps line capacity. Moves: shift
some batches of a product to another day and/or line; merge a run into another
run of the same product (saves a setup); add or remove batches; split off part
of a run to another day. Cost recomputed per touched product (T days) plus setups.

Usage: python3 sa_lot.py SITE.json OUT.json SECONDS SEED [START.json] [T0] [T1]
"""
import json, math, random, sys, time
sys.path.insert(0, "../../../tasks/tbrain-bottling-line-lot-sizing/environment/app/tools")
from check_plan import evaluate


class P:
    def __init__(s, site):
        s.T = site["days"]; s.site = site
        s.L = [l["id"] for l in site["lines"]]; s.cap = {l["id"]: l["capacity_minutes"] for l in site["lines"]}
        s.prods = site["products"]; s.pid = [p["id"] for p in s.prods]
        s.el = [[(l, p["lines"][l]) for l in p["lines"]] for p in s.prods]
        s.spec = [{l: p["lines"][l] for l in p["lines"]} for p in s.prods]


def prod_cost(s, i, made):
    p = s.prods[i]; st = p["initial_stock"]; c = 0
    for d in range(s.T):
        st += made[d] - p["demand"][d]
        c += p["holding_cost"] * st if st > 0 else p["backlog_cost"] * -st
    return c


def search(s, secs, seed, start, T0, T1):
    rng = random.Random(seed)
    x = {}
    for r in start["runs"]:
        x[(s.pid.index(r["product"]), r["line"], r["day"])] = r["batches"]
    used = {(l, d): 0 for l in s.L for d in range(s.T)}
    for (i, l, d), n in x.items():
        sp = s.spec[i][l]; used[(l, d)] += sp["setup_minutes"] + n * sp["minutes_per_batch"]
    made = [[0] * s.T for _ in s.prods]
    for (i, l, d), n in x.items(): made[i][d] += n
    pc = [prod_cost(s, i, made[i]) for i in range(len(s.prods))]
    setup = sum(s.spec[i][l]["setup_cost"] for (i, l, d) in x)
    cur = sum(pc) + setup; best = cur; bestx = dict(x)
    t0 = time.time(); it = 0; T = T0
    NP = len(s.prods)

    def mins(i, l, n):
        sp = s.spec[i][l]; return sp["setup_minutes"] + n * sp["minutes_per_batch"] if n > 0 else 0

    while True:
        it += 1
        if it & 255 == 0:
            el = time.time() - t0
            if el > secs: break
            T = T0 * (T1 / T0) ** (el / secs)
        r = rng.random()
        i = rng.randrange(NP)
        el_ = s.el[i]
        # build a change: dict key->new batches
        ch = {}
        if r < 0.35:      # shift k batches from an existing run to another (line, day)
            runs = [k for k in x if k[0] == i]
            if not runs: continue
            k = rng.choice(runs); n = x[k]
            m = rng.randint(1, n) if rng.random() < 0.5 else n
            l2 = rng.choice(el_)[0]; d2 = k[2] + rng.choice([-3, -2, -1, -1, 1, 1, 2, 3]) if rng.random() < 0.7 else rng.randrange(s.T)
            if not 0 <= d2 < s.T: continue
            k2 = (i, l2, d2)
            if k2 == k: continue
            ch[k] = n - m; ch[k2] = x.get(k2, 0) + m
        elif r < 0.55:    # merge run into another run of same product
            runs = [k for k in x if k[0] == i]
            if len(runs) < 2: continue
            a, b = rng.sample(runs, 2)
            ch[a] = 0; ch[b] = x[b] + x[a]
        elif r < 0.85:    # add / remove batches
            l = rng.choice(el_)[0]; d = rng.randrange(s.T); k = (i, l, d)
            n = x.get(k, 0); dn = rng.choice([-2, -1, -1, 1, 1, 2]) if n else rng.randint(1, 4)
            if n + dn < 0: continue
            ch[k] = n + dn
        else:             # move one run of product i and one of product j between days (swap slots)
            runs = [k for k in x if k[0] == i]
            if not runs: continue
            k = rng.choice(runs); d2 = rng.randrange(s.T); k2 = (i, k[1], d2)
            if k2 in x or d2 == k[2]: continue
            ch[k] = 0; ch[k2] = x[k]
        # feasibility
        du = {}
        for k, nn in ch.items():
            i2, l, d = k; old = x.get(k, 0)
            du[(l, d)] = du.get((l, d), 0) + mins(i2, l, nn) - mins(i2, l, old)
        if any(used[ld] + v > s.cap[ld[0]][ld[1]] for ld, v in du.items() if v > 0): continue
        # delta
        dsetup = sum(s.spec[k[0]][k[1]]["setup_cost"] * ((nn > 0) - (x.get(k, 0) > 0)) for k, nn in ch.items())
        touched = {k[0] for k in ch}
        newmade = {}
        for i2 in touched:
            mm = list(made[i2])
            for k, nn in ch.items():
                if k[0] == i2: mm[k[2]] += nn - x.get(k, 0)
            newmade[i2] = mm
        newpc = {i2: prod_cost(s, i2, newmade[i2]) for i2 in touched}
        delta = dsetup + sum(newpc[i2] - pc[i2] for i2 in touched)
        if delta <= 0 or rng.random() < math.exp(-delta / T):
            for ld, v in du.items(): used[ld] += v
            for k, nn in ch.items():
                if nn > 0: x[k] = nn
                else: x.pop(k, None)
            for i2 in touched: made[i2] = newmade[i2]; pc[i2] = newpc[i2]
            cur += delta
            if cur < best: best = cur; bestx = dict(x)
    return best, bestx, it


def to_plan(s, x):
    return {"runs": [{"day": d, "line": l, "product": s.pid[i], "batches": n} for (i, l, d), n in sorted(x.items(), key=lambda t: (t[0][2], t[0][1], t[0][0]))]}


if __name__ == "__main__":
    site = json.load(open(sys.argv[1])); s = P(site)
    if len(sys.argv) > 5 and sys.argv[5] != "-":
        start = json.load(open(sys.argv[5]))
    else:
        start = {"runs": []}
    T0 = float(sys.argv[6]) if len(sys.argv) > 6 else 300.0
    T1 = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0
    best, x, it = search(s, float(sys.argv[3]), int(sys.argv[4]), start, T0, T1)
    plan = to_plan(s, x)
    assert evaluate(site, plan) == best, (evaluate(site, plan), best)
    json.dump(plan, open(sys.argv[2], "w"))
    print(sys.argv[1].split("/")[-1], best, "iterations", it, flush=True)
