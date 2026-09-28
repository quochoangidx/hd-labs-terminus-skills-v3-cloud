"""Commission on bookings against quota."""

from .figures import figure
from .money import share_of


def bands(bookings, quota):
    """The part of the bookings in each band, as (amount, rate) pairs."""
    base = min(bookings, quota)
    above = min(max(bookings - quota, 0), quota)
    top = max(bookings - 2 * quota, 0)
    return [
        (base, figure("band_rate")),
        (above, figure("above_quota_rate")),
        (top, figure("top_rate")),
    ]


def commission_lines(bookings, quota):
    """The commission in cents of each band, each rounded on its own."""
    return [share_of(amount, rate) for amount, rate in bands(bookings, quota)]


def commission(bookings, quota):
    """The rep's commission in cents."""
    return sum(commission_lines(bookings, quota))
