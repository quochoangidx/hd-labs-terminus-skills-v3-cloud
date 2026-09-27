"""Replay one session through a looptune package and print the records as JSON.

Usage: python3 -I run_session.py <src-root>   (session JSON on stdin)
"""

import json
import math
import sys


def record(loop, u):
    terms = loop.terms()
    row = {"u": u, "integral": loop.integral}
    for key in ("p", "i", "d", "f", "v", "u"):
        row["t_" + key] = terms.get(key)
    return row


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    return value


def main():
    sys.path.insert(0, sys.argv[1])
    session = json.load(sys.stdin)
    from looptune import Controller, Tuning

    loop = Controller(Tuning(**session["tuning"]))
    rows = []
    for op in session["ops"]:
        kind = op[0]
        if kind == "step":
            _, r, y, f = op
            rows.append(record(loop, loop.step(r, y, f)))
        elif kind == "manual":
            loop.set_manual(op[1])
        elif kind == "auto":
            loop.set_auto()
        elif kind == "retune":
            loop.retune(**op[1])
        else:
            raise ValueError(kind)
    rows = [{k: clean(v) for k, v in row.items()} for row in rows]
    sys.stdout.write(json.dumps(rows))


if __name__ == "__main__":
    main()
