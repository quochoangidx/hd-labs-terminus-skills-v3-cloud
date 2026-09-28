"""Commission on bookings against quota."""

from .figures import figure
from .money import share_of


def bands(bookings, quota):
    """The parts of the bookings up to the quota, up to twice the quota, and above that."""
    low = min(bookings, quota)
    mid = min(max(bookings - quota, 0), quota)
    top = max(bookings - 2 * quota, 0)
    return low, mid, top


def commission(bookings, quota):
    """The rep's commission in cents: each band at its own rate, rounded on its own."""
    low, mid, top = bands(bookings, quota)
    return (low * figure("band_rate") // 10000 + mid * figure("above_quota_rate") // 10000
            + top * figure("top_rate") // 10000)
