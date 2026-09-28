"""Contract figures, looked up by the use each part of the settlement puts them to."""

# Figures in cents.
FIGURES = {
    "unit_handling": 40,
    "contract_gap": 100,
    "price_drop": 250,
    "small_settlement": 25000,
}

# Which figure each use of the package reads.
USES = {
    "return_charge": "unit_handling",
    "claim_cutoff": "contract_gap",
    "notice_cutoff": "price_drop",
    "settlement_minimum": "small_settlement",
}


def figure(use):
    """The figure in cents a use of the package reads."""
    return FIGURES[USES[use]]
