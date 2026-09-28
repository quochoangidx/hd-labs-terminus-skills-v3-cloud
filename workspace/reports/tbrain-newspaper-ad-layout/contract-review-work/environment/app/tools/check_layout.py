"""Check an ad layout against the make-up rules and print its cost.

Usage: python3 check_layout.py EDITION.json LAYOUT.json
"""

import json
import sys


class LayoutError(Exception):
    pass


def evaluate(ed, layout):
    """Return the integer cost of the layout, or raise LayoutError."""
    if not isinstance(layout, dict) or not isinstance(layout.get("placements"), dict):
        raise LayoutError('the layout must be an object with a "placements" object')
    cols, rows, pages = ed["columns"], ed["rows"], ed["pages"]
    ads = {a["id"]: a for a in ed["ads"]}
    grid = {p: [[None] * cols for _ in range(rows)] for p in range(1, pages + 1)}
    placed = {}
    for aid, pos in layout["placements"].items():
        if aid not in ads:
            raise LayoutError(f"unknown ad {aid!r}")
        if not isinstance(pos, dict) or any(type(pos.get(k)) is not int for k in ("page", "column", "row")):
            raise LayoutError(f"ad {aid}: a placement needs whole-number page, column and row")
        a = ads[aid]
        p, c, r = pos["page"], pos["column"], pos["row"]
        if not 1 <= p <= pages:
            raise LayoutError(f"ad {aid}: no page {p}")
        if c < 0 or r < 0 or c + a["width"] > cols or r + a["depth"] > rows:
            raise LayoutError(f"ad {aid} runs off page {p}")
        for y in range(r, r + a["depth"]):
            for x in range(c, c + a["width"]):
                if grid[p][y][x] is not None:
                    raise LayoutError(f"ads {grid[p][y][x]} and {aid} overlap on page {p}")
                grid[p][y][x] = aid
        placed[aid] = (p, c, r)

    for aid, (p, c, r) in placed.items():
        a = ads[aid]
        below = r + a["depth"]
        if below < rows:
            for x in range(c, c + a["width"]):
                if grid[p][below][x] is None:
                    raise LayoutError(f"ad {aid} on page {p} is not resting on the foot of the page or on ads across its full width")

    for p in range(1, pages + 1):
        used = sum(1 for y in range(rows) for x in range(cols) if grid[p][y][x] is not None)
        limit = ed["front_page_ad_rows"] * cols if p == 1 else ed["max_ad_share_percent"] * rows * cols // 100
        if used > limit:
            raise LayoutError(f"page {p} carries {used} ad cells, more than its limit of {limit}")
    for aid, (p, c, r) in placed.items():
        if p == 1 and r < rows - ed["front_page_ad_rows"]:
            raise LayoutError(f"ad {aid} reaches above the front-page strip")

    def spread(p):
        return 0 if p == 1 else p // 2

    by_group = {}
    for aid, (p, _, _) in placed.items():
        g = ads[aid]["competitor_group"]
        if g is not None:
            by_group.setdefault(g, []).append((spread(p), aid))
    for g, lst in by_group.items():
        seen = {}
        for s, aid in lst:
            if s in seen:
                raise LayoutError(f"competing ads {seen[s]} and {aid} face each other")
            seen[s] = aid

    for a in ed["ads"]:
        if a["booked"] and a["id"] not in placed:
            raise LayoutError(f"booked ad {a['id']} is not placed")

    sections = ed["sections"]
    cost = 0
    for a in ed["ads"]:
        if a["id"] not in placed:
            cost += a["rate"]
            continue
        p = placed[a["id"]][0]
        want = a["section"]
        if want is not None:
            first, last = sections[want]
            if not first <= p <= last:
                cost += a["rate"] * ed["wrong_section_percent"] // 100
        if a["right_hand"] and p % 2 == 0:
            cost += a["rate"] * ed["left_hand_percent"] // 100
    return cost


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        ed = json.load(fh)
    with open(argv[2]) as fh:
        layout = json.load(fh)
    try:
        cost = evaluate(ed, layout)
    except LayoutError as exc:
        print(f"invalid: {exc}")
        return 1
    print(f"valid, cost {cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
