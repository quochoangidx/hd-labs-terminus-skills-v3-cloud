"""Replicate wells of one sample and one gene."""

from .plate import CUTOFF_CYCLE, EARLIEST_CYCLE

OUTLIER_LIMIT = 0.50  # cycles from the median beyond which a replicate is an outlier


def reportable(cts):
    """Cts of the replicates that count: determined, from 10.00 to the cut-off cycle."""
    return [ct for ct in cts if ct is not None and EARLIEST_CYCLE <= ct <= CUTOFF_CYCLE]


def detected(cts):
    """Whether any replicate of the gene counts in this sample."""
    return bool(reportable(cts))


def mean_ct(cts):
    """Mean Ct of a set of determined wells."""
    return sum(cts) / len(cts)


def median_ct(cts):
    """Median of the replicates; of an even number, the lower of the middle two."""
    ordered = sorted(cts)
    return ordered[(len(ordered) - 1) // 2]


def without_outliers(replicates):
    """The reportable replicates that are not outliers (only three or more are screened)."""
    if len(replicates) < 3:
        return list(replicates)
    median = median_ct(replicates)
    return [ct for ct in replicates if abs(ct - median) <= OUTLIER_LIMIT]


def sample_ct(cts):
    """A sample's mean Ct for one gene, or None where the gene is not detected."""
    replicates = without_outliers(reportable(cts))
    if not replicates:
        return None
    return mean_ct(replicates)
