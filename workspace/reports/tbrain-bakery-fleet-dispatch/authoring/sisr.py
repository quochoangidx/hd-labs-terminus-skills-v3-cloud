"""Authoring tool: slack-induced string removal (SISR) search for the dispatch plans.

Ruin: remove strings of consecutive customers from routes near a random seed customer
(or a whole route now and then). Recreate: insert the removed customers one at a time,
in a random order rule, at the cheapest feasible position, skipping positions with a
small "blink" probability; a new route of any available vehicle kind is an option.
After recreate, each route moves to the cheapest vehicle kind that can run it.
Acceptance: simulated annealing on the plan cost.

Usage: python3 sisr.py ORDERS.json OUT.json SECONDS SEED [START_PLAN.json]
"""

import json
import math
import random
import sys
import time


def dist(a, b):
    sq = (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2
    d = math.isqrt(sq)
    return d if d * d == sq else d + 1


class P:
    def __init__(self, inst):
        self.depot = inst["depot"]
        cust = inst["customers"]
        self.n = len(cust)
        nodes = [self.depot] + cust
        self.D = [[dist(a, b) for b in nodes] for a in nodes]
        self.ready = [self.depot["open"]] + [c["ready"] for c in cust]
        self.due = [self.depot["close"]] + [c["due"] for c in cust]
        self.svc = [0] + [c["service"] for c in cust]
        self.dem = [0] + [c["demand"] for c in cust]
        self.ids = [0] + [c["id"] for c in cust]
        self.fleet = inst["fleet"]
        self.near = [sorted(range(1, self.n + 1), key=lambda j: self.D[i][j]) for i in range(self.n + 1)]
        self.open = self.depot["open"]
        self.close = self.depot["close"]

    def evaluate(self, ti, stops):
        """Cost of the route on vehicle kind ti, or None if it cannot run."""
        f = self.fleet[ti]
        load = 0
        dem = self.dem
        for s in stops:
            load += dem[s]
        if load > f["capacity"]:
            return None
        D, pace, ready, due, svc = self.D, f["pace"], self.ready, self.due, self.svc
        t = self.open
        prev = 0
        d = 0
        waits = 0
        fts = 1 << 60
        for s in stops:
            leg = D[prev][s]
            d += leg
            arrive = t + leg * pace
            if arrive < ready[s]:
                waits += ready[s] - arrive
                start = ready[s]
            else:
                start = arrive
            if start > due[s]:
                return None
            slack = waits + due[s] - start
            if slack < fts:
                fts = slack
            t = start + svc[s]
            prev = s
        leg = D[prev][0]
        d += leg
        back = t + leg * pace
        if back > self.close:
            return None
        rng_ = f["range"]
        if rng_ is not None and d > rng_:
            return None
        delay = min(fts, waits)
        if back - self.open - delay > f["shift"]:
            return None
        return f["fixed"] + f["per_unit"] * d

    def depart(self, ti, stops):
        f = self.fleet[ti]
        t, prev, waits, fts = self.open, 0, 0, 1 << 60
        for s in stops:
            leg = self.D[prev][s]
            arrive = t + leg * f["pace"]
            start = max(arrive, self.ready[s])
            waits += start - arrive
            fts = min(fts, waits + self.due[s] - start)
            t = start + self.svc[s]
            prev = s
        return self.open + min(fts, waits)


class Sol:
    __slots__ = ("routes", "kinds", "costs", "where")

    def __init__(self, n):
        self.routes, self.kinds, self.costs = [], [], []
        self.where = [None] * (n + 1)

    def copy(self):
        s = Sol.__new__(Sol)
        s.routes = [list(r) for r in self.routes]
        s.kinds = list(self.kinds)
        s.costs = list(self.costs)
        s.where = list(self.where)
        return s

    def total(self):
        return sum(self.costs)

    def reindex(self):
        for ri, r in enumerate(self.routes):
            for s in r:
                self.where[s] = ri


def used(sol, ti):
    return sum(1 for k in sol.kinds if k == ti)


def insert_best(p, sol, c, rng, blink):
    best = None
    dem_c = p.dem[c]
    for ri, r in enumerate(sol.routes):
        ti = sol.kinds[ri]
        f = p.fleet[ti]
        if sum(p.dem[s] for s in r) + dem_c > f["capacity"]:
            continue
        base = sol.costs[ri]
        for pos in range(len(r) + 1):
            if rng.random() < blink:
                continue
            prev = r[pos - 1] if pos else 0
            nxt = r[pos] if pos < len(r) else 0
            lower = f["per_unit"] * (p.D[prev][c] + p.D[c][nxt] - p.D[prev][nxt])
            if best is not None and lower >= best[0]:
                continue
            nc = p.evaluate(ti, r[:pos] + [c] + r[pos:])
            if nc is None:
                continue
            delta = nc - base
            if best is None or delta < best[0]:
                best = (delta, ri, pos, nc)
    for ti, f in enumerate(p.fleet):
        if used(sol, ti) < f["count"]:
            nc = p.evaluate(ti, [c])
            if nc is not None and (best is None or nc < best[0]):
                best = (nc, None, ti, nc)
    if best is None:
        return False
    _, ri, pos, nc = best
    if ri is None:
        sol.routes.append([c])
        sol.kinds.append(pos)
        sol.costs.append(nc)
    else:
        sol.routes[ri].insert(pos, c)
        sol.costs[ri] = nc
    return True


def downsize(p, sol):
    for ri, r in enumerate(sol.routes):
        for tj in range(len(p.fleet)):
            if tj == sol.kinds[ri] or used(sol, tj) >= p.fleet[tj]["count"]:
                continue
            nc = p.evaluate(tj, r)
            if nc is not None and nc < sol.costs[ri]:
                sol.kinds[ri], sol.costs[ri] = tj, nc


def swap_kinds(p, sol, rng, tries=12):
    """Swap the vehicle kinds of two routes when both can run and the pair gets cheaper."""
    n = len(sol.routes)
    if n < 2:
        return
    for _ in range(tries):
        i, j = rng.randrange(n), rng.randrange(n)
        if i == j or sol.kinds[i] == sol.kinds[j]:
            continue
        ci = p.evaluate(sol.kinds[j], sol.routes[i])
        if ci is None:
            continue
        cj = p.evaluate(sol.kinds[i], sol.routes[j])
        if cj is None:
            continue
        if ci + cj < sol.costs[i] + sol.costs[j]:
            sol.kinds[i], sol.kinds[j] = sol.kinds[j], sol.kinds[i]
            sol.costs[i], sol.costs[j] = ci, cj


def ruin(p, sol, rng, avg_len):
    removed = []
    if rng.random() < 0.08 and sol.routes:
        ri = rng.randrange(len(sol.routes))
        removed = list(sol.routes[ri])
        sol.routes[ri] = []
    else:
        cmax = min(10, avg_len)
        ks = max(1, int(rng.uniform(1, 4 * 10 / (1 + cmax) + 1)))
        seed = rng.randint(1, p.n)
        done = set()
        for c in p.near[seed]:
            if len(done) >= ks:
                break
            ri = sol.where[c]
            if ri is None or ri in done or not sol.routes[ri]:
                continue
            r = sol.routes[ri]
            lmax = min(len(r), cmax)
            length = rng.randint(1, lmax)
            i = r.index(c)
            start = rng.randint(max(0, i - length + 1), min(i, len(r) - length))
            removed.extend(r[start:start + length])
            del r[start:start + length]
            done.add(ri)
    keep = [i for i, r in enumerate(sol.routes) if r]
    sol.routes = [sol.routes[i] for i in keep]
    sol.kinds = [sol.kinds[i] for i in keep]
    sol.costs = [p.evaluate(sol.kinds[i], sol.routes[i]) if True else 0 for i in range(len(keep))]
    sol.where = [None] * (p.n + 1)
    sol.reindex()
    return removed


def recreate(p, sol, removed, rng):
    rule = rng.random()
    if rule < 0.4:
        rng.shuffle(removed)
    elif rule < 0.65:
        removed.sort(key=lambda c: -p.dem[c])
    elif rule < 0.85:
        removed.sort(key=lambda c: -p.D[0][c])
    else:
        removed.sort(key=lambda c: p.due[c] - p.ready[c])
    for c in removed:
        if not insert_best(p, sol, c, rng, 0.01):
            return False
    downsize(p, sol)
    swap_kinds(p, sol, rng)
    sol.where = [None] * (p.n + 1)
    sol.reindex()
    return True


def initial(p, rng):
    sol = Sol(p.n)
    order = list(range(1, p.n + 1))
    order.sort(key=lambda c: p.due[c])
    for c in order:
        if not insert_best(p, sol, c, rng, 0.0):
            raise SystemExit("no feasible start")
    downsize(p, sol)
    sol.reindex()
    return sol


def from_plan(p, plan):
    sol = Sol(p.n)
    index = {cid: i for i, cid in enumerate(p.ids)}
    kinds = {f["type"]: i for i, f in enumerate(p.fleet)}
    for r in plan["routes"]:
        ti = kinds[r["type"]]
        stops = [index[c] for c in r["stops"]]
        cost = p.evaluate(ti, stops)
        assert cost is not None
        sol.routes.append(stops)
        sol.kinds.append(ti)
        sol.costs.append(cost)
    sol.reindex()
    return sol


def search(p, seconds, seed, start):
    rng = random.Random(seed)
    cur = from_plan(p, start) if start else initial(p, rng)
    best = cur.copy()
    t0 = time.time()
    t_start, t_end = 0.004 * cur.total() / max(1, len(cur.routes)), 1.0
    it = 0
    while True:
        el = time.time() - t0
        if el > seconds:
            break
        temp = t_start * (t_end / t_start) ** (el / seconds)
        cand = cur.copy()
        avg = max(1, p.n // max(1, len(cand.routes)))
        removed = ruin(p, cand, rng, avg)
        if not recreate(p, cand, removed, rng):
            continue
        cc = cand.total()
        if cc < cur.total() - temp * math.log(rng.random()):
            cur = cand
            if cc < best.total():
                best = cand.copy()
        it += 1
    return best, it


def to_plan(p, sol):
    return {"routes": [{"type": p.fleet[k]["type"], "depart": p.depart(k, r), "stops": [p.ids[s] for s in r]}
                       for r, k in zip(sol.routes, sol.kinds)]}


if __name__ == "__main__":
    inst = json.load(open(sys.argv[1]))
    p = P(inst)
    start = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
    best, it = search(p, float(sys.argv[3]), int(sys.argv[4]), start)
    json.dump(to_plan(p, best), open(sys.argv[2], "w"))
    print(sys.argv[1], best.total(), len(best.routes), "iterations", it, flush=True)
