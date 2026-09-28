"""Per-lot figures and the release decision."""

from .attribution import holds, spacings, unlogged_minutes
from .bands import band_minutes
from .kinetics import mean_kinetic_temperature

UNLOGGED_LIMIT_MINUTES = 120
EXCURSION_ENTRY_MINUTES = 15  # an entry shorter than this records a transient (2.6)


def prior_minutes(lot, stability):
    """Prior time against each band: the lot's excursion entries against it (2.6, 2.9)."""
    totals = {}
    for band in stability.bands:
        entries = lot.certificate.get(band.name, [])
        totals[band.name] = sum(entry for entry in entries if entry >= EXCURSION_ENTRY_MINUTES)
    return totals


def dispose(lot, stability):
    """The QA figures and the disposition of one lot, times in minutes."""
    per_leg = []
    unlogged = 0
    temps, weights = [], []
    for leg in lot.legs:
        held = holds(leg.readings)
        per_leg.append(band_minutes(leg.readings, held, stability))
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
