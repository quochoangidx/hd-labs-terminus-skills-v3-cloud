"""Sound-level constants and reference durations.

Levels are A-weighted equivalent levels in dBA; peaks are C-weighted peak
levels in dBC. Durations are whole minutes.
"""

EIGHT_HOURS = 480  # minutes in the reference working day

CRITERION_DBA = 85.0  # steady level that gives a 100 per cent dose over eight hours
EXCHANGE_DB = 3.0  # change in level that halves or doubles the allowed time
MEASURING_FLOOR_DBA = 40.0  # bottom of the dosimeter's measuring range
THRESHOLD_DBA = 80.0  # runs below this level add no dose
CEILING_DBA = 115.0  # continuous-level ceiling
IMPULSE_DBC = 140.0  # peak level treated as impulse noise


def reference_minutes(level):
    """Minutes at a steady ``level`` (dBA) that make a dose of 100 per cent."""
    return EIGHT_HOURS / 2.0 ** ((level - CRITERION_DBA) / EXCHANGE_DB)


def is_reading(level):
    """True when a run logged at ``level`` is a reading (manual 2.2)."""
    return level >= MEASURING_FLOOR_DBA


def adds_dose(level):
    """True when a run logged at ``level`` is a counted reading (manual 2.3)."""
    return level >= THRESHOLD_DBA
