"""The draw, recovery of what a rep owes, and the payment."""

from .figures import figure


def payout(total, draw, owed):
    """(recovered, owed, paid, carried) in cents for a rep's total."""
    if total < draw:
        return 0, owed + draw - total, draw, 0
    recovered = min(owed, total - draw)
    due = total - recovered
    owed -= recovered
    if draw == 0 and due < 25000:
        return recovered, owed, 0, due
    return recovered, owed, due, 0
