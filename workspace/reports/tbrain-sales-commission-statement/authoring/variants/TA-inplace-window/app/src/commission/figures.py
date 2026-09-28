"""Plan figures, looked up by the use each step of the statement puts them to."""

# Figures: cents, days or basis points, as the name says.
FIGURES = {
    "base_bp": 800,
    "above_bp": 1200,
    "top_bp": 1600,
    "logo_bp": 300,
    "window_days": 120,
    "small_cents": 10000,
    "reversal_days": 120,
    "payment_cents": 25000,
}

# Which figure each use of the package reads.
USES = {
    "band_rate": "base_bp",
    "above_quota_rate": "above_bp",
    "top_rate": "top_bp",
    "clawback_rate": "base_bp",
    "clawback_age": "window_days",
    "reversal_age": "reversal_days",
    "bonus_rate": "logo_bp",
    "bonus_floor": "small_cents",
    "minimum_payment": "payment_cents",
}


def figure(use):
    """The figure a use of the package reads."""
    return FIGURES[USES[use]]
