"""Authoring tool: ruin-and-recreate search with annealing for press schedules.

Usage: python3 lns.py WEEK.json OUT.json SECONDS SEED [START.json]
"""
import json, math, random, sys, time
from check_schedule import clear_of, evaluate, minutes


class W:
    def __init__(self, week):
        self.week = week
        self.presses = week["presses"]
        self.jobs = week["jobs"]
        self.jidx = {j["id"]: i for i, j in enumerate(self.jobs)}
        self.setup = week["setup_minutes"]
        self.cpm = week["setup_cost_per_minute"]
        self.run = [[minutes(j, p) for j in self.jobs] for p in self.presses]
        self.ok = [[j["tonnage"] <= p["tonnage"] for j in self.jobs] for p in self.presses]

    def press_cost(self, pi, seq):
        p = self.presses[pi]
        clock, fam, cost = 0, p["initial_family"], 0
        win = p["maintenance"]
        for ji in seq:
            j = self.jobs[ji]
            ch = self.setup[fam][j["family"]]
            cs = clear_of(clock, ch, win)
            r = self.run[pi][ji]
            st = clear_of(max(cs + ch, j["release"]), r, win)
            end = st + r
            cost += self.cpm * ch + j["weight"] * max(0, end - j["due"])
            clock, fam = end, j["family"]
        return cost


def insert_best(w, seqs, costs, ji, rng, blink):
    best = None
    for pi in range(len(w.presses)):
        if not w.ok[pi][ji]:
            continue
        s = seqs[pi]
        for pos in range(len(s) + 1):
            if rng.random() < blink:
                continue
            c = w.press_cost(pi, s[:pos] + [ji] + s[pos:]) - costs[pi]
            if best is None or c < best[0]:
                best = (c, pi, pos)
    _, pi, pos = best
    seqs[pi].insert(pos, ji)
    costs[pi] = w.press_cost(pi, seqs[pi])


def search(w, seconds, seed, start):
    rng = random.Random(seed)
    n = len(w.jobs)
    seqs = [[] for _ in w.presses]
    costs = [0] * len(w.presses)
    if start:
        pid = {p["id"]: i for i, p in enumerate(w.presses)}
        for p, lst in start["presses"].items():
            seqs[pid[p]] = [w.jidx[j] for j in lst]
        costs = [w.press_cost(i, s) for i, s in enumerate(seqs)]
    else:
        for ji in sorted(range(n), key=lambda i: w.jobs[i]["due"]):
            insert_best(w, seqs, costs, ji, rng, 0.0)
    cur = (sum(costs), [list(s) for s in seqs], list(costs))
    best = cur
    t0 = time.time()
    T0 = max(1.0, 0.01 * cur[0] / max(1, n))
    it = 0
    while time.time() - t0 < seconds:
        frac = (time.time() - t0) / seconds
        temp = T0 * (0.01 ** frac)
        seqs = [list(s) for s in cur[1]]
        costs = list(cur[2])
        k = rng.randint(2, max(3, min(15, n // 6)))
        mode = rng.random()
        pool = [(pi, ji) for pi, s in enumerate(seqs) for ji in s]
        if mode < 0.35:
            chosen = rng.sample(pool, min(k, len(pool)))
        elif mode < 0.6:
            fam = w.jobs[rng.choice(pool)[1]]["family"]
            cands = [x for x in pool if w.jobs[x[1]]["family"] == fam]
            chosen = rng.sample(cands, min(k, len(cands)))
        elif mode < 0.85:
            ref = w.jobs[rng.choice(pool)[1]]["due"]
            chosen = sorted(pool, key=lambda x: abs(w.jobs[x[1]]["due"] - ref))[:k]
        else:
            pi = rng.randrange(len(seqs))
            s = seqs[pi]
            if len(s) < 2:
                continue
            a = rng.randrange(len(s))
            b = min(len(s), a + rng.randint(2, 6))
            chosen = [(pi, ji) for ji in s[a:b]]
        removed = []
        for pi, ji in chosen:
            seqs[pi].remove(ji)
            removed.append(ji)
        for pi in set(pi for pi, _ in chosen):
            costs[pi] = w.press_cost(pi, seqs[pi])
        order = rng.random()
        if order < 0.4:
            rng.shuffle(removed)
        elif order < 0.7:
            removed.sort(key=lambda i: w.jobs[i]["due"])
        else:
            removed.sort(key=lambda i: -w.jobs[i]["weight"] * w.jobs[i]["strokes"])
        for ji in removed:
            insert_best(w, seqs, costs, ji, rng, 0.02)
        total = sum(costs)
        if total < cur[0] - temp * math.log(rng.random()):
            cur = (total, seqs, costs)
            if total < best[0]:
                best = (total, [list(s) for s in seqs], list(costs))
        it += 1
    return best, it


def to_schedule(w, best):
    return {"presses": {w.presses[i]["id"]: [w.jobs[j]["id"] for j in s] for i, s in enumerate(best[1])}}


if __name__ == "__main__":
    week = json.load(open(sys.argv[1]))
    w = W(week)
    start = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
    best, it = search(w, float(sys.argv[3]), int(sys.argv[4]), start)
    sched = to_schedule(w, best)
    assert evaluate(week, sched) == best[0]
    json.dump(sched, open(sys.argv[2], "w"))
    print(sys.argv[1], best[0], "iterations", it, flush=True)
