"""Agreement times."""

from datetime import datetime

DAY = 1440


def minutes(text):
    """Minutes since 2000-01-01T00:00 for a YYYY-MM-DDTHH:MM time."""
    delta = datetime.strptime(text, "%Y-%m-%dT%H:%M") - datetime(2000, 1, 1)
    return delta.days * DAY + delta.seconds // 60


def length(agreement):
    """Minutes from going out to coming back."""
    return minutes(agreement["in"]) - minutes(agreement["out"])
