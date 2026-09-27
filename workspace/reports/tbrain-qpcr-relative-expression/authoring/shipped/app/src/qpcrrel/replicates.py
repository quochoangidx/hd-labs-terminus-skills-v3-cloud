"""Replicate wells of one sample and one gene."""

from .plate import called

NO_CALL_CT = 40.0  # the run length, used where a gene gives no usable Ct


def detected(cts):
    """Whether any replicate of the gene counts in this sample."""
    return bool(called(cts))


def mean_ct(cts):
    """Mean Ct of a set of determined wells."""
    return sum(cts) / len(cts)


def sample_ct(cts):
    """A sample's mean Ct for one gene, from the Cts of its unknown wells."""
    replicates = called(cts)
    if not replicates:
        return NO_CALL_CT
    return mean_ct(replicates)
