"""The variance report."""

from .tolerance import tolerance, within
from .variance import variance


def status(line, off):
    if within(line, off):
        return "ok"
    return "adjust" if line["recount"] is not None else "recount"


def report_line(line):
    off = variance(line)
    return {
        "sku": line["sku"],
        "variance": off,
        "tolerance": tolerance(line),
        "status": status(line, off),
        "value": off * line["unit_cost"],
        "booked": off if status(line, off) == "adjust" else line["count"] - line["system"],
    }


def variance_report(sheet):
    rows = [report_line(line) for line in sheet["lines"]]
    shrink = -sum(row["value"] for row in rows if row["status"] == "adjust" and row["variance"] < 0)
    return {"sheet": sheet["sheet"], "lines": rows, "shrink": shrink}
