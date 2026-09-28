"""Purchase lines from the ledger export and the purchases of a quarter."""

import datetime

from .dates import in_quarter, parse_day

CARTON_UNITS = 12
ROAD_FREIGHT_DAYS = 4


def dated_lines(lines):
    """Each purchase line as (day, units, value in cents), dated by the quarter it counts toward.

    The export dates a line by its invoice, which the supplier raises on the day the goods
    leave its warehouse. A carton shipment of 12 units or more travels by road freight and
    is received on the fourth day after its invoice date; loose units go by courier and keep
    the date the export gives them.
    """
    dated = []
    for invoiced, units, unit_cents in lines:
        day = parse_day(invoiced)
        if units >= CARTON_UNITS:
            day = day + datetime.timedelta(days=ROAD_FREIGHT_DAYS)
        dated.append((day, units, units * unit_cents))
    return dated


def quarter_purchases(lines, quarter):
    """The value in cents of the purchase lines that count toward the quarter."""
    return sum(value for day, _units, value in dated_lines(lines) if in_quarter(day, quarter))
