"""Amounts and flags for samples and spikes (SOP section 5)."""


def corrected(reading, level):
    """The corrected reading: the reading less the blank level."""
    return reading - level


def amount(reading, level, dilution):
    """The concentration in the sample as received, in ug/L."""
    return corrected(reading, level) * dilution


def flag(reading, level, dilution, analyte):
    """The flag of a sample or spike, judged on its corrected reading."""
    value = corrected(reading, level)
    if value < analyte["mdl"]:
        return "ND"
    if value < analyte["loq"]:
        return "J"
    return ""
