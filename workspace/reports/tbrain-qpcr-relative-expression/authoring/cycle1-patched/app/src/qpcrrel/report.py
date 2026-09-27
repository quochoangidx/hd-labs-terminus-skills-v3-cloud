"""The relative-expression report of one plate."""

from . import expression, ntc
from .curve import amplification_factor
from .plate import Plate


def build_report(data):
    """Reduce one plate export (a dict read from the JSON file) to its report."""
    plate = Plate(data)
    factors = {gene: amplification_factor(plate.standards.get(gene, [])) for gene in plate.genes}
    contaminated = {gene: ntc.contaminated(plate.ntcs.get(gene, [])) for gene in plate.genes}
    genes = [
        {"gene": gene, "factor": factors[gene], "contaminated": contaminated[gene]}
        for gene in plate.genes
    ]
    results = [
        expression.result(plate, factors, contaminated, sample, target)
        for sample in plate.samples
        for target in plate.target_genes
    ]
    return {"plate": plate.name, "genes": genes, "results": results}
