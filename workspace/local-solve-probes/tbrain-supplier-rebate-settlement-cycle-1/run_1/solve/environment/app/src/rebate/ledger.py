"""Purchase lines from the ledger export and the purchases of a quarter."""

import datetime

from .dates import in_quarter, parse_day

# A purchase line of this many units or more is a carton shipment (rule 2.2).
CARTON_UNITS = 12

# Days on the road before the distributor receives a carton shipment (rule 2.2).
FREIGHT_DAYS = 4


def dated_lines(lines):
    """Each purchase line as (day, units, value in cents), dated as it counts.

    A carton shipment of 12 units or more travels by road freight and counts toward
    the quarter in which the distributor receives it, the fourth day after its
    invoice date. A picking of loose units goes by courier, and the export dates it
    by its invoice, which the supplier raises on the day the goods leave its
    warehouse.
    """
    dated = []
    for invoiced, units, unit_cents in lines:
        day = parse_day(invoiced)
        if units >= CARTON_UNITS:
            day = day + datetime.timedelta(days=FREIGHT_DAYS)
        dated.append((day, units, units * unit_cents))
    return dated


def quarter_purchases(lines, quarter):
    """The value in cents of the purchase lines that count toward the quarter."""
    return sum(value for day, _units, value in dated_lines(lines) if in_quarter(day, quarter))
