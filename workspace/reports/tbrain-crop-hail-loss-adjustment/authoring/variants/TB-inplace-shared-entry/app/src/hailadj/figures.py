"""Policy figures, kept by unit and kind."""

# Percentages in tenths of a per cent, money in cents.
FIGURES = {
    "tenths.floor": 50,
    "tenths.minimum_loss": 80,
    "tenths.straight": 100,
    "tenths.vanish": 200,
    "cents.acre": 3000,
    "cents.floor": 10000,
    "cents.minimum_claim": 10000,
}


def figure(unit, kind):
    """The policy figure of a kind, in a unit ("tenths" or "cents")."""
    return FIGURES[f"{unit}.{kind}"]
