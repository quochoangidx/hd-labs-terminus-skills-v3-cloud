"""Replicate wells of one sample and one gene."""

import statistics

CUTOFF_CYCLE = 35.0
NO_CALL_CT = 40.0  # the run length, used where a gene gives no usable Ct
STRAY_CYCLES = 0.5


def reportable(cts):
    """The replicate Cts that count toward a sample's result."""
    return [ct for ct in cts if ct is not None and ct < CUTOFF_CYCLE]


def detected(cts):
    """Whether any replicate of the gene counts in this sample."""
    return bool(reportable(cts))


def kept(cts):
    """Replicates left once a stray one is set aside."""
    if len(cts) < 3:
        return list(cts)
    centre = statistics.median(cts)
    stray = [ct for ct in cts if abs(ct - centre) > STRAY_CYCLES]
    if len(stray) == 1:
        return [ct for ct in cts if abs(ct - centre) <= STRAY_CYCLES]
    return list(cts)


def mean_ct(cts):
    """Mean Ct of one sample's replicates of one gene."""
    usable = kept(reportable(cts))
    if not usable:
        return NO_CALL_CT
    return sum(usable) / len(usable)
