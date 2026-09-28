"""Policy figures, kept by unit and kind."""

# Percentages in tenths of a per cent, money in cents.
FIGURES = {
    # 100 per cent, in tenths of a per cent (1.1).
    "tenths.whole": 1000,
    # The trace figure the package enters as nought on a plot sheet.
    "tenths.floor": 50,
    # A field whose loss is below 8.0 per cent has no payable loss (5.1).
    "tenths.minimum": 80,
    # The `straight` deductible, 10.0 per cent (5.2).
    "tenths.straight": 100,
    # The `vanishing` deductible threshold, 20.0 per cent (5.2).
    "tenths.vanish": 200,
    # The replant payment for each acre replanted (6.1).
    "cents.acre": 3000,
    # The trace figure the package enters as nought on a replant line.
    "cents.floor": 2500,
    # A claim below 10,000 cents is not paid (7.2).
    "cents.minimum": 10000,
}


def figure(unit, kind):
    """The policy figure of a kind, in a unit ("tenths" or "cents")."""
    return FIGURES[f"{unit}.{kind}"]
