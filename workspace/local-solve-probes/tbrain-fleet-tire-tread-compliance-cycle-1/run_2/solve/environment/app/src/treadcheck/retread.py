"""Whether a casing may go for retread."""

from . import dates, status as status_module

MAX_AGE_DAYS = 2190
MAX_RETREADS = 2


def casing_eligible(tire, report_date, tire_status):
    """True when the casing may be sent for retread (6.1)."""
    if tire_status != status_module.PULL:
        return False
    age = dates.days_between(tire["casing"], report_date)
    if age >= MAX_AGE_DAYS:
        return False
    return tire["retreads"] < MAX_RETREADS
