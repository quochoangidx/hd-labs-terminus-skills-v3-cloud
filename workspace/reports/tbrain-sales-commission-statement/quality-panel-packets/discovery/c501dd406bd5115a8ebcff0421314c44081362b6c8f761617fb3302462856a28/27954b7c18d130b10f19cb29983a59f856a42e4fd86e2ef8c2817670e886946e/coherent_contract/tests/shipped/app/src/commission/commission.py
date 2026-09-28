"""Commission on bookings against quota."""

from .figures import figure


def band_rate(bookings, quota):
    """The rate in basis points of the band the bookings reach."""
    if bookings > 2 * quota:
        return figure("top_rate")
    if bookings > quota:
        return figure("above_quota_rate")
    return figure("band_rate")


def commission(bookings, quota):
    """The rep's commission in cents."""
    return bookings * band_rate(bookings, quota) // 10000
