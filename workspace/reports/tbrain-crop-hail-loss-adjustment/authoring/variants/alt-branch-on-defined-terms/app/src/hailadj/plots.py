"""Sample-plot figures and their field averages."""

from .figures import figure
from .rounding import half_up
from .sheet import UNITS


def stand_figure(plot):
    """The stand-loss figure of one plot, in tenths of a per cent."""
    share = half_up(plot.dead * 1000, plot.stand)
    if plot.dead * 10 >= plot.stand:
        return share
    if share < figure(UNITS["stand_loss"], "floor"):
        # A share under the trace figure is entered as nought.
        share = 0
    return share


def leaf_figure(plot):
    """The leaf-damage figure of one plot, in tenths of a per cent."""
    return plot.leaf


def plot_average(figures):
    """The average of a field's plot figures, in tenths of a per cent."""
    return half_up(sum(figures), len(figures))


def field_averages(plots):
    """(stand loss, defoliation) of a field, in tenths of a per cent."""
    stand = plot_average([stand_figure(plot) for plot in plots])
    defoliation = plot_average([leaf_figure(plot) for plot in plots])
    return stand, defoliation
