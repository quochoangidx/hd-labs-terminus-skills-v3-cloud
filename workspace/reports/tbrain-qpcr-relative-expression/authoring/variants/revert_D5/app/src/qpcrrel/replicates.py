"""Replicate wells of one sample and one gene."""

from .plate import called

EARLIEST_CYCLE = 10.0
STRAY_CYCLES = 0.5


def reportable(cts):
    """The replicate Cts that count toward a sample's result (SOP 2.2)."""
    return [ct for ct in called(cts) if ct >= EARLIEST_CYCLE]


def detected(cts):
    """Whether any replicate of the gene counts in this sample."""
    return bool(reportable(cts))


def mean_ct(cts):
    """Mean Ct of a set of determined wells."""
    return sum(cts) / len(cts)


def without_outliers(cts):
    """Replicates no more than 0.50 cycles from their median, the lower middle one for an even count."""
    if len(cts) < 3:
        return list(cts)
    centre = sorted(cts)[(len(cts) - 1) // 2]
    return [ct for ct in cts if abs(ct - centre) <= STRAY_CYCLES]


def sample_ct(cts):
    """A sample's mean Ct for one gene, from the Cts of its unknown wells."""
    replicates = reportable(cts)
    if not replicates:
        return None
    return mean_ct(replicates)
