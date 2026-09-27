"""The search that produced the reference layouts: large-neighbourhood search.

Ruin: clear one to four pages (random pages, one spread, or pages of one section).
Recreate: take the cleared ads plus a random sample of left-out ads, order them
by a randomized rule, and put each at its cheapest spot on the cleared pages
(lowest flat skyline segment; skyline packing is exact for ads that must rest on
the foot or on ads across their full width). Accept by simulated annealing.

The reference layouts came from runs of this script started from the shipped
planner's layout and later from the cheapest layout so far, several seeds per
edition, including repeated shorter runs at varied starting temperatures (TSCALE)
and single runs of two and four hours, until restarts stopped improving. solve.sh
only copies their saved output.

Usage: python3 search.py EDITION.json OUT.json SECONDS SEED [START.json]
Reads the rules checker from $APP/tools and the planner from $APP/planner
(APP defaults to /app).
"""

import json
import math
import os
import random
import sys
import time

TSCALE = 1.0  # set by cycle.py

APP = os.environ.get("APP", "/app")
sys.path.insert(0, os.path.join(APP, "tools"))
sys.path.insert(0, os.path.join(APP, "planner"))
from check_layout import evaluate  # noqa: E402


class E:
    def __init__(self, ed):
        self.ed = ed
        self.cols, self.rows, self.pages = ed["columns"], ed["rows"], ed["pages"]
        self.ads = ed["ads"]
        self.aidx = {a["id"]: i for i, a in enumerate(self.ads)}
        self.limit = {
            p: (
                ed["front_page_ad_rows"] * self.cols
                if p == 1
                else ed["max_ad_share_percent"] * self.rows * self.cols // 100
            )
            for p in range(1, self.pages + 1)
        }
        self.sec_of_page = {}
        for s, (a, b) in ed["sections"].items():
            for p in range(a, b + 1):
                self.sec_of_page[p] = s
        self.place_cost = []
        for a in self.ads:
            row = {}
            for p in range(1, self.pages + 1):
                c = 0
                if a["section"] is not None and self.sec_of_page[p] != a["section"]:
                    c += a["rate"] * ed["wrong_section_percent"] // 100
                if a["right_hand"] and p % 2 == 0:
                    c += a["rate"] * ed["left_hand_percent"] // 100
                row[p] = c
            self.place_cost.append(row)

    @staticmethod
    def spread(p):
        return 0 if p == 1 else p // 2


def pack_try(e, page_state, p, i, rng):
    """Find a spot for ad i on page p: returns (height, col) or None."""
    a = e.ads[i]
    w, d = a["width"], a["depth"]
    hs = page_state["h"]
    if page_state["used"] + w * d > e.limit[p]:
        return None
    best = None
    for c in range(e.cols - w + 1):
        seg = hs[c : c + w]
        h = seg[0]
        if any(x != h for x in seg):
            continue
        top = e.rows - h - d
        if top < 0 or (p == 1 and top < e.rows - e.ed["front_page_ad_rows"]):
            continue
        # prefer low spots and snug fits
        waste = 0
        if c > 0 and hs[c - 1] > h:
            waste -= 1
        if c + w < e.cols and hs[c + w] > h:
            waste -= 1
        key = (h, waste, rng.random())
        if best is None or key < best[0]:
            best = (key, h, c)
    return None if best is None else (best[1], best[2])


def empty_page(e):
    return {"h": [0] * e.cols, "used": 0, "ads": []}


def put(e, st, p, i, h, c, groups):
    a = e.ads[i]
    for x in range(c, c + a["width"]):
        st["h"][x] = h + a["depth"]
    st["used"] += a["width"] * a["depth"]
    st["ads"].append((i, c, e.rows - h - a["depth"]))
    g = a["competitor_group"]
    if g is not None:
        groups[(g, e.spread(p))] = i


def total_cost(e, where):
    c = 0
    for i, a in enumerate(e.ads):
        p = where[i]
        c += a["rate"] if p is None else e.place_cost[i][p]
    return c


def search(e, seconds, seed, start):
    rng = random.Random(seed)
    n = len(e.ads)
    pages = {p: empty_page(e) for p in range(1, e.pages + 1)}
    where = [None] * n
    groups = {}
    # rebuild from start layout, in order from the foot up per page
    items = []
    for aid, pos in start["placements"].items():
        i = e.aidx[aid]
        items.append((pos["page"], -(pos["row"] + e.ads[i]["depth"]), pos["column"], i))
    for p, negfoot, c, i in sorted(items):
        a = e.ads[i]
        h = e.rows - (-negfoot)
        put(e, pages[p], p, i, h, c, groups)
        where[i] = p
    cur = total_cost(e, where)
    best, best_pages = cur, {p: list(st["ads"]) for p, st in pages.items()}
    t0 = time.time()
    T0 = 0.02 * cur / max(1, e.pages) * TSCALE
    it = 0
    secs = list(e.ed["sections"])
    while True:
        el = time.time() - t0
        if el > seconds:
            break
        temp = max(0.5, T0 * (0.01 ** (el / seconds)))
        r = rng.random()
        if r < 0.45:
            sel = rng.sample(range(1, e.pages + 1), rng.randint(1, 3))
        elif r < 0.75:
            s = rng.randint(0, e.pages // 2)
            sel = [p for p in (2 * s, 2 * s + 1) if 1 <= p <= e.pages] if s else [1]
            if rng.random() < 0.5:
                sel.append(rng.randint(1, e.pages))
        else:
            a, b = e.ed["sections"][rng.choice(secs)]
            span = list(range(a, b + 1))
            sel = rng.sample(span, min(len(span), rng.randint(2, 4)))
        sel = sorted(set(sel))
        removed = [i for p in sel for (i, _, _) in pages[p]["ads"]]
        out = [i for i in range(n) if where[i] is None]
        pool = removed + rng.sample(out, min(len(out), rng.randint(3, 15)))
        old_pages = {p: pages[p] for p in sel}
        old_where = {i: where[i] for i in pool}
        old_groups = dict(groups)
        for p in sel:
            for i, _, _ in pages[p]["ads"]:
                g = e.ads[i]["competitor_group"]
                if g is not None:
                    groups.pop((g, e.spread(p)), None)
                where[i] = None
            pages[p] = empty_page(e)
        rule = rng.random()
        if rule < 0.35:
            pool.sort(
                key=lambda i: (
                    not e.ads[i]["booked"],
                    -e.ads[i]["width"] * e.ads[i]["depth"],
                    rng.random(),
                )
            )
        elif rule < 0.6:
            pool.sort(
                key=lambda i: (
                    not e.ads[i]["booked"],
                    -e.ads[i]["rate"]
                    / (e.ads[i]["width"] * e.ads[i]["depth"])
                    * rng.uniform(0.8, 1.2),
                )
            )
        elif rule < 0.8:
            pool.sort(
                key=lambda i: (
                    not e.ads[i]["booked"],
                    -e.ads[i]["depth"],
                    -e.ads[i]["width"],
                    rng.random(),
                )
            )
        else:
            rng.shuffle(pool)
            pool.sort(key=lambda i: not e.ads[i]["booked"])
        feasible = True
        for i in pool:
            a = e.ads[i]
            bestspot = None
            for p in sel:
                g = a["competitor_group"]
                if g is not None and groups.get((g, e.spread(p)), i) != i:
                    continue
                spot = pack_try(e, pages[p], p, i, rng)
                if spot is None:
                    continue
                key = (e.place_cost[i][p], spot[0], rng.random())
                if bestspot is None or key < bestspot[0]:
                    bestspot = (key, p, spot)
            if bestspot is None:
                if a["booked"]:
                    feasible = False
                    break
                continue
            _, p, (h, c) = bestspot
            put(e, pages[p], p, i, h, c, groups)
            where[i] = p
        new = total_cost(e, where) if feasible else None
        if feasible and (new <= cur or rng.random() < math.exp(-(new - cur) / temp)):
            cur = new
            if cur < best:
                best, best_pages = cur, {p: list(st["ads"]) for p, st in pages.items()}
        else:
            for p in sel:
                pages[p] = old_pages[p]
            for i, v in old_where.items():
                where[i] = v
            groups.clear()
            groups.update(old_groups)
        it += 1
    return best, best_pages, it


def to_layout(e, best_pages):
    out = {}
    for p, lst in best_pages.items():
        for i, c, r in lst:
            out[e.ads[i]["id"]] = {"page": p, "column": c, "row": r}
    return {"placements": dict(sorted(out.items()))}


if __name__ == "__main__":
    ed = json.load(open(sys.argv[1]))
    e = E(ed)
    if len(sys.argv) > 5:
        start = json.load(open(sys.argv[5]))
    else:
        from plan_edition import plan

        start = plan(ed)
    best, pages, it = search(e, float(sys.argv[3]), int(sys.argv[4]), start)
    lay = to_layout(e, pages)
    assert evaluate(ed, lay) == best, (evaluate(ed, lay), best)
    json.dump(lay, open(sys.argv[2], "w"))
    print(sys.argv[1], best, "iterations", it, flush=True)
