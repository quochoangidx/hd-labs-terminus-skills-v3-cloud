"""Relative quantities, normalisation and fold change for one result."""

import math

from .replicates import detected, mean_ct


def flags_for(plate, contaminated, sample, target):
    """The flags of one sample's result for one target gene, in report order."""
    flags = []
    if contaminated[target] or any(contaminated[gene] for gene in plate.reference_genes):
        flags.append("ntc")
    pair = (sample, plate.calibrator)
    if not all(detected(plate.replicates(s, gene)) for gene in plate.reference_genes for s in pair):
        flags.append("ref")
    if not all(detected(plate.replicates(s, target)) for s in pair):
        flags.append("nd")
    return flags


def fold_change(plate, factors, sample, target):
    """Target quantity relative to the calibrator, over the sample's normalisation factor."""
    cal = plate.calibrator

    def relative_quantity(gene):
        delta = mean_ct(plate.replicates(cal, gene)) - mean_ct(plate.replicates(sample, gene))
        return factors[gene] ** delta

    logs = [math.log(relative_quantity(gene)) for gene in plate.reference_genes]
    return relative_quantity(target) / math.exp(sum(logs) / len(logs))


def result(plate, factors, contaminated, sample, target):
    """One row of the report."""
    flags = flags_for(plate, contaminated, sample, target)
    fold = None if "ntc" in flags else fold_change(plate, factors, sample, target)
    return {
        "sample": sample,
        "gene": target,
        "mean_ct": mean_ct(plate.replicates(sample, target)),
        "fold_change": fold,
        "flags": flags,
    }
