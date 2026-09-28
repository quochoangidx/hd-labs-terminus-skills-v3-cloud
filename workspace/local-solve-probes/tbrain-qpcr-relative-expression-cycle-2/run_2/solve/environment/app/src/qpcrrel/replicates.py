"""Replicate wells of one sample and one gene."""

from .plate import reportable

OUTLIER_DISTANCE = 0.50  # SOP 4.1: cycles from the median of the reportable replicates


def detected(cts):
    """Whether any replicate of the gene counts in this sample (SOP 2.3)."""
    return bool(reportable(cts))


def mean_ct(cts):
    """Mean Ct of a set of determined wells."""
    return sum(cts) / len(cts)


def median_ct(cts):
    """The median of the replicates, the lower of the middle two when even (SOP 4.1)."""
    ordered = sorted(cts)
    return ordered[(len(ordered) - 1) // 2]


def kept(cts):
    """The reportable replicates that are not outliers (SOP 4.1), in export order."""
    replicates = reportable(cts)
    if len(replicates) < 3:
        return replicates
    median = median_ct(replicates)
    return [ct for ct in replicates if abs(ct - median) <= OUTLIER_DISTANCE]


def sample_ct(cts):
    """A sample's mean Ct for one gene, or None where the gene is not detected (SOP 4.2, 4.3)."""
    replicates = kept(cts)
    if not replicates:
        return None
    return mean_ct(replicates)
