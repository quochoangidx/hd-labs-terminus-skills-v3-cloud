"""Assemble the lineage report (SOP section 7)."""

from cellbank import banks, lineage


def build_report(log):
    lines = {line["name"]: line for line in log["lines"]}
    records = log["records"]
    cultures, frozen, line_of = lineage.walk(lines, records)
    return {"cultures": cultures, "banks": banks.summarise(records, frozen, line_of)}
