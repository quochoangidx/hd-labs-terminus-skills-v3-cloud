"""Amounts and flags for samples and spikes (SOP section 5)."""


def corrected(reading, level):
    return reading - level


def amount(reading, level, dilution):
    return corrected(reading, level) * dilution


def is_result(reading, level, analyte):
    return corrected(reading, level) >= analyte["mdl"]


def flag(reading, level, dilution, analyte):
    value = corrected(reading, level)
    if value < analyte["mdl"]:
        return "ND"
    if value < analyte["loq"]:
        return "J"
    return ""
