"""The variance report."""

from .tolerance import tolerance, within
from .variance import has_recount, variance


def status(line, off):
    """CC-2 rule 3.1."""
    if within(line, off):
        return "ok"
    if has_recount(line):
        return "adjust"
    return "recount"


def booked(line, off, state):
    """The units posted to stock."""
    if state == "adjust":
        # An adjusted line books its variance (CC-2 3.3).
        return off
    return line["count"] - line["system"]


def report_line(line):
    off = variance(line)
    state = status(line, off)
    return {
        "sku": line["sku"],
        "variance": off,
        "tolerance": tolerance(line),
        "status": state,
        "value": off * line["unit_cost"],
        "booked": booked(line, off, state),
    }


def variance_report(sheet):
    rows = [report_line(line) for line in sheet["lines"]]
    # CC-2 rule 3.4: shrink is the sum of the values of the adjusted shortages,
    # taken without their sign; a surplus does not reduce it.
    shrink = sum(
        -row["value"] for row in rows if row["status"] == "adjust" and row["variance"] < 0
    )
    return {"sheet": sheet["sheet"], "lines": rows, "shrink": shrink}
