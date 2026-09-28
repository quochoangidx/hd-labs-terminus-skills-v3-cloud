"""Per-lot figures and the release decision."""

from .attribution import holds, unlogged_minutes
from .bands import band_minutes
from .kinetics import mean_kinetic_temperature

UNLOGGED_LIMIT_MINUTES = 120


def lot_band_minutes(lot, stability):
    """Minutes the lot spent in each band, and its unlogged minutes."""
    per_leg = []
    unlogged = 0
    for leg in lot.legs:
        minutes = holds(leg.readings)
        per_leg.append(band_minutes(leg.readings, minutes, stability))
        unlogged += unlogged_minutes(leg.readings)  # 4.3
    if lot.chained():
        # 4.1: a chained lot's time in a band totals that band's time over its legs.
        totals = {
            band.name: sum(leg_totals[band.name] for leg_totals in per_leg) for band in stability.bands
        }
    else:
        # The procedure fixes no time in a band for a lot that is not chained.
        totals = {
            band.name: max(leg_totals[band.name] for leg_totals in per_leg) for band in stability.bands
        }
    return totals, unlogged


def dispose(lot, stability):
    """The QA figures and the disposition of one lot, times in minutes."""
    band_time, unlogged = lot_band_minutes(lot, stability)
    # 4.2: allowance less the prior time the release certificate records less the lot's time in the band.
    remaining = {
        band.name: band.allowance_h * 60 - lot.prior_minutes.get(band.name, 0) - band_time[band.name]
        for band in stability.bands
    }
    readings = []
    weights = []
    for leg in lot.legs:
        readings.extend(leg.readings)
        weights.extend(holds(leg.readings))
    mkt = mean_kinetic_temperature(
        [reading.temp for reading in readings], weights, stability.ratio
    )  # 5.1
    frozen = any(reading.temp < stability.freeze_point for reading in readings)  # 2.8
    if frozen or any(left < 0 for left in remaining.values()):  # 6.1
        decision = "reject"
    elif mkt > stability.high or unlogged > UNLOGGED_LIMIT_MINUTES:  # 6.2, on unrounded figures (1.2)
        decision = "quarantine"
    else:
        decision = "release"  # 6.3
    return {
        "lot": lot.lot,
        "disposition": decision,
        "band_minutes": band_time,
        "remaining_minutes": remaining,
        "unlogged_minutes": unlogged,
        "mkt_c": mkt,
    }
