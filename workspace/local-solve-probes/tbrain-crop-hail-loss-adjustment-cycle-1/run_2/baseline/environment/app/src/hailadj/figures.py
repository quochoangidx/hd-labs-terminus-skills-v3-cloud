"""Policy figures, looked up by the step of the adjustment that reads them."""

# Percentages in tenths of a per cent, money in cents.
FIGURES = {
    "trace_tenths": 50,
    "deductible_tenths": 50,
    "vanish_tenths": 200,
    "replant_cents": 3000,
    "small_cents": 2500,
}

# Which figure each step of the package reads.
STEPS = {
    "plot_trace": "trace_tenths",
    "minimum_loss": "trace_tenths",
    "straight_deductible": "deductible_tenths",
    "vanishing_start": "vanish_tenths",
    "replant_rate": "replant_cents",
    "replant_trace": "small_cents",
    "minimum_claim": "small_cents",
}


def figure(step):
    """The figure a step of the package reads."""
    return FIGURES[STEPS[step]]
