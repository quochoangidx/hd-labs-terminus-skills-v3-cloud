"""Commission on bookings against quota."""

from .figures import figure
from .money import share_of


def band_parts(bookings, quota):
    """The parts of the bookings falling in each of the three bands."""
    first = min(bookings, quota)
    second = min(bookings, 2 * quota) - first
    third = bookings - min(bookings, 2 * quota)
    return first, second, third


def commission(bookings, quota):
    """The rep's commission in cents."""
    first, second, third = band_parts(bookings, quota)
    return (
        share_of(first, figure("band_rate"))
        + share_of(second, figure("above_quota_rate"))
        + share_of(third, figure("top_rate"))
    )
