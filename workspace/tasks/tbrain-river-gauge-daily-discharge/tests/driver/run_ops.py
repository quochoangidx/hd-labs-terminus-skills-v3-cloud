"""Run scripted calls against a gaugeflow package and print the outcomes as JSON.

Usage: python3 run_ops.py <package-root> < job.json

The verifier runs this file from its own read-only copy, as an unprivileged
user, against the candidate's /app/src or the sealed shipped copy. It reports
what the package returns or raises; it decides nothing.
"""

import json
import sys


def plain(value):
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def main():
    sys.path.insert(0, sys.argv[1])
    import gaugeflow as g

    def curve(op):
        return g.RatingCurve([g.Segment(*s) for s in op["segments"]])

    def table(op):
        return [tuple(e) for e in op["table"]]

    def series(op):
        return [tuple(p) for p in op["series"]]

    def record(op):
        return [g.Reading(t, h) for t, h in op["record"]]

    calls = {
        "shift": lambda op: g.shift_at(table(op), op["t"]),
        "rate": lambda op: curve(op).discharge(op["stage"]),
        "series": lambda op: g.discharge_series(record(op), table(op), curve(op)),
        "pieces": lambda op: list(g.joined_pieces(series(op), op["gap"])),
        "span": lambda op: g.span_totals(series(op), op["start"], op["end"], op["gap"]),
        "daily": lambda op: g.daily_mean(series(op), op["day"], op["gap"]),
        "volume": lambda op: g.volume(series(op), op["start"], op["end"], op["gap"]),
        "peaks": lambda op: g.peaks(series(op), op["threshold"], op["separation"]),
        "daily_values": lambda op: g.daily_values(record(op), table(op), curve(op), op["first"], op["last"], op["gap"]),
    }
    out = []
    for op in json.load(sys.stdin):
        try:
            out.append({"ok": plain(calls[op["op"]](op))})
        except Exception as exc:  # reported, never judged here
            out.append({"error": type(exc).__name__})
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
