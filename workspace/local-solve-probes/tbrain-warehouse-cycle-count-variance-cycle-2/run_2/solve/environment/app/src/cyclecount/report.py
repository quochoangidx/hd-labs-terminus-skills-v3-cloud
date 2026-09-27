"""The variance report."""

from .tolerance import tolerance, within
from .variance import variance


def status(line, off):
    """Rule 3.1."""
    if within(line, off):
        return "ok"
    if line["recount"] is None:
        return "recount"
    return "adjust"


def report_line(line):
    off = variance(line)
    return {
        "sku": line["sku"],
        "variance": off,
        "tolerance": tolerance(line),
        "status": status(line, off),
        "value": off * line["unit_cost"],
        "booked": off,
    }


def variance_report(sheet):
    rows = [report_line(line) for line in sheet["lines"]]
    # Rule 3.4: shrink sums the value of the adjusted shortages, without sign.
    shrink = sum(
        -row["value"]
        for row in rows
        if row["status"] == "adjust" and row["variance"] < 0
    )
    return {"sheet": sheet["sheet"], "lines": rows, "shrink": shrink}
