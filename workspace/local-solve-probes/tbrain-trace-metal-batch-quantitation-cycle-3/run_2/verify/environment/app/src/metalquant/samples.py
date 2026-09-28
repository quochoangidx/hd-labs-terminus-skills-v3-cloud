"""Amounts and flags for samples and spikes (SOP section 5)."""


def corrected(reading, level):
    return reading - level


def amount(reading, level, dilution):
    return corrected(reading, level) * dilution


def flag(reading, level, dilution, analyte):
    """Flag a sample or spike from its corrected reading (SOP section 5)."""
    value = corrected(reading, level)
    if value < analyte["mdl"]:
        return "ND"
    if value < analyte["loq"]:
        return "J"
    return ""
