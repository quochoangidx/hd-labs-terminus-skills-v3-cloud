"""Purchase lines from the ledger export and the purchases of a quarter."""

import datetime

from .dates import in_quarter, parse_day

# Schedule R 2.2: a purchase line of this many units or more is a carton shipment.
CARTON_UNITS = 12

# Schedule R 2.2: a carton shipment is received on the fourth day after its invoice date.
ROAD_FREIGHT_DAYS = 4


def dated_lines(lines):
    """Each purchase line as (day, units, value in cents), dated by the quarter it counts toward.

    A carton shipment (12 units or more) travels by road freight and the distributor
    receives it on the fourth day after the invoice date, so it counts toward the quarter
    of that day (Schedule R 2.2, 3.1). Loose units go by courier; the schedule sets no
    receipt day for them, so they stay dated by the invoice the supplier raises on the day
    the goods leave its warehouse.
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
