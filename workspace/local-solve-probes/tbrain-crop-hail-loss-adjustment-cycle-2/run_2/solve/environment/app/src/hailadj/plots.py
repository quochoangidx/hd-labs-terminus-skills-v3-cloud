"""Sample-plot figures and their field averages."""

from .figures import figure
from .rounding import half_up
from .sheet import UNITS


def hail_thinned(plot):
    """Whether one plant in ten of the plot's stand, or more, is dead or broken (2.1)."""
    return plot.dead * 10 >= plot.stand


def stand_figure(plot):
    """The stand-loss figure of one plot, in tenths of a per cent."""
    share = half_up(plot.dead * 1000, plot.stand)
    if hail_thinned(plot):
        # The stand loss of a hail-thinned plot (3.1).
        return share
    if share < figure(UNITS["stand_loss"], "floor"):
        # A share under the trace figure is entered as nought.
        share = 0
    return share


def leaf_figure(plot):
    """The leaf-damage figure of one plot, in tenths of a per cent."""
    return plot.leaf


def plot_average(figures):
    """The average of a field's plot figures, in tenths of a per cent.

    The average is taken over all of the field's plots (3.3).
    """
    if not figures:
        return 0
    return half_up(sum(figures), len(figures))


def field_averages(plots):
    """(stand loss, defoliation) of a field, in tenths of a per cent."""
    stand = plot_average([stand_figure(plot) for plot in plots])
    defoliation = plot_average([leaf_figure(plot) for plot in plots])
    return stand, defoliation
