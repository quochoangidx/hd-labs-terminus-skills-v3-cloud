"""Whether a casing may go for retread."""

from . import dates

MAX_AGE_YEARS = 6
MAX_RETREADS = 2


def casing_eligible(tire, report_date):
    """True when the casing may be sent for retread."""
    age = dates.year_of(report_date) - dates.year_of(tire["casing"])
    if age >= MAX_AGE_YEARS:
        return False
    return tire["retreads"] <= MAX_RETREADS
