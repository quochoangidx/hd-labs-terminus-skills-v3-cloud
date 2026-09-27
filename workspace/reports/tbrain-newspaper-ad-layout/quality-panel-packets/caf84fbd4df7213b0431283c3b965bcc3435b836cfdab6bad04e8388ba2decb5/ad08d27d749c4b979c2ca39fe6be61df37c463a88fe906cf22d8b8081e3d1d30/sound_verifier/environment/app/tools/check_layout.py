"""Check an ad layout against the make-up rules and print its cost.

Usage: python3 check_layout.py EDITION.json LAYOUT.json
"""

import json
import os
import sys

sys.set_int_max_str_digits(4300)


class LayoutError(Exception):
    pass


MAX_BYTES = 2_000_000
MAX_DEPTH = 64
MAX_DIGITS = 4300


def _no_constant(name):
    raise LayoutError(f"{name} is not JSON")


def _digits(text):
    if sum(c.isdigit() for c in text) > MAX_DIGITS:
        raise LayoutError(f"a number is written with more than {MAX_DIGITS} digits")
    return text


def _int(text):
    return int(_digits(text))


def _float(text):
    return float(_digits(text))


def _no_repeats(pairs):
    names = set()
    for name, _ in pairs:
        if name in names:
            raise LayoutError(f"the name {name!r} appears twice in one object")
        names.add(name)
    return dict(pairs)


def _check_depth(value):
    stack = [(value, 1)]
    while stack:
        v, depth = stack.pop()
        if isinstance(v, (dict, list)):
            if depth > MAX_DEPTH:
                raise LayoutError(f"the file nests values more than {MAX_DEPTH} levels deep")
            stack.extend((x, depth + 1) for x in (v.values() if isinstance(v, dict) else v))


def load_layout(path):
    """Read a layout file: standard JSON of at most MAX_BYTES bytes."""
    if os.path.getsize(path) > MAX_BYTES:
        raise LayoutError(f"the file is larger than {MAX_BYTES} bytes")
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_no_repeats,
                           parse_int=_int, parse_float=_float)
    except (UnicodeDecodeError, ValueError) as exc:
        raise LayoutError(f"the file is not valid JSON: {exc}")
    except RecursionError:
        raise LayoutError(f"the file nests values more than {MAX_DEPTH} levels deep")
    _check_depth(value)
    return value


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
    try:
        layout = load_layout(argv[2])
        cost = evaluate(ed, layout)
    except LayoutError as exc:
        print(f"invalid: {exc}")
        return 1
    print(f"valid, cost {cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
