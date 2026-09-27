"""Independent model of procedure CC-2 (/app/docs/cycle-count-procedure.md).

Worked out from the procedure alone; it never imports the package under repair. Where the procedure gives
no rule for a figure, the model mirrors the shipped package's step for it and says so ("Shipped step"),
feeding that step the figures the procedure does define.
"""

GRADED = {"A": 0, "B": 2, "C": 5}  # 2.3, per cent of the system quantity


def final_count(line):
    """2.1."""
    return line["recount"] if line["recount"] is not None else line["count"]


def variance(line):
    """2.2."""
    return final_count(line) - line["system"]


def tolerance(line):
    if line["class"] in GRADED:  # 2.3, a fraction of a unit dropped (1.2)
        return line["system"] * GRADED[line["class"]] // 100
    # Shipped step (no rule for a line that is not a graded item): tolerance.tolerance() takes
    # round(system * 5 / 100), Python's round, a half going to the even unit.
    return round(line["system"] * 5 / 100)


def status(line, off):
    """3.1."""
    if abs(off) <= tolerance(line):  # 2.4
        return "ok"
    return "adjust" if line["recount"] is not None else "recount"


def booked(off, state):
    if state == "adjust":  # 3.3
        return off
    # Shipped step (no rule for a line that is not adjusted): report.report_line() books the variance.
    return off


def report(sheet):
    rows = []
    for line in sheet["lines"]:
        off = variance(line)
        state = status(line, off)
        rows.append({"sku": line["sku"], "variance": off, "tolerance": tolerance(line), "status": state,
                     "value": off * line["unit_cost"], "booked": booked(off, state)})
    shrink = sum(-r["value"] for r in rows if r["status"] == "adjust" and r["variance"] < 0)  # 3.4
    return {"sheet": sheet["sheet"], "lines": rows, "shrink": shrink}
