"""Replicate wells of one sample and one gene."""

import statistics

CUTOFF_CYCLE = 35.0
EARLIEST_CYCLE = 10.0  # a Ct before this cycle is a baseline or saturation fault
NO_CALL_CT = 40.0  # the run length, used where a gene gives no usable Ct
STRAY_CYCLES = 0.5


def reportable(cts):
    """The replicate Cts that count toward a sample's result (SOP 2.2)."""
    return [ct for ct in cts if ct is not None and EARLIEST_CYCLE <= ct <= CUTOFF_CYCLE]


def detected(cts):
    """Whether any replicate of the gene counts in this sample (SOP 2.3)."""
    return bool(reportable(cts))


def kept(cts):
    """Reportable replicates left once the outliers are set aside (SOP 4.1)."""
    if len(cts) < 3:
        return list(cts)
    centre = statistics.median(cts)
    return [ct for ct in cts if abs(ct - centre) <= STRAY_CYCLES]


def mean_ct(cts):
    """Mean Ct of one sample's replicates of one gene (SOP 4.2, 4.3)."""
    replicates = reportable(cts)
    if not replicates:
        return None
    usable = kept(replicates)
    if not usable:
        return NO_CALL_CT
    return sum(usable) / len(usable)
