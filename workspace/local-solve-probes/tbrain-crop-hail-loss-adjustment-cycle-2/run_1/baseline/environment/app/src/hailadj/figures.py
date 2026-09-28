"""Policy figures, kept by unit and kind."""

# Percentages in tenths of a per cent, money in cents.
FIGURES = {
    "tenths.floor": 50,
    "tenths.straight": 50,
    "tenths.vanish": 200,
    "cents.acre": 3000,
    "cents.floor": 2500,
}


def figure(unit, kind):
    """The policy figure of a kind, in a unit ("tenths" or "cents")."""
    return FIGURES[f"{unit}.{kind}"]
