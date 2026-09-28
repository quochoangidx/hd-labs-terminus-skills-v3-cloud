"""Per-bottle arithmetic: depletion, sample fraction, the spent and usable tests, bottle BOD."""

BOTTLE_ML = 300.0
MIN_DEPLETION = 2.5
MIN_FINAL_DO = 1.0


def depletion(bottle):
    """Initial DO less final DO, in mg/L."""
    return bottle["do_initial"] - bottle["do_final"]


def sample_fraction(bottle):
    """Share of the bottle taken up by sample."""
    return bottle["sample_ml"] / BOTTLE_ML


def is_spent(bottle):
    """The oxygen ran out before day five."""
    return bottle["do_final"] < MIN_FINAL_DO


def is_usable(bottle):
    """Depleted enough to read and not spent."""
    return depletion(bottle) >= MIN_DEPLETION and not is_spent(bottle)


def seed_correction(bottle, seed_factor):
    """Oxygen taken up by the seed the bottle holds."""
    return seed_factor * bottle["seed_ml"]


def bottle_bod(bottle, seed_factor):
    """BOD of one check or sample bottle, in mg/L."""
    return (depletion(bottle) - seed_correction(bottle, seed_factor)) / sample_fraction(bottle)
