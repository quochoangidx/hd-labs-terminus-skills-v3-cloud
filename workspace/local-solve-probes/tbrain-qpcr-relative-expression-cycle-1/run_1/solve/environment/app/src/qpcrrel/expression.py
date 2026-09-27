"""Relative quantities, normalisation and fold change for one result."""

from .replicates import detected, mean_ct


def flags_for(plate, contaminated, sample, target):
    """The flags of one sample's result for one target gene, in report order (SOP 6.3)."""
    flags = []
    if contaminated[target] or any(contaminated[gene] for gene in plate.reference_genes):
        flags.append("ntc")
    pair = (sample, plate.calibrator)
    if not all(detected(plate.replicates(s, gene)) for gene in plate.reference_genes for s in pair):
        flags.append("ref")
    if not all(detected(plate.replicates(s, target)) for s in pair):
        flags.append("nd")
    return flags


def relative_quantity(plate, factors, sample, gene):
    """The gene's quantity in the sample relative to the calibrator (SOP 5.1)."""
    cal_ct = mean_ct(plate.replicates(plate.calibrator, gene))
    sample_ct = mean_ct(plate.replicates(sample, gene))
    return factors[gene] ** (cal_ct - sample_ct)


def fold_change(plate, factors, sample, target):
    """Target quantity relative to the calibrator, over the reference genes' shift."""
    quantities = [
        relative_quantity(plate, factors, sample, gene) for gene in plate.reference_genes
    ]
    product = 1.0
    for quantity in quantities:
        product *= quantity
    normalisation = product ** (1.0 / len(quantities))  # SOP 5.2: geometric mean
    return relative_quantity(plate, factors, sample, target) / normalisation


def result(plate, factors, contaminated, sample, target):
    """One row of the report."""
    flags = flags_for(plate, contaminated, sample, target)
    fold = None if flags else fold_change(plate, factors, sample, target)
    return {
        "sample": sample,
        "gene": target,
        "mean_ct": mean_ct(plate.replicates(sample, target)),
        "fold_change": fold,
        "flags": flags,
    }
