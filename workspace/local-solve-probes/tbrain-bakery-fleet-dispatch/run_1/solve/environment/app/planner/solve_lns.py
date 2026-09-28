"""Large-neighbourhood-search planner for the morning dispatch problem.

Usage: python3 planner/solve_lns.py orders/<m>.json plans/<m>.json <seconds> [seed]

Only the Python 3 standard library is used.
"""

import json
import math
import random
import sys
import time


def dist(a, b):
    sq = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
    d = math.isqrt(sq)
    return d if d * d == sq else d + 1


class Problem:
    def __init__(self, orders):
        depot = orders["depot"]
        self.open = depot["open"]
        self.close = depot["close"]
        cs = orders["customers"]
        self.n = len(cs)
        self.ids = [0] + [c["id"] for c in cs]
        pts = [(depot["x"], depot["y"])] + [(c["x"], c["y"]) for c in cs]
        self.pts = pts
        m = len(pts)
        self.D = [[0] * m for _ in range(m)]
        for i in range(m):
            Di = self.D[i]
            pi = pts[i]
            for j in range(m):
                Di[j] = dist(pi, pts[j])
        self.dem = [0] + [c["demand"] for c in cs]
        self.ready = [self.open] + [c["ready"] for c in cs]
        self.due = [self.close] + [c["due"] for c in cs]
        self.srv = [0] + [c["service"] for c in cs]
        self.fleet = orders["fleet"]
        self.types = [f["type"] for f in self.fleet]
        self.F = {f["type"]: f for f in self.fleet}
        # neighbour lists (by index 1..n)
        K = min(30, self.n - 1)
        self.nbr = [[] for _ in range(m)]
        for i in range(1, m):
            order = sorted(range(1, m), key=lambda j: self.D[i][j])
            self.nbr[i] = [j for j in order if j != i][:K]


class Route:
    __slots__ = ("vt", "stops", "load", "dist", "e", "l", "cost", "depart", "ok")

    def __init__(self, vt, stops):
        self.vt = vt
        self.stops = stops


class Solver:
    def __init__(self, prob, seed=0):
        self.p = prob
        self.rng = random.Random(seed)

    # ---------- route evaluation ----------
    def full_eval(self, vt, stops):
        """Return (dist, depart, cost) or None when infeasible."""
        p = self.p
        f = p.F[vt]
        pace = f["pace"]
        load = 0
        for s in stops:
            load += p.dem[s]
        if load > f["capacity"]:
            return None
        D = p.D
        d = D[0][stops[0]] + D[stops[-1]][0]
        for a, b in zip(stops, stops[1:]):
            d += D[a][b]
        rng = f["range"]
        if rng is not None and d > rng:
            return None
        latest = p.close
        nxt = 0
        for c in reversed(stops):
            latest = min(p.due[c], latest - p.srv[c] - D[c][nxt] * pace)
            if latest < p.ready[c]:
                return None
            nxt = c
        depart = latest - D[0][stops[0]] * pace
        if depart < p.open:
            return None
        clock = depart
        here = 0
        for c in stops:
            st = clock + D[here][c] * pace
            if st < p.ready[c]:
                st = p.ready[c]
            if st > p.due[c]:
                return None
            clock = st + p.srv[c]
            here = c
        back = clock + D[here][0] * pace
        if back > p.close or back - depart > f["shift"]:
            return None
        return d, depart, f["fixed"] + f["per_unit"] * d

    def refresh(self, r):
        """Recompute cached arrays for a feasible route."""
        p = self.p
        f = p.F[r.vt]
        pace = f["pace"]
        D = p.D
        stops = r.stops
        res = self.full_eval(r.vt, stops)
        if res is None:
            r.ok = False
            return False
        r.dist, r.depart, r.cost = res
        r.load = sum(p.dem[s] for s in stops)
        # earliest starts with depart = open
        e = []
        clock = p.open
        here = 0
        for c in stops:
            st = clock + D[here][c] * pace
            if st < p.ready[c]:
                st = p.ready[c]
            e.append(st)
            clock = st + p.srv[c]
            here = c
        # latest starts
        l = [0] * len(stops)
        latest = p.close
        nxt = 0
        for i in range(len(stops) - 1, -1, -1):
            c = stops[i]
            latest = min(p.due[c], latest - p.srv[c] - D[c][nxt] * pace)
            l[i] = latest
            nxt = c
        r.e = e
        r.l = l
        r.ok = True
        return True

    # ---------- solution bookkeeping ----------
    def sol_cost(self, routes):
        return sum(r.cost for r in routes)

    def used_counts(self, routes):
        u = {t: 0 for t in self.p.types}
        for r in routes:
            u[r.vt] += 1
        return u

    # ---------- insertion ----------
    def insertion_candidates(self, u, routes, where):
        """Yield (delta_cost, route_index, position) for feasible-looking spots."""
        p = self.p
        D = p.D
        du = p.due[u]
        ru = p.ready[u]
        su = p.srv[u]
        demu = p.dem[u]
        out = []
        seen = set()
        for r_i, pos_list in where.items():
            r = routes[r_i]
            f = p.F[r.vt]
            if r.load + demu > f["capacity"]:
                continue
            pace = f["pace"]
            pu = f["per_unit"]
            rng = f["range"]
            stops = r.stops
            e = r.e
            l = r.l
            L = len(stops)
            for pos in pos_list:
                key = (r_i, pos)
                if key in seen:
                    continue
                seen.add(key)
                prev = stops[pos - 1] if pos > 0 else 0
                nxt = stops[pos] if pos < L else 0
                delta_d = D[prev][u] + D[u][nxt] - D[prev][nxt]
                if rng is not None and r.dist + delta_d > rng:
                    continue
                fin_prev = p.open if pos == 0 else e[pos - 1] + p.srv[prev]
                st = fin_prev + D[prev][u] * pace
                if st < ru:
                    st = ru
                if st > du:
                    continue
                lat_next = l[pos] if pos < L else p.close
                if st + su + D[u][nxt] * pace > lat_next:
                    continue
                out.append((pu * delta_d, r_i, pos))
        return out

    def new_route_options(self, u, used):
        p = self.p
        best = []
        for t in p.types:
            if used[t] >= p.F[t]["count"]:
                continue
            res = self.full_eval(t, [u])
            if res is None:
                continue
            best.append((res[2], t))
        best.sort()
        return best

    def upgrade_options(self, u, routes, used):
        """Fallback: re-type a route to a bigger free vehicle so u fits in it."""
        p = self.p
        out = []
        for r_i, r in enumerate(routes):
            for t in p.types:
                if t == r.vt or used[t] >= p.F[t]["count"]:
                    continue
                if p.F[t]["capacity"] < r.load + p.dem[u]:
                    continue
                best = None
                for pos in range(len(r.stops) + 1):
                    new = r.stops[:pos] + [u] + r.stops[pos:]
                    res = self.full_eval(t, new)
                    if res is not None and (best is None or res[2] < best[0]):
                        best = (res[2], pos)
                if best is not None:
                    out.append((best[0] - r.cost, r_i, best[1], t))
        out.sort(key=lambda z: z[0])
        return out

    def where_map(self, u, routes, pos_of):
        """Candidate positions near u: around its nearest assigned neighbours."""
        where = {}
        for v in self.p.nbr[u]:
            loc = pos_of.get(v)
            if loc is None:
                continue
            r_i, idx = loc
            where.setdefault(r_i, set()).update((idx, idx + 1))
        return where

    def repair(self, routes, pool, used, noise=0.0):
        """Regret-2 insertion of customers in pool. Returns the leftovers."""
        p = self.p
        pos_of = {}
        for r_i, r in enumerate(routes):
            for i, c in enumerate(r.stops):
                pos_of[c] = (r_i, i)
        pool = list(pool)
        rng = self.rng
        left = []
        while pool:
            best_u = None
            best_score = None
            best_move = None
            for u in pool:
                where = self.where_map(u, routes, pos_of)
                cands = self.insertion_candidates(u, routes, where)
                nr = self.new_route_options(u, used)
                opts = []
                for c, r_i, pos in cands:
                    if noise:
                        c += rng.uniform(0, noise)
                    opts.append((c, ("ins", r_i, pos)))
                if nr:
                    c = nr[0][0]
                    if noise:
                        c += rng.uniform(0, noise)
                    opts.append((c, ("new", nr[0][1], 0)))
                    if len(nr) > 1:
                        opts.append((nr[1][0], ("new", nr[1][1], 0)))
                if not opts:
                    for delta, r_i, pos, t in self.upgrade_options(u, routes, used)[:2]:
                        opts.append((delta, ("up", r_i, pos, t)))
                if not opts:
                    left.append(u)
                    pool.remove(u)
                    break
                opts.sort(key=lambda z: z[0])
                first = opts[0]
                second = opts[1][0] if len(opts) > 1 else first[0] + 100000
                regret = second - first[0]
                score = (regret, -first[0])
                if best_score is None or score > best_score:
                    best_score = score
                    best_u = u
                    best_move = first[1]
            if best_u is None:
                continue
            u = best_u
            kind, a, b = best_move[0], best_move[1], best_move[2]
            placed = False
            if kind == "up":
                r = routes[a]
                t = best_move[3]
                old_stops, old_t = r.stops, r.vt
                r.stops = old_stops[:b] + [u] + old_stops[b:]
                r.vt = t
                if self.refresh(r):
                    used[old_t] -= 1
                    used[t] += 1
                    placed = True
                else:
                    r.stops, r.vt = old_stops, old_t
                    self.refresh(r)
            elif kind == "ins":
                r = routes[a]
                old = r.stops
                r.stops = old[:b] + [u] + old[b:]
                if self.refresh(r):
                    placed = True
                else:
                    r.stops = old
                    self.refresh(r)
            if not placed:
                if kind != "new":
                    nr = self.new_route_options(u, used)
                    if not nr:
                        left.append(u)
                        pool.remove(u)
                        continue
                    a = nr[0][1]
                r = Route(a, [u])
                if not self.refresh(r):
                    left.append(u)
                    pool.remove(u)
                    continue
                routes.append(r)
                used[a] += 1
            pool.remove(u)
            pos_of = {}
            for r_i, rr in enumerate(routes):
                for i, c in enumerate(rr.stops):
                    pos_of[c] = (r_i, i)
        return left

    # ---------- improvement ----------
    def retype(self, routes, used):
        """Give each route the cheapest feasible vehicle type."""
        p = self.p
        changed = False
        for r in routes:
            best = (r.cost, r.vt)
            for t in p.types:
                if t == r.vt:
                    continue
                if used[t] >= p.F[t]["count"]:
                    continue
                res = self.full_eval(t, r.stops)
                if res is None:
                    continue
                if res[2] < best[0]:
                    best = (res[2], t)
            if best[1] != r.vt:
                used[r.vt] -= 1
                used[best[1]] += 1
                r.vt = best[1]
                self.refresh(r)
                changed = True
        return changed

    def intra_opt(self, r):
        """Or-opt and 2-opt inside one route."""
        improved = True
        any_change = False
        while improved:
            improved = False
            L = len(r.stops)
            if L < 3:
                break
            base = r.cost
            for i in range(L - 1):
                for j in range(i + 2, L + 1):
                    new = r.stops[:i] + r.stops[i:j][::-1] + r.stops[j:]
                    res = self.full_eval(r.vt, new)
                    if res is not None and res[2] < base - 1e-9:
                        r.stops = new
                        self.refresh(r)
                        base = r.cost
                        improved = True
                        any_change = True
                        break
                if improved:
                    break
            if improved:
                continue
            for seg in (1, 2, 3):
                for i in range(L - seg + 1):
                    piece = r.stops[i:i + seg]
                    rest = r.stops[:i] + r.stops[i + seg:]
                    for k in range(len(rest) + 1):
                        if k == i:
                            continue
                        new = rest[:k] + piece + rest[k:]
                        res = self.full_eval(r.vt, new)
                        if res is not None and res[2] < base - 1e-9:
                            r.stops = new
                            self.refresh(r)
                            base = r.cost
                            improved = True
                            any_change = True
                            break
                    if improved:
                        break
                if improved:
                    break
        return any_change

    def inter_opt(self, routes, used, passes=2):
        """Relocate single customers between routes while cost falls."""
        p = self.p
        D = p.D
        for _ in range(passes):
            changed = False
            pos_of = {}
            for r_i, r in enumerate(routes):
                for i, c in enumerate(r.stops):
                    pos_of[c] = (r_i, i)
            order = list(pos_of)
            self.rng.shuffle(order)
            for u in order:
                loc = pos_of.get(u)
                if loc is None:
                    continue
                src_i, idx = loc
                src = routes[src_i]
                if src.stops[idx] != u:
                    continue
                rest = src.stops[:idx] + src.stops[idx + 1:]
                if rest:
                    res = self.full_eval(src.vt, rest)
                    if res is None:
                        continue
                    gain = src.cost - res[2]
                    new_src_cost = res[2]
                else:
                    gain = src.cost
                    new_src_cost = 0
                where = {}
                for v in p.nbr[u]:
                    l2 = pos_of.get(v)
                    if l2 is None or l2[0] == src_i:
                        continue
                    where.setdefault(l2[0], set()).update((l2[1], l2[1] + 1))
                cands = self.insertion_candidates(u, routes, where)
                cands.sort(key=lambda z: z[0])
                done = False
                for delta, r_j, pos in cands[:6]:
                    if delta >= gain:
                        break
                    tgt = routes[r_j]
                    old = tgt.stops
                    old_tgt_cost = tgt.cost
                    tgt.stops = old[:pos] + [u] + old[pos:]
                    if not self.refresh(tgt):
                        tgt.stops = old
                        self.refresh(tgt)
                        continue
                    if tgt.cost - old_tgt_cost < gain - 0.5:
                        src.stops = rest
                        if rest:
                            self.refresh(src)
                        changed = True
                        done = True
                        break
                    tgt.stops = old
                    self.refresh(tgt)
                if done:
                    if not src.stops:
                        used[src.vt] -= 1
                        routes.remove(src)
                    pos_of = {}
                    for r_i, r in enumerate(routes):
                        for i, c in enumerate(r.stops):
                            pos_of[c] = (r_i, i)
            if not changed:
                break
        return routes

    # ---------- removal ----------
    def remove(self, routes, q):
        p = self.p
        rng = self.rng
        assigned = [(c, r_i) for r_i, r in enumerate(routes) for c in r.stops]
        if not assigned:
            return []
        op = rng.random()
        pool = set()
        if op < 0.30:
            for c, _ in rng.sample(assigned, min(q, len(assigned))):
                pool.add(c)
        elif op < 0.75:
            seed = rng.choice(assigned)[0]
            order = [seed] + [v for v in p.nbr[seed]]
            in_sol = {c for c, _ in assigned}
            for v in order:
                if len(pool) >= q:
                    break
                if v in in_sol:
                    pool.add(v)
            while len(pool) < q and len(pool) < len(assigned):
                pool.add(rng.choice(assigned)[0])
        else:
            idxs = list(range(len(routes)))
            rng.shuffle(idxs)
            for r_i in idxs:
                if len(pool) >= q:
                    break
                pool.update(routes[r_i].stops)
        for r in routes:
            r.stops = [c for c in r.stops if c not in pool]
        return list(pool)

    def clean(self, routes, used):
        keep = []
        for r in routes:
            if r.stops:
                keep.append(r)
            else:
                used[r.vt] -= 1
        return keep

    def copy_routes(self, routes):
        out = []
        for r in routes:
            nr = Route(r.vt, list(r.stops))
            nr.load = r.load
            nr.dist = r.dist
            nr.e = r.e
            nr.l = r.l
            nr.cost = r.cost
            nr.depart = r.depart
            nr.ok = r.ok
            out.append(nr)
        return out

    # ---------- main ----------
    PEN = 200000

    def solve(self, tlimit):
        p = self.p
        deadline = time.time() + tlimit
        routes = []
        used = {t: 0 for t in p.types}
        pool = list(range(1, p.n + 1))
        # seed order: tight windows first
        pool.sort(key=lambda c: (p.due[c], -p.dem[c]))
        un = self.repair(routes, pool, used)
        routes = self.clean(routes, used)
        self.retype(routes, used)
        for r in routes:
            self.intra_opt(r)
        routes = self.inter_opt(routes, used, passes=3)
        for r in routes:
            self.intra_opt(r)
        cur = routes
        cur_un = un
        cur_cost = self.sol_cost(cur) + self.PEN * len(cur_un)
        best = self.copy_routes(cur)
        best_un = list(cur_un)
        best_cost = cur_cost
        cur_used = dict(used)
        best_used = dict(used)
        import os
        T0 = max(1.0, float(os.environ.get("TFAC", "0.0015")) * self.sol_cost(cur))
        it = 0
        last_report = time.time()
        while time.time() < deadline:
            it += 1
            frac = 1.0 - (deadline - time.time()) / tlimit
            T = T0 * (0.02 ** frac)
            cand = self.copy_routes(cur)
            cand_used = dict(cur_used)
            q = self.rng.randint(max(2, p.n // 50), max(4, p.n // 6))
            pool = self.remove(cand, q) + list(cur_un)
            cand = self.clean(cand, cand_used)
            noise = self.rng.choice([0.0, 0.0, 30.0, 120.0])
            cand_un = self.repair(cand, pool, cand_used, noise)
            cand = self.clean(cand, cand_used)
            if self.rng.random() < 0.25:
                self.retype(cand, cand_used)
            if self.rng.random() < 0.35:
                for r in cand:
                    if len(r.stops) > 2:
                        self.intra_opt(r)
            if not cand_un and self.rng.random() < 0.25:
                cand = self.inter_opt(cand, cand_used, passes=1)
            c = self.sol_cost(cand) + self.PEN * len(cand_un)
            if c < cur_cost or self.rng.random() < math.exp(-min(50.0, (c - cur_cost) / max(T, 1e-9))):
                cur = cand
                cur_cost = c
                cur_un = cand_un
                cur_used = cand_used
                if c < best_cost:
                    best_cost = c
                    best = self.copy_routes(cand)
                    best_un = list(cand_un)
                    best_used = dict(cand_used)
            if time.time() - last_report > 30:
                last_report = time.time()
                print(f"  it={it} best={best_cost} un={len(best_un)}", file=sys.stderr, flush=True)
        # final polish
        for _ in range(3):
            for r in best:
                self.intra_opt(r)
            self.retype(best, best_used)
            best = self.inter_opt(best, best_used, passes=3)
        for r in best:
            self.intra_opt(r)
        best_cost = self.sol_cost(best) + self.PEN * len(best_un)
        return best, best_cost, it, len(best_un)


def to_plan(prob, routes):
    out = []
    for r in routes:
        out.append({
            "type": r.vt,
            "depart": int(r.depart),
            "stops": [int(prob.ids[s]) for s in r.stops],
        })
    return {"routes": out}


def main(argv):
    orders_path, plan_path, tl = argv[1], argv[2], float(argv[3])
    seed = int(argv[4]) if len(argv) > 4 else 12345
    with open(orders_path) as fh:
        orders = json.load(fh)
    prob = Problem(orders)
    best = None
    best_cost = None
    # multi-start within the budget
    starts = int(__import__("os").environ.get("STARTS", "1"))
    slice_t = tl / starts
    for k in range(starts):
        s = Solver(prob, seed + 977 * k)
        routes, cost, it, nun = s.solve(slice_t)
        print(f"start {k}: cost {cost} un={nun} after {it} iterations", file=sys.stderr, flush=True)
        if nun:
            continue
        if best_cost is None or cost < best_cost:
            best, best_cost = routes, cost
    plan = to_plan(prob, best)
    with open(plan_path, "w") as fh:
        json.dump(plan, fh)
    print(f"{orders_path}: cost {best_cost}")


if __name__ == "__main__":
    main(sys.argv)
