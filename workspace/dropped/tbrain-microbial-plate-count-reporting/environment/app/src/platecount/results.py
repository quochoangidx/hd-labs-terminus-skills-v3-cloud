"""A sample's result from its plate readings."""

from fractions import Fraction

from .plates import COUNTABLE_HIGH, colonies, in_count, is_countable, is_crowded, plated_amount

COUNT = "count"
ESTIMATE = "estimate"
BELOW = "below"
ABOVE = "above"


def count(dilution):
    """Colonies on the plates of a dilution that take part in a count, over their plated amount."""
    plates = [colonies(r) for r in dilution.plates if in_count(r)]
    return Fraction(sum(plates)) / (len(plates) * plated_amount(dilution))


def estimate(dilutions):
    """A sample without a countable plate: pool the plates that are not crowded."""
    total = 0
    amount = Fraction(0)
    for dilution in dilutions:
        for reading in dilution.plates:
            if not is_crowded(reading):
                total += colonies(reading)
                amount += plated_amount(dilution)
    if total == 0:
        return BELOW, 1 / plated_amount(dilutions[-1])
    return ESTIMATE, Fraction(total) / amount


def sample_result(sample):
    """(kind, value) for one sample; value is exact and unrounded."""
    dilutions = sample.dilutions
    for dilution in dilutions:
        if any(is_countable(r) for r in dilution.plates):
            return COUNT, count(dilution)
    if all(is_crowded(r) for d in dilutions for r in d.plates):
        return ABOVE, COUNTABLE_HIGH / plated_amount(dilutions[0])
    return estimate(dilutions)
