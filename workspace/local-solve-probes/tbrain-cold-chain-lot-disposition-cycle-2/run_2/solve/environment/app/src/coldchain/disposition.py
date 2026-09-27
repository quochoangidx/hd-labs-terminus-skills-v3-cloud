"""Per-lot figures and the release decision."""

from .attribution import holds, spacings, unlogged_minutes
from .bands import band_minutes
from .kinetics import mean_kinetic_temperature

UNLOGGED_LIMIT_MINUTES = 120
EXCURSION_ENTRY_MINUTES = 15  # a shorter certificate entry records a transient


def prior_minutes(lot, stability):
    """Prior time against each band of the record, from the lot's release certificate."""
    prior = {band.name: 0 for band in stability.bands}
    for name, entries in lot.certificate.items():
        if name in prior:
            prior[name] += sum(entry for entry in entries if entry >= EXCURSION_ENTRY_MINUTES)
    return prior


def dispose(lot, stability):
    """The QA figures and the disposition of one lot, times in minutes."""
    per_leg = []
    unlogged = 0
    temps, weights = [], []
    for leg in lot.legs:
        per_leg.append(band_minutes(leg.readings, holds(leg.readings), stability))
        unlogged += unlogged_minutes(leg.readings)
        temps += [reading.temp for reading in leg.readings]
        weights += spacings(leg.readings)
    prior = prior_minutes(lot, stability)
    band_time = {band.name: sum(leg_totals[band.name] for leg_totals in per_leg) for band in stability.bands}
    remaining = {
        band.name: band.allowance_h * 60 - prior[band.name] - band_time[band.name] for band in stability.bands
    }
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
