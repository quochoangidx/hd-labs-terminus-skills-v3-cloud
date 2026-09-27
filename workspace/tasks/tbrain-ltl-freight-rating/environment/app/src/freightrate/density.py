"""Freight class from density."""

# (minimum pounds per cubic foot, class), densest class first.
DENSITY_TABLE = [
    (50, "50"),
    (35, "55"),
    (30, "60"),
    (22.5, "65"),
    (15, "70"),
    (13.5, "77.5"),
    (12, "85"),
    (10.5, "92.5"),
    (9, "100"),
    (8, "110"),
    (7, "125"),
    (6, "150"),
    (5, "175"),
    (4, "200"),
    (3, "250"),
    (2, "300"),
    (1, "400"),
    (0, "500"),
]


def density(weight, volume):
    """Pounds per cubic foot."""
    return weight / max(volume, 1.0)


def class_for(value):
    """The freight class for a density."""
    for minimum, freight_class in DENSITY_TABLE:
        if value > minimum:
            return freight_class
    return DENSITY_TABLE[-1][1]
