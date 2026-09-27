"""Ad make-up planner used by the advertising desk.

Booked ads first, then the rest by rate, highest first. Each ad goes on the
first page that can take it, trying its own section's pages before the others,
at the lowest spot where it rests flat on the foot of the page or on ads below
it, leftmost first. An ad that fits nowhere is left out.

Usage: python3 plan_edition.py EDITION.json LAYOUT.json
"""

import json
import sys


def plan(ed):
    cols, rows, pages = ed["columns"], ed["rows"], ed["pages"]
    height = {p: [0] * cols for p in range(1, pages + 1)}  # filled cells from the foot, per column
    used = {p: 0 for p in range(1, pages + 1)}
    spreads = {}
    placements = {}

    def spread(p):
        return 0 if p == 1 else p // 2

    order = sorted(ed["ads"], key=lambda a: (not a["booked"], -a["rate"], a["id"]))
    for a in order:
        w, d = a["width"], a["depth"]
        pages_order = list(range(1, pages + 1))
        if a["section"] is not None:
            first, last = ed["sections"][a["section"]]
            pages_order = [p for p in pages_order if first <= p <= last] + \
                          [p for p in pages_order if not first <= p <= last]
        done = False
        for p in pages_order:
            limit = ed["front_page_ad_rows"] * cols if p == 1 else ed["max_ad_share_percent"] * rows * cols // 100
            if used[p] + w * d > limit:
                continue
            g = a["competitor_group"]
            if g is not None and (g, spread(p)) in spreads:
                continue
            best = None
            for c in range(cols - w + 1):
                hs = height[p][c:c + w]
                if len(set(hs)) != 1:
                    continue
                h = hs[0]
                top = rows - h - d
                if top < 0 or (p == 1 and top < rows - ed["front_page_ad_rows"]):
                    continue
                if best is None or h < best[0]:
                    best = (h, c)
            if best is None:
                continue
            h, c = best
            for x in range(c, c + w):
                height[p][x] = h + d
            used[p] += w * d
            if g is not None:
                spreads[(g, spread(p))] = a["id"]
            placements[a["id"]] = {"page": p, "column": c, "row": rows - h - d}
            done = True
            break
        if not done and a["booked"]:
            raise SystemExit(f"cannot place booked ad {a['id']}")
    return {"placements": placements}


def main(argv):
    with open(argv[1]) as fh:
        ed = json.load(fh)
    with open(argv[2], "w") as fh:
        json.dump(plan(ed), fh, indent=1)


if __name__ == "__main__":
    main(sys.argv)
