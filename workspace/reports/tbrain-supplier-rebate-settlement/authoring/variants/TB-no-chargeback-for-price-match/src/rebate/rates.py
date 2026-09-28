"""Contract figures, looked up by the use each part of the settlement puts them to."""

# Figures in cents.
FIGURES = {
    "unit_handling": 25,
    "small_credit": 5000,
    "return_handling": 40,
    "minimum_settlement": 25000,
}

# Which figure each use of the package reads.
USES = {
    "return_charge": "return_handling",
    "claim_cutoff": "unit_handling",
    "notice_cutoff": "small_credit",
    "settlement_minimum": "minimum_settlement",
}


def figure(use):
    """The figure in cents a use of the package reads."""
    return FIGURES[USES[use]]
