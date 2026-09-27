"""Nuclide data (manual section 2) and half-life conversion."""

# name: (half-life, unit, exempt quantity in Bq, leak-test class, daughter, branching fraction)
TABLE = {
    "H-3": (12.32, "y", 1.0e9, None, None, 0.0),
    "Na-22": (2.6018, "y", 1.0e6, "beta-gamma", None, 0.0),
    "P-32": (14.268, "d", 1.0e5, "beta-gamma", None, 0.0),
    "S-35": (87.37, "d", 1.0e8, "beta-gamma", None, 0.0),
    "Co-57": (271.74, "d", 1.0e6, "beta-gamma", None, 0.0),
    "Co-60": (5.2713, "y", 1.0e5, "beta-gamma", None, 0.0),
    "Ni-63": (101.2, "y", 1.0e8, "beta-gamma", None, 0.0),
    "Ge-68": (270.95, "d", 1.0e5, "beta-gamma", "Ga-68", 1.0),
    "Sr-90": (28.79, "y", 1.0e4, "beta-gamma", "Y-90", 1.0),
    "Cd-109": (461.9, "d", 1.0e6, "beta-gamma", None, 0.0),
    "I-125": (59.49, "d", 1.0e6, "beta-gamma", None, 0.0),
    "Ba-133": (10.551, "y", 1.0e6, "beta-gamma", None, 0.0),
    "Cs-137": (30.08, "y", 1.0e4, "beta-gamma", "Ba-137m", 0.944),
    "Ir-192": (73.829, "d", 1.0e4, "beta-gamma", None, 0.0),
    "Po-210": (138.376, "d", 1.0e4, "alpha", None, 0.0),
    "Am-241": (432.6, "y", 1.0e4, "alpha", None, 0.0),
    "Cf-252": (2.645, "y", 1.0e4, "alpha", None, 0.0),
}

DAYS_PER_YEAR = 365.25  # manual 1.4


def half_life_days(nuclide):
    """Half-life of a nuclide in days."""
    value, unit = TABLE[nuclide][0], TABLE[nuclide][1]
    if unit == "y":
        return value * DAYS_PER_YEAR
    return value


def exempt_quantity(nuclide):
    """Exempt quantity of a nuclide in Bq."""
    return TABLE[nuclide][2]


def leak_class(nuclide):
    """Leak-test class of a nuclide: "beta-gamma", "alpha", or None."""
    return TABLE[nuclide][3]


def daughter_of(nuclide):
    """(daughter name, branching fraction), or (None, 0.0) for a nuclide without one."""
    return TABLE[nuclide][4], TABLE[nuclide][5]
