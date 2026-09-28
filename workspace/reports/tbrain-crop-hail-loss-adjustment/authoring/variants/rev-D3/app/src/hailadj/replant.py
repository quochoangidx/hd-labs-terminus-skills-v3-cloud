"""The replant line of a field."""

from .figures import figure
from .sheet import UNITS


def replant_line(replanted):
    """The replant line in cents for the acres replanted, given in tenths of an acre."""
    line = replanted * figure(UNITS["replant"], "acre") // 10
    if line < figure(UNITS["replant"], "floor"):
        # A line under the trace figure is entered as nought.
        line = 0
    return line
