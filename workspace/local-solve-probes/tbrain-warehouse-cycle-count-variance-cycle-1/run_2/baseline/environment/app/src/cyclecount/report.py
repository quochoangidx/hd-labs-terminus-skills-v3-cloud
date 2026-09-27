"""The variance report."""

from .tolerance import tolerance, within
from .variance import variance


def status(line, off):
    if within(line, off):
        return "ok"
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
    shrink = -sum(row["value"] for row in rows if row["status"] == "adjust")
    return {"sheet": sheet["sheet"], "lines": rows, "shrink": shrink}
