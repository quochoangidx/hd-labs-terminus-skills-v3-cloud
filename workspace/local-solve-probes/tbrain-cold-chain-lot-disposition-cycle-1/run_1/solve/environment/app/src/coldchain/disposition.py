"""Per-lot figures and the release decision."""

from .attribution import holds, unlogged_minutes
from .bands import band_minutes
from .kinetics import mean_kinetic_temperature

UNLOGGED_LIMIT_MINUTES = 120
CHAIN_LIMIT_MINUTES = 2880  # the longest handover a chained lot may have (2.9)


def handovers(lot):
    """Minutes from the last reading of each leg to the first reading of the next (2.9)."""
    spans = []
    for earlier, later in zip(lot.legs, lot.legs[1:]):
        spans.append(later.readings[0].minute - earlier.readings[-1].minute)
    return spans


def is_chained(lot):
    """Whether no handover of the lot is longer than 2,880 minutes (2.9)."""
    return all(span <= CHAIN_LIMIT_MINUTES for span in handovers(lot))


def lot_band_minutes(lot, stability):
    """Minutes the lot spent in each band, and its unlogged minutes."""
    per_leg = []
    unlogged = 0
    for leg in lot.legs:
        minutes = holds(leg.readings)
        per_leg.append(band_minutes(leg.readings, minutes, stability))
        unlogged += unlogged_minutes(leg.readings)
    if is_chained(lot):
        totals = {band.name: sum(leg_totals[band.name] for leg_totals in per_leg) for band in stability.bands}
    else:
        totals = {band.name: max(leg_totals[band.name] for leg_totals in per_leg) for band in stability.bands}
    return totals, unlogged


def dispose(lot, stability):
    """The QA figures and the disposition of one lot, times in minutes."""
    band_time, unlogged = lot_band_minutes(lot, stability)
    remaining = {
        band.name: band.allowance_h * 60 - lot.prior_minutes.get(band.name, 0) - band_time[band.name]
        for band in stability.bands
    }
    temps = []
    weights = []
    for leg in lot.legs:
        held = holds(leg.readings)
        for reading, minutes in zip(leg.readings, held):
            temps.append(reading.temp)
            weights.append(minutes)
    mkt = mean_kinetic_temperature(temps, weights, stability.ratio)
    frozen = any(reading.temp < stability.freeze_point for reading in lot.readings())
    if frozen or any(left < 0 for left in remaining.values()):
        decision = "reject"
    elif mkt > stability.high or unlogged > UNLOGGED_LIMIT_MINUTES:
        decision = "quarantine"
    else:
        decision = "release"
    return {
        "lot": lot.lot,
        "disposition": decision,
        "band_minutes": band_time,
        "remaining_minutes": remaining,
        "unlogged_minutes": unlogged,
        "mkt_c": mkt,
    }
