"""Relative quantities, normalisation and fold change for one result."""

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
    """Target quantity relative to the calibrator, over the reference genes' shift."""
    cal = plate.calibrator
    factor = factors[target]
    shifts = [
        mean_ct(plate.replicates(cal, gene)) - mean_ct(plate.replicates(sample, gene))
        for gene in plate.reference_genes
    ]
    shift = sum(shifts) / len(shifts)
    delta = mean_ct(plate.replicates(cal, target)) - mean_ct(plate.replicates(sample, target))
    return factor ** delta / factor ** shift


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
