"""Authoring tool: iterated local search for press schedules.

Local search to a local optimum under three exhaustive neighbourhoods (relocate one
job to any press/position, swap two jobs, move a block of 2-8 consecutive jobs to
any press/position), then perturb by ruin-and-recreate of a few jobs and accept by
record-to-record travel against the best.

Usage: python3 ils.py WEEK.json OUT.json SECONDS SEED START.json
"""
import json, random, sys, time
from check_schedule import evaluate
from lns import W, insert_best, to_schedule


def local_search(w, seqs, costs, deadline):
    P = len(seqs)
    improved = True
    while improved and time.time() < deadline:
        improved = False
        # relocate and block moves
        for L in (1, 2, 3, 4, 6, 8):
            for a in range(P):
                i = 0
                while i + L <= len(seqs[a]):
                    blk = seqs[a][i:i + L]
                    rest = seqs[a][:i] + seqs[a][i + L:]
                    ca = w.press_cost(a, rest)
                    base = costs[a]
                    done = False
                    for b in range(P):
                        if not all(w.ok[b][j] for j in blk):
                            continue
                        tgt = rest if b == a else seqs[b]
                        for pos in range(len(tgt) + 1):
                            if b == a and pos == i:
                                continue
                            new = tgt[:pos] + blk + tgt[pos:]
                            cb = w.press_cost(b, new)
                            if b == a:
                                if cb < base:
                                    seqs[a], costs[a] = new, cb
                                    done = True
                                    break
                            elif ca + cb < base + costs[b]:
                                seqs[a], costs[a] = rest, ca
                                seqs[b], costs[b] = new, cb
                                done = True
                                break
                        if done:
                            break
                    if done:
                        improved = True
                    else:
                        i += 1
        # swaps
        for a in range(P):
            for i in range(len(seqs[a])):
                for b in range(a, P):
                    for k in range(len(seqs[b])):
                        if b == a and k <= i:
                            continue
                        if i >= len(seqs[a]) or k >= len(seqs[b]):
                            continue
                        x, y = seqs[a][i], seqs[b][k]
                        if not (w.ok[a][y] and w.ok[b][x]):
                            continue
                        if a == b:
                            s = list(seqs[a]); s[i], s[k] = y, x
                            c = w.press_cost(a, s)
                            if c < costs[a]:
                                seqs[a], costs[a] = s, c
                                improved = True
                        else:
                            s1 = list(seqs[a]); s1[i] = y
                            s2 = list(seqs[b]); s2[k] = x
                            c1, c2 = w.press_cost(a, s1), w.press_cost(b, s2)
                            if c1 + c2 < costs[a] + costs[b]:
                                seqs[a], costs[a], seqs[b], costs[b] = s1, c1, s2, c2
                                improved = True
    return seqs, costs


def main():
    week = json.load(open(sys.argv[1]))
    w = W(week)
    seconds, rng = float(sys.argv[3]), random.Random(int(sys.argv[4]))
    start = json.load(open(sys.argv[5]))
    pid = {p["id"]: i for i, p in enumerate(w.presses)}
    seqs = [[] for _ in w.presses]
    for p, lst in start["presses"].items():
        seqs[pid[p]] = [w.jidx[j] for j in lst]
    costs = [w.press_cost(i, s) for i, s in enumerate(seqs)]
    deadline = time.time() + seconds
    seqs, costs = local_search(w, seqs, costs, deadline)
    best = (sum(costs), [list(s) for s in seqs], list(costs))
    cur = best
    it = 0
    while time.time() < deadline:
        seqs, costs = [list(s) for s in cur[1]], list(cur[2])
        pool = [(pi, ji) for pi, s in enumerate(seqs) for ji in s]
        mode = rng.random()
        k = rng.randint(3, 10)
        if mode < 0.5:
            chosen = rng.sample(pool, k)
        else:
            ref = w.jobs[rng.choice(pool)[1]]["due"]
            chosen = sorted(pool, key=lambda x: abs(w.jobs[x[1]]["due"] - ref))[:k]
        for pi, ji in chosen:
            seqs[pi].remove(ji)
        for pi in set(pi for pi, _ in chosen):
            costs[pi] = w.press_cost(pi, seqs[pi])
        removed = [ji for _, ji in chosen]
        rng.shuffle(removed)
        for ji in removed:
            insert_best(w, seqs, costs, ji, rng, 0.05)
        seqs, costs = local_search(w, seqs, costs, deadline)
        total = sum(costs)
        if total <= best[0] * 1.004:
            cur = (total, seqs, costs)
            if total < best[0]:
                best = (total, [list(s) for s in seqs], list(costs))
                print("best", total, round(time.time() - deadline + seconds), flush=True)
        it += 1
    sched = to_schedule(w, best)
    assert evaluate(week, sched) == best[0]
    json.dump(sched, open(sys.argv[2], "w"))
    print(sys.argv[1], best[0], "iterations", it, flush=True)


if __name__ == "__main__":
    main()
