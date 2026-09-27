"""No-template control wells."""

from .replicates import CUTOFF_CYCLE


def contaminated(ntc_cts):
    """Whether a gene's no-template controls show template on the plate (SOP 2.6)."""
    return any(ct is not None and ct <= CUTOFF_CYCLE for ct in ntc_cts)
