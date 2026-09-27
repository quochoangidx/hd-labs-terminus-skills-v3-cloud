"""No-template control wells."""

from .replicates import reportable


def contaminated(ntc_cts):
    """Whether a gene's no-template controls show template on the plate."""
    return bool(reportable(ntc_cts))
