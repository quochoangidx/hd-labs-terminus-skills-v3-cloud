"""Amounts and flags for samples and spikes (SOP section 5)."""


def corrected(reading, level):
    """The reading less the blank level."""
    return reading - level


def amount(reading, level, dilution):
    """The corrected reading multiplied by the dilution."""
    return corrected(reading, level) * dilution


def flag(reading, level, dilution, analyte):
    """The flag, judged on the corrected reading (SOP 3 and 5)."""
    value = corrected(reading, level)
    if value < analyte["mdl"]:
        return "ND"
    if value < analyte["loq"]:
        return "J"
    return ""
