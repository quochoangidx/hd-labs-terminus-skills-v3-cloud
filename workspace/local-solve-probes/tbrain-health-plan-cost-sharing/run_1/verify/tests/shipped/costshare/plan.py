"""Benefit settings for one plan year."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    """Cost-sharing settings. Amounts are cents; the rate is basis points."""

    deductible: int
    family_deductible: int
    coinsurance: int
    office_copay: int
    oop_max: int
    family_oop_max: int
