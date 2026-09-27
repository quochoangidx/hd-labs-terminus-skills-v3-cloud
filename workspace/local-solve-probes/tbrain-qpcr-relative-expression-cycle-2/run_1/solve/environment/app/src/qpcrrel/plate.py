"""Reading a plate export together with its plate map (see README)."""

UNDETERMINED = "Undetermined"
CUTOFF_CYCLE = 35.0
EARLIEST_CYCLE = 10.0


def ct_value(raw):
    """A well's Ct as a float, or None for a well reported as Undetermined."""
    if raw == UNDETERMINED:
        return None
    return float(raw)


def determined(cts):
    """Cts of the wells whose signal crossed the threshold, in export order."""
    return [ct for ct in cts if ct is not None]


def called(cts):
    """Cts of the wells that crossed the threshold by the cut-off cycle, in export order."""
    return [ct for ct in cts if ct is not None and ct <= CUTOFF_CYCLE]


class Plate:
    """The wells of one plate, grouped the way the reduction reads them."""

    def __init__(self, data):
        self.name = data["plate"]
        self.calibrator = data["calibrator"]
        self.reference_genes = list(data["reference_genes"])
        self.target_genes = list(data["target_genes"])
        self.unknowns = {}  # (sample, gene) -> [Ct or None, ...] in export order
        self.standards = {}  # gene -> [(quantity, Ct or None), ...]
        self.ntcs = {}  # gene -> [Ct or None, ...]
        for well in data["wells"]:
            kind = well["kind"]
            gene = well["gene"]
            ct = ct_value(well["ct"])
            if kind == "unknown":
                self.unknowns.setdefault((well["sample"], gene), []).append(ct)
            elif kind == "standard":
                self.standards.setdefault(gene, []).append((float(well["quantity"]), ct))
            elif kind == "ntc":
                self.ntcs.setdefault(gene, []).append(ct)

    @property
    def genes(self):
        """Reference genes first, then target genes, each in plate-map order."""
        return self.reference_genes + self.target_genes

    @property
    def samples(self):
        """Every sample with an unknown well, in code-point order of its name."""
        return sorted({sample for sample, _gene in self.unknowns})

    def replicates(self, sample, gene):
        """The Cts of one sample's unknown wells of one gene."""
        return self.unknowns.get((sample, gene), [])
