"""No-template control wells."""

from .plate import called


def contaminated(ntc_cts):
    """Whether a gene's no-template controls show template on the plate."""
    return bool(called(ntc_cts))
