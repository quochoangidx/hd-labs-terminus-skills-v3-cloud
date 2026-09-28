"""The replant line of a field."""

from .figures import figure


def replant_line(replanted):
    """The replant line in cents for the acres replanted, given in tenths of an acre."""
    line = replanted * figure("replant_rate") // 10
    if line < figure("replant_trace"):
        # Too small to be worth a cheque line of its own.
        line = 0
    return line
