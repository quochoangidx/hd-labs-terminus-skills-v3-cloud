"""Authoring tool: simulated annealing for stand plans.

Moves: relocate a turn to another stand; swap the stands of two turns; eject:
put a turn on a stand and re-place the turns it collides with (on its old stand
or their cheapest free stand); window swap: exchange everything two stands hold
inside a time window. Incremental cost evaluation.

Usage: python3 search.py DAY.json OUT.json SECONDS SEED [START.json]
"""
import json
import math
import random
import sys
import time

TSCALE = 1.0  # set by cycle.py

from check_plan import evaluate


class S:
    def __init__(self, day):
        self.day = day
        self.stands = day["stands"]
        self.turns = day["turns"]
        self.ns, self.nt = len(self.stands), len(self.turns)
        self.tidx = {t["id"]: i for i, t in enumerate(self.turns)}
        self.sidx = {s["id"]: i for i, s in enumerate(self.stands)}
        self.A = [t["arrive"] for t in self.turns]
        self.D = [t["depart"] for t in self.turns]
        self.big = [t["size"] == 3 for t in self.turns]
        self.buf = day["buffer_minutes"]
        self.W = day["walk_metres"]
        self.ok = [[t["size"] <= s["size"] and (s["international"] or not t["international"]) for s in self.stands]
                   for t in self.turns]
        self.okl = [[j for j in range(self.ns) if self.ok[i][j]] for i in range(self.nt)]
        self.bus = [[day["bus_cost_per_passenger"] * (t["pax_in"] + t["pax_out"]) if s["remote"] else 0
                     for s in self.stands] for t in self.turns]
        self.adj = [[] for _ in range(self.nt)]
        for tr in day["transfers"]:
            a, b = self.tidx[tr["from"]], self.tidx[tr["to"]]
            self.adj[a].append((b, tr["passengers"]))
            self.adj[b].append((a, tr["passengers"]))
        self.wing = [[] for _ in range(self.ns)]
        for a, b in day["wingtip_pairs"]:
            self.wing[self.sidx[a]].append(self.sidx[b])
            self.wing[self.sidx[b]].append(self.sidx[a])

    def clash(self, i, j, members, ignore=()):
        """Turns on stand j (or wingtip neighbours) that block turn i."""
        out = []
        a, d, b = self.A[i], self.D[i], self.buf
        for k in members[j]:
            if k != i and k not in ignore and not (self.D[k] + b <= a or d + b <= self.A[k]):
                out.append(k)
        if self.big[i]:
            for n in self.wing[j]:
                for k in members[n]:
                    if k != i and k not in ignore and self.big[k] and self.A[k] < d and a < self.D[k]:
                        out.append(k)
        return out

    def tcost(self, i, j, at):
        c = self.bus[i][j]
        Wj = self.W[j]
        for k, p in self.adj[i]:
            c += p * Wj[at[k]]
        return c

    def total(self, at):
        c = sum(self.bus[i][at[i]] for i in range(self.nt))
        for tr in self.day["transfers"]:
            c += tr["passengers"] * self.W[at[self.tidx[tr["from"]]]][at[self.tidx[tr["to"]]]]
        return c


def search(p, seconds, seed, start):
    rng = random.Random(seed)
    at = [p.sidx[sid] for sid in [None] * 0] or [None] * p.nt
    for sid, lst in start["stands"].items():
        for tid in lst:
            at[p.tidx[tid]] = p.sidx[sid]
    members = [set() for _ in range(p.ns)]
    for i, j in enumerate(at):
        members[j].add(i)
    cur = p.total(at)
    best, best_at = cur, list(at)
    t0 = time.time()
    T0 = 2000.0 * TSCALE
    it = 0
    while True:
        el = time.time() - t0
        if el > seconds:
            break
        temp = T0 * (0.002 ** (el / seconds))
        r = rng.random()
        i = rng.randrange(p.nt)
        oi = at[i]
        if r < 0.4:
            j = rng.choice(p.okl[i])
            if j == oi or p.clash(i, j, members):
                continue
            delta = p.tcost(i, j, at) - p.tcost(i, oi, at)
            if delta <= 0 or rng.random() < math.exp(-delta / temp):
                members[oi].discard(i); members[j].add(i); at[i] = j; cur += delta
        elif r < 0.7:
            j = rng.choice(p.okl[i])
            if j == oi or not members[j]:
                continue
            cands = [k for k in members[j] if p.ok[k][oi] and p.A[k] < p.D[i] + 240 and p.A[i] < p.D[k] + 240]
            if not cands:
                continue
            k = rng.choice(cands)
            members[oi].discard(i); members[j].discard(k)
            if p.clash(i, j, members) or p.clash(k, oi, members):
                members[oi].add(i); members[j].add(k)
                continue
            before = p.tcost(i, oi, at) + p.tcost(k, j, at)
            at[i], at[k] = j, oi
            after = p.tcost(i, j, at) + p.tcost(k, oi, at)
            # a transfer between i and k was counted twice on both sides alike
            delta = after - before
            if delta <= 0 or rng.random() < math.exp(-delta / temp):
                members[j].add(i); members[oi].add(k); cur += delta
            else:
                at[i], at[k] = oi, j
                members[oi].add(i); members[j].add(k)
        elif r < 0.9:
            # eject
            j = rng.choice(p.okl[i])
            if j == oi:
                continue
            members[oi].discard(i)
            hit = p.clash(i, j, members)
            if not hit or len(hit) > 3:
                members[oi].add(i)
                continue
            old = {k: at[k] for k in hit}
            before = p.tcost(i, oi, at) + sum(p.tcost(k, at[k], at) for k in hit)
            for k in hit:
                members[at[k]].discard(k)
            members[j].add(i); at[i] = j
            okk = True
            rng.shuffle(hit)
            for k in hit:
                opts = [s for s in p.okl[k] if not p.clash(k, s, members)]
                if not opts:
                    okk = False
                    break
                s = min(opts, key=lambda s: p.tcost(k, s, at) + rng.random())
                members[s].add(k); at[k] = s
            if okk:
                after = p.tcost(i, j, at) + sum(p.tcost(k, at[k], at) for k in hit)
                # pairwise transfers among moved turns are counted from both ends; recompute exactly
                delta = p.total(at) - cur if len(hit) > 0 and any(
                    k2 in dict(p.adj[k1]) for k1 in [i] + hit for k2 in [i] + hit if k1 != k2) else after - before
                if delta <= 0 or rng.random() < math.exp(-delta / temp):
                    cur += delta
                    okk = "accepted"
            if okk != "accepted":
                for k in hit:
                    if at[k] is not None:
                        members[at[k]].discard(k)
                members[j].discard(i)
                at[i] = oi; members[oi].add(i)
                for k, s in old.items():
                    at[k] = s; members[s].add(k)
        else:
            # window swap between two compatible stands
            j = rng.choice(p.okl[i])
            if j == oi:
                continue
            lo = p.A[i] - rng.randint(0, 120)
            hi = p.D[i] + rng.randint(0, 180)
            X = [k for k in members[oi] if lo <= p.A[k] and p.D[k] <= hi]
            Y = [k for k in members[j] if lo <= p.A[k] and p.D[k] <= hi]
            if any(not p.ok[k][j] for k in X) or any(not p.ok[k][oi] for k in Y):
                continue
            moved = X + Y
            before = sum(p.tcost(k, at[k], at) for k in moved)
            for k in X:
                members[oi].discard(k)
            for k in Y:
                members[j].discard(k)
            for k in X:
                at[k] = j
            for k in Y:
                at[k] = oi
            bad = any(p.clash(k, j, members) for k in X) or any(p.clash(k, oi, members) for k in Y)
            if not bad:
                for k in X:
                    members[j].add(k)
                for k in Y:
                    members[oi].add(k)
                bad = any(p.clash(k, j, members) for k in X) or any(p.clash(k, oi, members) for k in Y)
                if bad:
                    for k in X:
                        members[j].discard(k)
                    for k in Y:
                        members[oi].discard(k)
            if bad:
                for k in X:
                    at[k] = oi; members[oi].add(k)
                for k in Y:
                    at[k] = j; members[j].add(k)
                continue
            delta = p.total(at) - cur
            if delta <= 0 or rng.random() < math.exp(-delta / temp):
                cur += delta
            else:
                for k in X:
                    members[j].discard(k); at[k] = oi; members[oi].add(k)
                for k in Y:
                    members[oi].discard(k); at[k] = j; members[j].add(k)
        it += 1
        if cur < best:
            best, best_at = cur, list(at)
    assert p.total(best_at) == best, (p.total(best_at), best)
    return best, best_at, it


def to_plan(p, at):
    out = {s["id"]: [] for s in p.stands}
    for i in sorted(range(p.nt), key=lambda i: p.A[i]):
        out[p.stands[at[i]]["id"]].append(p.turns[i]["id"])
    return {"stands": out}


if __name__ == "__main__":
    day = json.load(open(sys.argv[1]))
    p = S(day)
    if len(sys.argv) > 5:
        start = json.load(open(sys.argv[5]))
    else:
        from plan_day import plan
        start = plan(day)
    best, at, it = search(p, float(sys.argv[3]), int(sys.argv[4]), start)
    plan_out = to_plan(p, at)
    assert evaluate(day, plan_out) == best
    json.dump(plan_out, open(sys.argv[2], "w"))
    print(sys.argv[1], best, "iterations", it, flush=True)
