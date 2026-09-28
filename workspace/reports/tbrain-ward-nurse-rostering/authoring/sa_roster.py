"""Authoring tool: simulated annealing for ward rosters.

State may break hard rules at a large price per breach; the best roster with no
breach is kept. Moves: set one cell, swap one day between two nurses, swap a
block of days between two nurses, shift a block of one nurse's row by a day.

Usage: python3 sa_roster.py WARD.json OUT.json SECONDS SEED [START.json]
"""
import json
import math
import random
import sys
import time

TSCALE = 1.0  # set by cycle.py

from check_roster import evaluate

HARD = 5000


class P:
    def __init__(self, ward):
        self.w = ward
        self.days = ward["days"]
        self.nurses = ward["nurses"]
        self.n = len(self.nurses)
        self.hours = ward["shift_hours"]
        self.W = ward["weights"]
        self.R = ward["rules"]
        self.cover = ward["cover"]
        self.grade = [x["grade"] for x in self.nurses]
        self.leave = [set(x["leave"]) for x in self.nurses]
        self.req = [[] for _ in self.nurses]
        for i, x in enumerate(self.nurses):
            for r in x["requests"]:
                self.req[i].append((r["day"], r["off"]))

    def row_cost(self, i, row):
        x, W, R, days = self.nurses[i], self.W, self.R, self.days
        hard = 0
        soft = 0
        for d in self.leave[i]:
            if row[d] != ".":
                hard += 1
        run = 0
        for d in range(days):
            c = row[d]
            if d + 1 < days:
                pair = c + row[d + 1]
                if pair in ("NE", "NL", "LE"):
                    hard += 1
                if c == "N" and row[d + 1] != "N":
                    for k in range(d + 1, min(days, d + 1 + R["rest_days_after_nights"])):
                        if row[k] != ".":
                            hard += 1
            run = run + 1 if c != "." else 0
            if run > R["max_consecutive_days"]:
                hard += 1
        worked = sum(self.hours[c] for c in row if c != ".")
        if worked < x["min_hours"]:
            soft += W["hour_under"] * (x["min_hours"] - worked)
        if worked > x["max_hours"]:
            soft += W["hour_over"] * (worked - x["max_hours"])
        nights = row.count("N")
        if nights > x["max_nights"]:
            soft += W["night_over"] * (nights - x["max_nights"])
        weekends = 0
        for sat in range(5, days, 7):
            a = row[sat] != "."
            b = sat + 1 < days and row[sat + 1] != "."
            if a or b:
                weekends += 1
            if sat + 1 < days and a != b:
                soft += W["split_weekend"]
        if weekends > R["max_weekends"]:
            soft += W["weekend_over"] * (weekends - R["max_weekends"])
        for d in range(1, days - 1):
            if row[d] != "." and row[d - 1] == "." and row[d + 1] == ".":
                soft += W["lone_day"]
        for d, want in self.req[i]:
            if (want == "day" and row[d] != ".") or (want != "day" and row[d] == want):
                soft += W["request"]
        return hard, soft

    def day_cost(self, rows, d):
        hard = soft = 0
        for s in "ELN":
            on = rn = sen = 0
            for i in range(self.n):
                if rows[i][d] == s:
                    on += 1
                    g = self.grade[i]
                    if g != "HCA":
                        rn += 1
                    if g == "senior":
                        sen += 1
            need = self.cover[s]
            hard += max(0, need["minimum"] - on) + max(0, need["registered"] - rn) + (sen < 1)
            soft += self.W["short_of_preferred"] * max(0, need["preferred"] - on)
        return hard, soft


def search(p, seconds, seed, start):
    rng = random.Random(seed)
    ids = [x["id"] for x in p.nurses]
    rows = [list(start["roster"][nid]) for nid in ids]
    rc = [p.row_cost(i, rows[i]) for i in range(p.n)]
    dc = [p.day_cost(rows, d) for d in range(p.days)]

    def score(h, s):
        return HARD * h + s

    cur_h = sum(h for h, _ in rc) + sum(h for h, _ in dc)
    cur_s = sum(s for _, s in rc) + sum(s for _, s in dc)
    cur = score(cur_h, cur_s)
    best = cur_s if cur_h == 0 else None
    best_rows = [list(r) for r in rows] if cur_h == 0 else None
    t0 = time.time()
    T0, T1 = 60.0 * TSCALE, 0.5
    it = 0
    codes = "ELN."
    while True:
        el = time.time() - t0
        if el > seconds:
            break
        temp = T0 * (T1 / T0) ** (el / seconds)
        r = rng.random()
        if r < 0.3:
            i = rng.randrange(p.n)
            d = rng.randrange(p.days)
            c = rng.choice(codes)
            if c == rows[i][d]:
                continue
            changes = [(i, d, c)]
        elif r < 0.65:
            d = rng.randrange(p.days)
            i, j = rng.sample(range(p.n), 2)
            if rows[i][d] == rows[j][d]:
                continue
            changes = [(i, d, rows[j][d]), (j, d, rows[i][d])]
        elif r < 0.9:
            i, j = rng.sample(range(p.n), 2)
            a = rng.randrange(p.days)
            b = min(p.days, a + rng.randint(2, 7))
            changes = []
            for d in range(a, b):
                if rows[i][d] != rows[j][d]:
                    changes.append((i, d, rows[j][d]))
                    changes.append((j, d, rows[i][d]))
            if not changes:
                continue
        else:
            i = rng.randrange(p.n)
            a = rng.randrange(p.days - 1)
            b = min(p.days, a + rng.randint(2, 6))
            seg = rows[i][a:b]
            if rng.random() < 0.5:
                new = seg[1:] + seg[:1]
            else:
                new = seg[-1:] + seg[:-1]
            changes = [(i, a + k, new[k]) for k in range(len(seg)) if new[k] != seg[k]]
            if not changes:
                continue
        old = [(i, d, rows[i][d]) for i, d, _ in changes]
        nurses_hit = {i for i, _, _ in changes}
        days_hit = {d for _, d, _ in changes}
        before_h = sum(rc[i][0] for i in nurses_hit) + sum(dc[d][0] for d in days_hit)
        before_s = sum(rc[i][1] for i in nurses_hit) + sum(dc[d][1] for d in days_hit)
        for i, d, c in changes:
            rows[i][d] = c
        nrc = {i: p.row_cost(i, rows[i]) for i in nurses_hit}
        ndc = {d: p.day_cost(rows, d) for d in days_hit}
        after_h = sum(v[0] for v in nrc.values()) + sum(v[0] for v in ndc.values())
        after_s = sum(v[1] for v in nrc.values()) + sum(v[1] for v in ndc.values())
        delta = score(after_h, after_s) - score(before_h, before_s)
        if delta <= 0 or rng.random() < math.exp(-delta / temp):
            for i, v in nrc.items():
                rc[i] = v
            for d, v in ndc.items():
                dc[d] = v
            cur_h += after_h - before_h
            cur_s += after_s - before_s
            if cur_h == 0 and (best is None or cur_s < best):
                best = cur_s
                best_rows = [list(r) for r in rows]
        else:
            for i, d, c in old:
                rows[i][d] = c
        it += 1
    return best, best_rows, it


if __name__ == "__main__":
    ward = json.load(open(sys.argv[1]))
    p = P(ward)
    if len(sys.argv) > 5:
        start = json.load(open(sys.argv[5]))
    else:
        from plan_ward import plan
        start = plan(ward)
    best, rows, it = search(p, float(sys.argv[3]), int(sys.argv[4]), start)
    out = {"roster": {x["id"]: "".join(r) for x, r in zip(p.nurses, rows)}}
    assert evaluate(ward, out) == best, (evaluate(ward, out), best)
    json.dump(out, open(sys.argv[2], "w"))
    print(sys.argv[1], best, "iterations", it, flush=True)
