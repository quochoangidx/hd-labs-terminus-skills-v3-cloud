"""Purchase lines from the ledger export and the purchases of a quarter."""

import datetime

from .dates import in_quarter, parse_day

# A carton shipment (12 units or more) travels by road freight and is received on the fourth
# day after its invoice date; it counts toward the quarter it is received in.
CARTON_UNITS = 12
TRANSIT = datetime.timedelta(days=4)


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
