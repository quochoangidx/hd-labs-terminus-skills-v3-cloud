"""No-template control wells."""

from .replicates import CUTOFF_CYCLE


def contaminated(ntc_cts):
    """Whether a gene's no-template controls show template on the plate."""
    return any(ct is not None for ct in ntc_cts)
