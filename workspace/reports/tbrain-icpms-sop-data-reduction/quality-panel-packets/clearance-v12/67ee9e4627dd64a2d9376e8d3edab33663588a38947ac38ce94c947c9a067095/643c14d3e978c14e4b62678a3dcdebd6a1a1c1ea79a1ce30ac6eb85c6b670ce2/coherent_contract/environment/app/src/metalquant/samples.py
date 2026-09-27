"""Amounts and flags for samples and spikes (SOP section 5)."""


def corrected(reading, level):
    return reading - level


def amount(reading, level, dilution):
    return reading * dilution - level


def flag(reading, level, dilution, analyte):
    value = amount(reading, level, dilution)
    if value < analyte["mdl"]:
        return "ND"
    if value <= analyte["loq"]:
        return "J"
    return ""
