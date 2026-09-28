"""Purchase lines from the ledger export and the purchases of a quarter."""

import datetime

from .dates import in_quarter, parse_day

# A purchase line of this many units or more is a carton shipment: it goes by road
# freight and the distributor receives it this many days after the invoice date.
CARTON_UNITS = 12
ROAD_DAYS = 4


def dated_lines(lines):
    """Each purchase line as (day, units, value in cents), dated as it counts.

    A carton shipment counts from the day the distributor receives it, the fourth day
    after its invoice date. A few loose units go by courier; such a line keeps the day
    the export dates it, its invoice date, the day the goods leave the warehouse.
    """
    dated = []
    for invoiced, units, unit_cents in lines:
        day = parse_day(invoiced)
        if units >= CARTON_UNITS:
            day = day + datetime.timedelta(days=ROAD_DAYS)
        dated.append((day, units, units * unit_cents))
    return dated


def quarter_purchases(lines, quarter):
    """The value in cents of the purchase lines that count toward the quarter."""
    return sum(value for day, _units, value in dated_lines(lines) if in_quarter(day, quarter))
