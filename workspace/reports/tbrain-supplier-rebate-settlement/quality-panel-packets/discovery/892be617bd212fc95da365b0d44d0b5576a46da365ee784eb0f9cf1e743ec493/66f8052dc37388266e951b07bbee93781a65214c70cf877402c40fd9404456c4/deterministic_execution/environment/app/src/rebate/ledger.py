"""Purchase lines from the ledger export and the purchases of a quarter."""

from .dates import in_quarter, parse_day


def dated_lines(lines):
    """Each purchase line as (day, units, value in cents), dated as the export dates it.

    The export dates a line by its invoice, which the supplier raises on the day the goods
    leave its warehouse.
    """
    dated = []
    for invoiced, units, unit_cents in lines:
        day = parse_day(invoiced)
        dated.append((day, units, units * unit_cents))
    return dated


def quarter_purchases(lines, quarter):
    """The value in cents of the purchase lines that count toward the quarter."""
    return sum(value for day, _units, value in dated_lines(lines) if in_quarter(day, quarter))
