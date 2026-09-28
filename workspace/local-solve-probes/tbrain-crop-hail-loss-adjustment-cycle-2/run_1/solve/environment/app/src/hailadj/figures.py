"""Policy figures, kept by unit and kind."""

# Percentages in tenths of a per cent, money in cents.
FIGURES = {
    # 5.1: a field whose loss is below 8.0 per cent has no payable loss.
    "tenths.floor": 80,
    # A plot share under this trace figure is entered as nought (no rule of the
    # procedure reaches a plot that is not hail-thinned).
    "tenths.trace": 50,
    # 5.2: the straight deductible, 10.0 per cent.
    "tenths.straight": 100,
    # 5.2: the vanishing deductible starts above 20.0 per cent.
    "tenths.vanish": 200,
    # 6.1: the replant payment for each acre replanted.
    "cents.acre": 3000,
    # 7.2: a claim under this figure is not paid.
    "cents.floor": 10000,
    # A replant line under this trace figure is entered as nought (no rule of
    # the procedure reaches a field that is not a replanted field).
    "cents.trace": 2500,
}


def figure(unit, kind):
    """The policy figure of a kind, in a unit ("tenths" or "cents")."""
    return FIGURES[f"{unit}.{kind}"]
