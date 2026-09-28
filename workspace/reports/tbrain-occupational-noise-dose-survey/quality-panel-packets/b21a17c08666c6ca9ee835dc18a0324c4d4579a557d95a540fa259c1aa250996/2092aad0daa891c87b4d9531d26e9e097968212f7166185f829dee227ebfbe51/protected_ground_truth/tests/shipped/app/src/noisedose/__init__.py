"""Personal noise-dosimeter survey reduction for the hearing conservation programme.

``build_report`` takes a survey as decoded from its JSON file and returns the
exposure report: one row per worker and one row per similar-exposure group.
"""

from .report import build_report

__all__ = ["build_report"]
